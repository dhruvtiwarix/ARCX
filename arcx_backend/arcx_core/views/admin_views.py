"""
ARCX Admin Operations Views - Phase 11
----------------------------------------
Superuser-only endpoints for the ARCX Treasury team.
Enforces IsAdminUser strictly.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import serializers as drf_serializers
from django.db import transaction
from drf_spectacular.utils import (
    extend_schema, OpenApiExample, OpenApiResponse, inline_serializer
)

from arcx_core.models import User, Wallet, KYCRecord, CircuitBreakerLog
from domain.valuation import ValuationEngine
from domain.oracle import MultiSourceOracle
from arcx_core.tasks.eod_tasks import take_vault_snapshot, publish_daily_nav

logger = logging.getLogger("arcx.views.admin")

# -- Inline schemas -----------------------------------------------------------
_ErrorSchema = inline_serializer(
    name="AdminErrorResponse",
    fields={
        "error": drf_serializers.CharField(),
    },
)

_AdminUserSchema = inline_serializer(
    name="AdminUserEntry",
    fields={
        "id":             drf_serializers.UUIDField(),
        "email":          drf_serializers.EmailField(),
        "full_name":      drf_serializers.CharField(),
        "kyc_status":     drf_serializers.CharField(),
        "is_active":      drf_serializers.BooleanField(),
        "created_at":     drf_serializers.DateTimeField(),
        "arcx_balance":   drf_serializers.FloatField(),
        "cost_basis_inr": drf_serializers.FloatField(),
    },
)

_AdminUserListSchema = inline_serializer(
    name="AdminUserListResponse",
    fields={"users": drf_serializers.ListField(child=drf_serializers.DictField(), help_text="List of user records")},
)

_PendingKYCEntry = inline_serializer(
    name="PendingKYCEntry",
    fields={
        "id":            drf_serializers.UUIDField(),
        "user_email":    drf_serializers.EmailField(),
        "tier":          drf_serializers.CharField(),
        "document_type": drf_serializers.CharField(),
        "document_ref":  drf_serializers.CharField(),
        "created_at":    drf_serializers.DateTimeField(),
    },
)

_PendingKYCListSchema = inline_serializer(
    name="PendingKYCListResponse",
    fields={"pending_kyc": drf_serializers.ListField(child=drf_serializers.DictField(), help_text="List of pending KYC records")},
)

_KYCActionRequestSchema = inline_serializer(
    name="KYCActionRequest",
    fields={
        "record_id": drf_serializers.UUIDField(help_text="UUID of the KYCRecord to action"),
        "action":    drf_serializers.ChoiceField(
            choices=["approve", "reject"],
            help_text="approve -> sets user kyc_status=approved | reject -> sets kyc_status=rejected",
        ),
    },
)

_KYCActionResponseSchema = inline_serializer(
    name="KYCActionResponse",
    fields={"message": drf_serializers.CharField()},
)

_NAVComputeResponseSchema = inline_serializer(
    name="NAVComputeResponse",
    fields={
        "message": drf_serializers.CharField(),
        "nav_inr": drf_serializers.DecimalField(max_digits=20, decimal_places=4, allow_null=True),
        "nav_usd": drf_serializers.DecimalField(max_digits=20, decimal_places=8, allow_null=True),
        "date":    drf_serializers.DateField(allow_null=True),
    },
)


class AdminUserListView(APIView):
    """
    GET /api/v1/admin/users
    Returns a list of all users and their basic wallet/KYC info.
    """
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin"],
        operation_id="admin_user_list",
        summary="List all users (staff only)",
        description=(
            "Returns the 100 most recently created users with their wallet balances "
            "and KYC status. **Requires Django `is_staff=True`.**\n\n"
            "Use for treasury operations, support investigations, and compliance audits."
        ),
        responses={
            200: _AdminUserListSchema,
            403: OpenApiResponse(response=_ErrorSchema, description="Not a staff user"),
            401: OpenApiResponse(response=_ErrorSchema, description="JWT missing or expired"),
        },
    )
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

    @extend_schema(
        tags=["Admin"],
        operation_id="admin_kyc_list",
        summary="List pending KYC submissions (staff only)",
        description=(
            "Returns all KYC records with `status=pending`, ordered oldest-first "
            "(FIFO review queue). **Requires Django `is_staff=True`.**"
        ),
        responses={
            200: _PendingKYCListSchema,
            403: OpenApiResponse(response=_ErrorSchema, description="Not a staff user"),
            401: OpenApiResponse(response=_ErrorSchema, description="JWT missing or expired"),
        },
    )
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

    @extend_schema(
        tags=["Admin"],
        operation_id="admin_kyc_action",
        summary="Approve or reject a KYC submission (staff only)",
        description=(
            "Approves or rejects a pending KYC record and updates the user's "
            "`kyc_status` atomically. **Requires Django `is_staff=True`.**\n\n"
            "- `approve` → user gains deposit/withdraw/transfer access\n"
            "- `reject` → user stays blocked; they may resubmit\n\n"
            "All state changes are wrapped in a database transaction and logged."
        ),
        request=_KYCActionRequestSchema,
        responses={
            200: _KYCActionResponseSchema,
            400: OpenApiResponse(
                response=_ErrorSchema,
                description="Invalid action or KYC record is not pending",
                examples=[
                    OpenApiExample("Not pending", value={"error": "KYC record is not pending."}),
                    OpenApiExample("Bad action",  value={"error": "Action must be approve or reject."}),
                ],
            ),
            404: OpenApiResponse(response=_ErrorSchema, description="KYC record not found"),
            403: OpenApiResponse(response=_ErrorSchema, description="Not a staff user"),
        },
        examples=[
            OpenApiExample(
                "Approve KYC",
                request_only=True,
                value={"record_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "action": "approve"},
            ),
            OpenApiExample(
                "Reject KYC",
                request_only=True,
                value={"record_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "action": "reject"},
            ),
        ],
    )
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

    @extend_schema(
        tags=["Admin"],
        operation_id="admin_nav_compute",
        summary="Trigger manual NAV computation (staff only)",
        description=(
            "Manually triggers the end-of-day vault snapshot and NAV publication pipeline. "
            "Normally this runs automatically on a schedule. Use this for:\n\n"
            "- Forcing a same-day NAV update after large inflows\n"
            "- Re-running after an oracle failure\n"
            "- Testing the EOD pipeline in staging\n\n"
            "**Requires Django `is_staff=True`.** All operations are logged."
        ),
        request=None,
        responses={
            200: _NAVComputeResponseSchema,
            500: OpenApiResponse(
                response=_ErrorSchema,
                description="NAV computation failed — check oracle availability",
            ),
            403: OpenApiResponse(response=_ErrorSchema, description="Not a staff user"),
        },
        examples=[
            OpenApiExample(
                "NAV computed successfully",
                response_only=True,
                status_codes=["200"],
                value={
                    "message": "NAV calculated successfully.",
                    "nav_inr": "99.8000",
                    "nav_usd": "1.19520000",
                    "date":    "2025-06-01",
                },
            ),
        ],
    )
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
