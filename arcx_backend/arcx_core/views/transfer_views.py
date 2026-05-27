"""
ARCX Transfer View - Phase 3
------------------------------
Endpoint:
  POST /api/v1/transfer/
  Headers: Idempotency-Key: <uuid>

Body:
  {
    "to_user_email": "friend@example.com",
    "amount_arcx":   "10.5",
    "note":          "Splitting dinner"      <- optional
  }

Response:
  {
    "transaction_id":     "...",
    "amount_sent":        "10.5",
    "recipient_email":    "friend@example.com",
    "new_balance":        "89.5",
    "fee":                "0.00"
  }

The fee is always 0.00. This is a feature, not an oversight.
SWIFT charges $25-50 and takes 3-5 days.
ARCX charges Rs.0 and takes <100ms.
This is the headline feature. Make it visible in the response.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import (
    extend_schema, OpenApiExample, OpenApiResponse,
    OpenApiParameter, inline_serializer
)
from drf_spectacular.types import OpenApiTypes

from arcx_core.permissions import IsKYCApproved, IsWalletActive, IsCircuitBreakerClear
from arcx_core.serializers import TransferRequestSerializer
from arcx_core.services.transfer_service import TransferService
from arcx_core.services.wallet_service import WalletService
from arcx_core.services.b2b_service import B2BService

logger = logging.getLogger("arcx.views.transfer")


def _user_id(request) -> str:
    return request.user.username


# -- Inline schemas -----------------------------------------------------------
_ErrorSchema = inline_serializer(
    name="TransferErrorResponse",
    fields={
        "error": drf_serializers.CharField(),
        "code":  drf_serializers.CharField(),
    },
)

_TransferResponseSchema = inline_serializer(
    name="TransferResponse",
    fields={
        "transaction_id":  drf_serializers.UUIDField(help_text="Unique transaction ID"),
        "amount_sent":     drf_serializers.DecimalField(max_digits=28, decimal_places=18, help_text="ARCX tokens sent"),
        "recipient_email": drf_serializers.EmailField(help_text="Recipient's email address"),
        "new_balance":     drf_serializers.DecimalField(max_digits=28, decimal_places=18, help_text="Sender's updated ARCX balance"),
        "fee":             drf_serializers.CharField(help_text="Always 0.00 — zero-fee transfers"),
        "note":            drf_serializers.CharField(help_text="Optional memo attached to this transfer"),
    },
)


class TransferView(APIView):
    """
    POST /api/v1/transfer/

    Zero-fee, real-time ARCX transfer between any two ARCX users.
    Both wallets update atomically in one DB transaction.
    """
    permission_classes = [IsAuthenticated, IsKYCApproved, IsWalletActive, IsCircuitBreakerClear]

    @extend_schema(
        tags=["Transfer"],
        operation_id="transfer_arcx",
        summary="Transfer ARCX to another user",
        description=(
            "Sends ARCX tokens from the authenticated user to any other ARCX user "
            "identified by email. Both wallets are updated atomically in a single "
            "database transaction — no partial states.\n\n"
            "**Zero fees.** SWIFT charges $25-50 and takes 3-5 days. "
            "ARCX charges ₹0 and settles in under 100ms.\n\n"
            "**Idempotency:** Include `Idempotency-Key` UUID header to prevent "
            "duplicate transfers on retry.\n\n"
            "**Requirements:** KYC approved + active (non-frozen) wallet."
        ),
        request=TransferRequestSerializer,
        responses={
            201: _TransferResponseSchema,
            400: OpenApiResponse(
                response=_ErrorSchema,
                description="Insufficient balance, recipient not found, or self-transfer attempted",
                examples=[
                    OpenApiExample(
                        "Insufficient balance",
                        value={"error": "Insufficient ARCX balance.", "code": "INSUFFICIENT_BALANCE"},
                    ),
                    OpenApiExample(
                        "Recipient not found",
                        value={"error": "Recipient not found or inactive.", "code": "RECIPIENT_NOT_FOUND"},
                    ),
                ],
            ),
            403: OpenApiResponse(response=_ErrorSchema, description="KYC not approved, wallet frozen, or circuit breaker active"),
            401: OpenApiResponse(response=_ErrorSchema, description="JWT missing or expired"),
        },
        examples=[
            OpenApiExample(
                "Transfer 10.5 ARCX",
                request_only=True,
                value={
                    "to_user_email": "priya@example.com",
                    "amount_arcx":   "10.500000000000000000",
                    "note":          "Splitting dinner",
                },
            ),
            OpenApiExample(
                "Transfer success",
                response_only=True,
                status_codes=["201"],
                value={
                    "transaction_id":  "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "amount_sent":     "10.500000000000000000",
                    "recipient_email": "priya@example.com",
                    "new_balance":     "89.500000000000000000",
                    "fee":             "0.00",
                    "note":            "Splitting dinner",
                },
            ),
        ],
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                location=OpenApiParameter.HEADER,
                required=True,
                type=OpenApiTypes.UUID,
                description="A unique UUID v4 per request. Prevents duplicate transfers on retry.",
            ),
        ],
    )
    def post(self, request):
        serializer = TransferRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # 1. Validate UPI-Style PIN
        B2BService.validate_transaction_pin(request.user, data["pin"])

        transfer_service = TransferService()
        tx = transfer_service.transfer(
            sender_user_id  = _user_id(request),
            recipient_email = data["to_user_email"],
            amount_arcx     = data["amount_arcx"],
        )

        wallet_service = WalletService()
        wallet         = wallet_service.get_wallet(_user_id(request))

        return Response(
            {
                "transaction_id":  str(tx.id),
                "amount_sent":     str(data["amount_arcx"]),
                "recipient_email": data["to_user_email"],
                "new_balance":     str(wallet.arcx_balance),
                "fee":             "0.00",
                "note":            data.get("note", ""),
            },
            status=status.HTTP_201_CREATED,
        )