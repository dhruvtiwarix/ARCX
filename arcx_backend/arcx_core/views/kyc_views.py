"""
ARCX KYC Views — Phase 6
--------------------------
Goes in: arcx_backend/arcx_core/views/kyc_views.py

Endpoints:
  POST /api/v1/kyc/submit  → Submit KYC document reference
  GET  /api/v1/kyc/status  → Current KYC tier + all submitted records

WHY DOCUMENT REFERENCE, NOT DOCUMENT UPLOAD?
  Storing documents directly (even encrypted) in PostgreSQL is wrong for:
    - Scale: a 4MB Aadhaar PDF × 10,000 users = 40GB in your DB
    - Compliance: documents must be stored in certified encrypted storage
    - Security: DB breach = no documents exposed (only external refs)

  In production:
    1. Frontend uploads to S3 pre-signed URL directly (never touches your server)
    2. S3 triggers Lambda which calls Onfido / DigiLocker / CKYC API
    3. API returns a reference ID
    4. Frontend sends that reference ID to /api/v1/kyc/submit
    5. You store the reference. Done.

  For Phase 6 / demo, the "document_ref" field accepts any string
  (e.g., "DEMO_REF_001") so the full flow is testable without a real KYC API.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from arcx_core.serializers_auth import KYCSubmitSerializer
from arcx_core.services.kyc_service import KYCService, KYCAlreadyApprovedError

logger = logging.getLogger("arcx.views.kyc")


def _user_id(request) -> str:
    return request.user.username


class KYCSubmitView(APIView):
    """
    POST /api/v1/kyc/submit

    Body:
      {
        "tier":          "tier_1",
        "document_type": "aadhaar",
        "document_ref":  "DIGILOCKER_REF_ABC123"
      }

    Response:
      {
        "kyc_id":      "uuid...",
        "tier":        "tier_1",
        "status":      "approved",
        "verified_at": "2025-06-01T15:30:00Z",
        "message":     "KYC tier_1 approved. You can now deposit up to Rs.10,000/day."
      }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = KYCSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            service = KYCService()
            kyc     = service.submit(
                user_id       = _user_id(request),
                tier          = data["tier"],
                document_type = data["document_type"],
                document_ref  = data["document_ref"],
            )
        except KYCAlreadyApprovedError as e:
            return Response(
                {"error": str(e), "code": "KYC_ALREADY_APPROVED"},
                status=status.HTTP_409_CONFLICT,
            )

        daily_limits = {
            "tier_1": "₹10,000",
            "tier_2": "₹1,00,000",
            "tier_3": "Unlimited",
        }
        limit = daily_limits.get(kyc.tier, "")

        return Response(
            {
                "kyc_id":      str(kyc.id),
                "tier":        kyc.tier,
                "status":      kyc.status,
                "verified_at": kyc.verified_at.isoformat() if kyc.verified_at else None,
                "message":     (
                    f"KYC {kyc.tier} approved. "
                    f"You can now transact up to {limit}/day."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class KYCStatusView(APIView):
    """
    GET /api/v1/kyc/status

    Returns full KYC status — current tier, daily limit, all past submissions.

    Response:
      {
        "kyc_status":      "approved",
        "highest_tier":    "tier_1",
        "daily_limit_inr": "10,000",
        "records": [
          {
            "id":            "uuid...",
            "tier":          "tier_1",
            "status":        "approved",
            "document_type": "aadhaar",
            "verified_at":   "2025-06-01T15:30:00Z",
            "submitted_at":  "2025-06-01T15:29:50Z"
          }
        ]
      }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = KYCService()
        result  = service.get_status(_user_id(request))
        return Response(result)