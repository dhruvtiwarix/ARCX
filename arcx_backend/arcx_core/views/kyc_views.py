"""
ARCX KYC Views - Phase 6
--------------------------
Goes in: arcx_backend/arcx_core/views/kyc_views.py

Endpoints:
  POST /api/v1/kyc/submit  -> Submit KYC document reference
  GET  /api/v1/kyc/status  -> Current KYC tier + all submitted records

WHY DOCUMENT REFERENCE, NOT DOCUMENT UPLOAD?
  Storing documents directly (even encrypted) in PostgreSQL is wrong for:
    - Scale: a 4MB Aadhaar PDF x 10,000 users = 40GB in your DB
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
from rest_framework import status, serializers as drf_serializers
from drf_spectacular.utils import (
    extend_schema, OpenApiExample, OpenApiResponse, inline_serializer
)

from arcx_core.serializers_auth import KYCSubmitSerializer
from arcx_core.services.kyc_service import KYCService, KYCAlreadyApprovedError

logger = logging.getLogger("arcx.views.kyc")


def _user_id(request) -> str:
    return request.user.username


# -- Inline schemas -----------------------------------------------------------
_ErrorSchema = inline_serializer(
    name="KYCErrorResponse",
    fields={
        "error": drf_serializers.CharField(),
        "code":  drf_serializers.CharField(),
    },
)

_KYCSubmitResponseSchema = inline_serializer(
    name="KYCSubmitResponse",
    fields={
        "kyc_id":      drf_serializers.UUIDField(help_text="Unique ID of the KYC record"),
        "tier":        drf_serializers.CharField(help_text="KYC tier that was approved: tier_1, tier_2, or tier_3"),
        "status":      drf_serializers.CharField(help_text="Status of this KYC record: approved, pending, or rejected"),
        "verified_at": drf_serializers.DateTimeField(allow_null=True),
        "message":     drf_serializers.CharField(help_text="Human-readable summary of the approval with daily limit"),
    },
)

_KYCRecordItemSchema = inline_serializer(
    name="KYCRecordItem",
    fields={
        "id":            drf_serializers.UUIDField(),
        "tier":          drf_serializers.CharField(),
        "status":        drf_serializers.CharField(),
        "document_type": drf_serializers.CharField(),
        "verified_at":   drf_serializers.DateTimeField(allow_null=True),
        "submitted_at":  drf_serializers.DateTimeField(),
    },
)

_KYCStatusResponseSchema = inline_serializer(
    name="KYCStatusResponse",
    fields={
        "kyc_status":      drf_serializers.CharField(help_text="Overall KYC status on the user account"),
        "highest_tier":    drf_serializers.CharField(allow_null=True, help_text="Highest approved KYC tier"),
        "daily_limit_inr": drf_serializers.CharField(help_text="Current daily transaction limit based on KYC tier"),
        "records":         drf_serializers.ListField(
            child=drf_serializers.DictField(help_text="KYC record: id, tier, status, document_type, verified_at, submitted_at"),
            help_text="All KYC submissions for this user",
        ),
    },
)


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

    @extend_schema(
        tags=["KYC"],
        operation_id="kyc_submit",
        summary="Submit KYC document for verification",
        description=(
            "Submits a KYC document reference for verification. ARCX stores only the "
            "external reference ID returned by the KYC provider (DigiLocker, Onfido, etc.) — "
            "never the raw document itself.\n\n"
            "**Tier limits:**\n"
            "- `tier_1` (Aadhaar/DL) → ₹10,000/day\n"
            "- `tier_2` (PAN/Passport) → ₹1,00,000/day\n"
            "- `tier_3` (Full address proof) → Unlimited\n\n"
            "**Demo:** Pass any string as `document_ref` (e.g. `DEMO_REF_001`) "
            "to test the flow without a real KYC provider."
        ),
        request=KYCSubmitSerializer,
        responses={
            201: _KYCSubmitResponseSchema,
            409: OpenApiResponse(
                response=_ErrorSchema,
                description="KYC already approved for this user",
                examples=[
                    OpenApiExample(
                        "Already approved",
                        value={"error": "KYC is already approved.", "code": "KYC_ALREADY_APPROVED"},
                    )
                ],
            ),
            400: OpenApiResponse(response=_ErrorSchema, description="Validation error — invalid tier/document_type combination"),
            401: OpenApiResponse(response=_ErrorSchema, description="JWT missing or expired"),
        },
        examples=[
            OpenApiExample(
                "Tier 1 Aadhaar submission",
                request_only=True,
                value={
                    "tier":          "tier_1",
                    "document_type": "aadhaar",
                    "document_ref":  "DIGILOCKER_REF_ABC123",
                },
            ),
            OpenApiExample(
                "KYC approved",
                response_only=True,
                status_codes=["201"],
                value={
                    "kyc_id":      "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "tier":        "tier_1",
                    "status":      "approved",
                    "verified_at": "2025-06-01T15:30:00Z",
                    "message":     "KYC tier_1 approved. You can now transact up to Rs.10,000/day.",
                },
            ),
        ],
    )
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
            "tier_1": "Rs.10,000",
            "tier_2": "Rs.1,00,000",
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

    Returns full KYC status -- current tier, daily limit, all past submissions.

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

    @extend_schema(
        tags=["KYC"],
        operation_id="kyc_status",
        summary="Get current KYC status and history",
        description=(
            "Returns the user's current overall KYC status, the highest approved tier, "
            "the resulting daily transaction limit, and the full list of all KYC submissions."
        ),
        responses={
            200: _KYCStatusResponseSchema,
            401: OpenApiResponse(response=_ErrorSchema, description="JWT missing or expired"),
        },
        examples=[
            OpenApiExample(
                "KYC status response",
                response_only=True,
                status_codes=["200"],
                value={
                    "kyc_status":      "approved",
                    "highest_tier":    "tier_1",
                    "daily_limit_inr": "Rs.10,000",
                    "records": [
                        {
                            "id":            "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                            "tier":          "tier_1",
                            "status":        "approved",
                            "document_type": "aadhaar",
                            "verified_at":   "2025-06-01T15:30:00Z",
                            "submitted_at":  "2025-06-01T15:29:50Z",
                        }
                    ],
                },
            ),
        ],
    )
    def get(self, request):
        service = KYCService()
        result  = service.get_status(_user_id(request))
        return Response(result)