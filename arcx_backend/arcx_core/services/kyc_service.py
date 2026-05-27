"""
ARCX KYC Service — Phase 6
-----------------------------
Goes in: arcx_backend/arcx_core/services/kyc_service.py

KYC = Know Your Customer. Legally required by RBI / PMLA for any
Indian financial product that handles real INR.

TIER MODEL (matches models.py KYCRecord):
  Single Tier — PAN only. Daily limit: Unlimited.

WHAT WE STORE VS WHAT WE DON'T:
  We store:    pan_number
  We don't:    The actual document image

APPROVAL FLOW (MVP / Phase 6):
  User submits → KYCRecord created with status=pending
  Admin reviews (or auto-approve for demo) → status=approved
  User's daily limits automatically unlock (Unlimited)

PRODUCTION UPGRADE:
  Connect to PAN verification API.
  Webhook callback sets status=approved automatically.
  For ARCX Phase 6, we create the record and auto-approve for demo purposes.
"""

import logging
from django.db import transaction
from django.utils import timezone

from arcx_core.models import User as ArcxUser, KYCRecord

logger = logging.getLogger("arcx.kyc")


class KYCAlreadyApprovedError(Exception):
    code = "KYC_ALREADY_APPROVED"


class KYCService:

    def submit(
        self,
        user_id:    str,
        pan_number: str,
    ) -> KYCRecord:
        """
        Submit a KYC document for a user.

        In production this would call NSDL PAN verification API.
        For Phase 6 / demo, we auto-approve so the full flow is testable.

        Args:
            user_id:    ARCX User UUID
            pan_number: 10 character PAN

        Returns:
            The created KYCRecord (status=approved for demo)
        """
        user = ArcxUser.objects.get(id=user_id, deleted_at__isnull=True)

        # Check if this user is already approved
        already_approved = KYCRecord.objects.filter(
            user   = user,
            status = KYCRecord.Status.APPROVED,
            deleted_at__isnull = True,
        ).exists()

        if already_approved:
            raise KYCAlreadyApprovedError("KYC is already approved for this account.")

        with transaction.atomic():
            # Create the KYC record
            kyc = KYCRecord.objects.create(
                user       = user,
                status     = KYCRecord.Status.PENDING,
                pan_number = pan_number,
            )

            # ── AUTO-APPROVE FOR DEMO / MVP ───────────────────────────────
            kyc.status      = KYCRecord.Status.APPROVED
            kyc.verified_at = timezone.now()
            kyc.save(update_fields=["status", "verified_at"])

            # Upgrade the user's kyc_status on the User record
            user.kyc_status = ArcxUser.KycStatus.APPROVED
            user.save(update_fields=["kyc_status", "updated_at"])

        logger.info(
            "KYC approved: user_id=%s pan_number=%s",
            user_id, pan_number,
        )
        return kyc

    def get_status(self, user_id: str) -> dict:
        """
        Returns the user's current KYC status and all submitted records.
        Used by the status endpoint.
        """
        user = ArcxUser.objects.get(id=user_id, deleted_at__isnull=True)

        records = KYCRecord.objects.filter(
            user=user,
            deleted_at__isnull=True,
        ).order_by("-created_at")

        is_approved = any(r.status == KYCRecord.Status.APPROVED for r in records)

        return {
            "kyc_status":      user.kyc_status,
            "highest_tier":    "approved" if is_approved else None,
            "daily_limit_inr": "Unlimited" if is_approved else "0 — KYC required",
            "records": [
                {
                    "id":            str(r.id),
                    "status":        r.status,
                    "pan_number":    r.pan_number,
                    "verified_at":   r.verified_at.isoformat() if r.verified_at else None,
                    "submitted_at":  r.created_at.isoformat(),
                }
                for r in records
            ],
        }