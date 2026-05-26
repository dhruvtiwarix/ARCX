"""
ARCX Admin Operations Views — Phase 11
----------------------------------------
Superuser-only endpoints for the ARCX Treasury team.
Enforces IsAdminUser strictly.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db import transaction

from arcx_core.models import User, Wallet, KYCRecord, CircuitBreakerLog
from domain.valuation import ValuationEngine
from domain.oracle import MultiSourceOracle
from arcx_core.tasks.eod_tasks import take_vault_snapshot, publish_daily_nav

logger = logging.getLogger("arcx.views.admin")


class AdminUserListView(APIView):
    """
    GET /api/v1/admin/users
    Returns a list of all users and their basic wallet/KYC info.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.select_related("wallet").filter(deleted_at__isnull=True).order_by("-created_at")[:100]
        data = []
        for u in users:
            try:
                w = u.wallet
                balance = float(w.arcx_balance)
                cost = float(w.cost_basis_inr)
            except Wallet.DoesNotExist:
                balance = 0.0
                cost = 0.0

            data.append({
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "kyc_status": u.kyc_status,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
                "arcx_balance": balance,
                "cost_basis_inr": cost,
            })
        return Response({"users": data})


class AdminKYCView(APIView):
    """
    GET /api/v1/admin/kyc
    POST /api/v1/admin/kyc

    Manage KYC verifications.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        records = KYCRecord.objects.filter(status=KYCRecord.Status.PENDING).select_related("user").order_by("created_at")
        data = []
        for r in records:
            data.append({
                "id": str(r.id),
                "user_email": r.user.email,
                "tier": r.tier,
                "document_type": r.document_type,
                "document_ref": r.document_ref,
                "created_at": r.created_at.isoformat(),
            })
        return Response({"pending_kyc": data})

    def post(self, request):
        record_id = request.data.get("record_id")
        action = request.data.get("action")  # 'approve' or 'reject'

        if action not in ["approve", "reject"]:
            return Response({"error": "Action must be approve or reject."}, status=400)

        try:
            with transaction.atomic():
                record = KYCRecord.objects.select_related("user").select_for_update().get(id=record_id)
                if record.status != KYCRecord.Status.PENDING:
                    return Response({"error": "KYC record is not pending."}, status=400)
                
                if action == "approve":
                    record.status = KYCRecord.Status.APPROVED
                    record.user.kyc_status = User.KycStatus.APPROVED
                else:
                    record.status = KYCRecord.Status.REJECTED
                    record.user.kyc_status = User.KycStatus.REJECTED
                
                record.save()
                record.user.save()

                logger.info(f"Admin {request.user.email} {action}d KYC {record_id} for user {record.user.email}")
                return Response({"message": f"KYC successfully {action}d."})

        except KYCRecord.DoesNotExist:
            return Response({"error": "KYC record not found."}, status=404)


class AdminNAVComputerView(APIView):
    """
    POST /api/v1/admin/nav/compute
    Trigger the EOD NAV calculation manually.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        try:
            logger.info(f"Manual NAV computation triggered by admin {request.user.email}")
            snapshot_result = take_vault_snapshot()
            nav_result = publish_daily_nav()
            
            return Response({
                "message": "NAV calculated successfully.",
                "nav_inr": nav_result.get("nav_inr"),
                "nav_usd": nav_result.get("nav_usd"),
                "date": nav_result.get("date"),
            })
        except Exception as e:
            logger.exception("Manual NAV computation failed.")
            return Response({"error": str(e)}, status=500)
