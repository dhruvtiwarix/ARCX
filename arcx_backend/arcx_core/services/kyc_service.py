"""
ARCX KYC Service — Phase 6
-----------------------------
Goes in: arcx_backend/arcx_core/services/kyc_service.py

KYC = Know Your Customer. Legally required by RBI / PMLA for any
Indian financial product that handles real INR.

TIER MODEL (matches models.py KYCRecord.Tier):
  Tier 1 — Aadhaar OTP only.    Daily limit: ₹10,000
  Tier 2 — PAN + Selfie.        Daily limit: ₹1,00,000
  Tier 3 — Full address proof.  Daily limit: Unlimited

WHAT WE STORE VS WHAT WE DON'T:
  We store:    document_ref (the ID from the KYC provider's API)
  We don't:    The actual document image, Aadhaar number, PAN number

  Actual documents go to encrypted S3/GCS with IAM access controls.
  We store only the external reference. This limits our liability if
  we're ever breached — we have reference IDs, not documents.

APPROVAL FLOW (MVP / Phase 6):
  User submits → KYCRecord created with status=pending
  Admin reviews (or auto-approve for demo) → status=approved
  User's daily limits automatically unlock based on tier

PRODUCTION UPGRADE:
  Connect to DigiLocker / Aadhaar XML / PAN verification API.
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
        user_id:       str,
        tier:          str,
        document_type: str,
        document_ref:  str,
    ) -> KYCRecord:
        """
        Submit a KYC document for a user.

        In production this would call DigiLocker or Onfido.
        For Phase 6 / demo, we auto-approve so the full flow is testable.

        Args:
            user_id:       ARCX User UUID
            tier:          "tier_1" | "tier_2" | "tier_3"
            document_type: "aadhaar" | "pan" | "passport" | "dl"
            document_ref:  External reference ID from KYC provider

        Returns:
            The created KYCRecord (status=approved for demo)
        """
        user = ArcxUser.objects.get(id=user_id, deleted_at__isnull=True)

        # Check if this tier is already approved — no-op resubmission
        already_approved = KYCRecord.objects.filter(
            user   = user,
            tier   = tier,
            status = KYCRecord.Status.APPROVED,
            deleted_at__isnull = True,
        ).exists()

        if already_approved:
            raise KYCAlreadyApprovedError(
                f"KYC {tier} is already approved for this account."
            )

        with transaction.atomic():
            # Create the KYC record
            kyc = KYCRecord.objects.create(
                user          = user,
                tier          = tier,
                status        = KYCRecord.Status.PENDING,
                document_type = document_type,
                document_ref  = document_ref,
            )

            # ── AUTO-APPROVE FOR DEMO / MVP ───────────────────────────────
            # In production: remove these lines, connect KYC provider webhook instead
            kyc.status      = KYCRecord.Status.APPROVED
            kyc.verified_at = timezone.now()
            kyc.save(update_fields=["status", "verified_at"])

            # Upgrade the user's kyc_status on the User record
            # (highest approved tier wins)
            user.kyc_status = ArcxUser.KycStatus.APPROVED
            user.save(update_fields=["kyc_status", "updated_at"])

        logger.info(
            "KYC approved: user_id=%s tier=%s doc_type=%s",
            user_id, tier, document_type,
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

        # Find highest approved tier
        approved_tiers = [
            r.tier for r in records if r.status == KYCRecord.Status.APPROVED
        ]
        highest_tier = max(approved_tiers) if approved_tiers else None

        # Daily limits by tier
        limits = {
            "tier_1": "10,000",
            "tier_2": "1,00,000",
            "tier_3": "Unlimited",
        }

        return {
            "kyc_status":    user.kyc_status,
            "highest_tier":  highest_tier,
            "daily_limit_inr": limits.get(highest_tier, "0 — KYC required"),
            "records": [
                {
                    "id":            str(r.id),
                    "tier":          r.tier,
                    "status":        r.status,
                    "document_type": r.document_type,
                    "verified_at":   r.verified_at.isoformat() if r.verified_at else None,
                    "submitted_at":  r.created_at.isoformat(),
                }
                for r in records
            ],
        }