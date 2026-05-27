"""
ARCX Wallet Views - Phase 3
------------------------------
These are thin views. The pattern is always:
  1. Deserialize + validate input
  2. Call service
  3. Serialize + return output

No business logic here. The view's only job is HTTP.

Endpoints:
  GET  /api/v1/wallet/          -> wallet balance + unrealized P&L
  POST /api/v1/wallet/deposit   -> INR -> ARCX
  POST /api/v1/wallet/withdraw  -> ARCX -> INR
  GET  /api/v1/wallet/history   -> transaction history
"""

import logging
from decimal import Decimal
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
from arcx_core.serializers import (
    DepositRequestSerializer,
    WithdrawRequestSerializer,
    WalletResponseSerializer,
    TransactionResponseSerializer,
)
from arcx_core.services.wallet_service import WalletService

logger = logging.getLogger("arcx.views.wallet")

# -- Shared inline schemas ----------------------------------------------------
_ErrorSchema = inline_serializer(
    name="WalletErrorResponse",
    fields={
        "error": drf_serializers.CharField(),
        "code":  drf_serializers.CharField(),
    },
)

_DepositResponseSchema = inline_serializer(
    name="DepositResponse",
    fields={
        "transaction_id": drf_serializers.UUIDField(help_text="Unique transaction ID"),
        "arcx_credited":  drf_serializers.DecimalField(max_digits=28, decimal_places=18, help_text="ARCX tokens credited to wallet"),
        "nav_at_tx":      drf_serializers.DecimalField(max_digits=20, decimal_places=4,  help_text="NAV price used for this conversion (INR)"),
        "new_balance":    drf_serializers.DecimalField(max_digits=28, decimal_places=18, help_text="Updated ARCX wallet balance"),
    },
)

_WithdrawResponseSchema = inline_serializer(
    name="WithdrawResponse",
    fields={
        "transaction_id": drf_serializers.UUIDField(),
        "gross_inr":      drf_serializers.DecimalField(max_digits=20, decimal_places=4, help_text="INR before fees"),
        "fee_inr":        drf_serializers.DecimalField(max_digits=20, decimal_places=4, help_text="Redemption fee charged"),
        "inr_returned":   drf_serializers.DecimalField(max_digits=20, decimal_places=4, help_text="Net INR returned to user"),
        "nav_at_tx":      drf_serializers.DecimalField(max_digits=20, decimal_places=4, help_text="NAV price used for this conversion (INR)"),
        "new_balance":    drf_serializers.DecimalField(max_digits=28, decimal_places=18, help_text="Updated ARCX wallet balance"),
    },
)

_TransactionListSchema = inline_serializer(
    name="TransactionListResponse",
    fields={
        "transactions": drf_serializers.ListField(
            child=drf_serializers.DictField(),
            help_text="List of transaction records (id, tx_type, amount_arcx, amount_inr, fee_inr, nav_at_tx, status, created_at)",
        ),
        "count":        drf_serializers.IntegerField(),
    },
)


def _user_id(request) -> str:
    """Extract ARCX user UUID from JWT subject claim."""
    return request.user.username   # JWT sub = ARCX user UUID


class WalletBalanceView(APIView):
    """
    GET /api/v1/wallet/

    Returns the user's current balance and unrealized P&L.
    No KYC requirement -- even pending users can see their balance.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Wallet"],
        operation_id="wallet_balance",
        summary="Get wallet balance and P&L",
        description=(
            "Returns the authenticated user's ARCX token balance, cost basis, "
            "and real-time unrealized P&L (calculated using the current oracle NAV). "
            "\n\n`unrealized_pnl_inr` may return `null` if the oracle is temporarily "
            "unavailable — the balance is always returned."
        ),
        responses={
            200: WalletResponseSerializer,
            401: OpenApiResponse(response=_ErrorSchema, description="JWT missing or expired"),
        },
    )
    def get(self, request):
        service = WalletService()
        wallet  = service.get_wallet(_user_id(request))

        # Fetch current NAV to compute unrealized P&L
        # If oracle is down, we still return the balance (P&L shows null)
        current_nav = None
        try:
            prices      = service._fetch_prices()
            current_nav = service._get_nav_inr(prices)
        except Exception:
            logger.warning("Could not fetch NAV for P&L calculation. Returning balance only.")

        serializer = WalletResponseSerializer(
            wallet,
            context={"current_nav_inr": current_nav},
        )
        return Response(serializer.data)


class DepositView(APIView):
    """
    POST /api/v1/wallet/deposit
    Headers: Idempotency-Key: <uuid>

    Body:
      { "amount_inr": "5000.00" }

    Response:
      {
        "transaction_id": "...",
        "arcx_credited":  "49.123456...",
        "nav_at_tx":      "101.80",
        "new_balance":    "49.123456..."
      }
    """
    permission_classes = [IsAuthenticated, IsKYCApproved, IsCircuitBreakerClear]

    @extend_schema(
        tags=["Wallet"],
        operation_id="wallet_deposit",
        summary="Deposit INR -> ARCX",
        description=(
            "Converts INR to ARCX tokens at the current oracle NAV price. "
            "Minimum deposit is ₹100. KYC approval is required.\n\n"
            "**Idempotency:** Include a unique `Idempotency-Key` UUID header. "
            "Replaying the same key returns the original response without double-charging."
        ),
        request=DepositRequestSerializer,
        responses={
            201: _DepositResponseSchema,
            400: OpenApiResponse(response=_ErrorSchema, description="Validation error or oracle failure"),
            403: OpenApiResponse(response=_ErrorSchema, description="KYC not approved or circuit breaker active"),
            401: OpenApiResponse(response=_ErrorSchema, description="JWT missing or expired"),
        },
        examples=[
            OpenApiExample(
                "Deposit 5000 INR",
                request_only=True,
                value={"amount_inr": "5000.00"},
            ),
            OpenApiExample(
                "Deposit success",
                response_only=True,
                status_codes=["201"],
                value={
                    "transaction_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "arcx_credited":  "49.123456789012345678",
                    "nav_at_tx":      "101.80",
                    "new_balance":    "49.123456789012345678",
                },
            ),
        ],
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                location=OpenApiParameter.HEADER,
                required=True,
                type=OpenApiTypes.UUID,
                description="A unique UUID v4 per request. Prevents duplicate transactions on retry.",
            ),
        ],
    )
    def post(self, request):
        serializer = DepositRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = WalletService()
        tx      = service.deposit(
            user_id    = _user_id(request),
            amount_inr = serializer.validated_data["amount_inr"],
        )

        wallet = service.get_wallet(_user_id(request))

        return Response(
            {
                "transaction_id": str(tx.id),
                "arcx_credited":  str(tx.amount_arcx),
                "nav_at_tx":      str(tx.nav_at_tx),
                "new_balance":    str(wallet.arcx_balance),
            },
            status=status.HTTP_201_CREATED,
        )


class WithdrawView(APIView):
    """
    POST /api/v1/wallet/withdraw
    Headers: Idempotency-Key: <uuid>

    Body:
      { "amount_arcx": "10.5" }

    Response:
      {
        "transaction_id": "...",
        "inr_returned":   "1068.90",
        "nav_at_tx":      "101.80",
        "new_balance":    "38.623456..."
      }
    """
    permission_classes = [IsAuthenticated, IsKYCApproved, IsWalletActive, IsCircuitBreakerClear]

    @extend_schema(
        tags=["Wallet"],
        operation_id="wallet_withdraw",
        summary="Withdraw ARCX -> INR",
        description=(
            "Redeems ARCX tokens back to INR at the current oracle NAV price. "
            "A redemption fee is deducted — see `fee_inr` in the response. "
            "KYC approval and an active (non-frozen) wallet are both required.\n\n"
            "**Idempotency:** Include `Idempotency-Key` UUID header to prevent double-redemptions."
        ),
        request=WithdrawRequestSerializer,
        responses={
            201: _WithdrawResponseSchema,
            400: OpenApiResponse(response=_ErrorSchema, description="Insufficient balance or validation error"),
            403: OpenApiResponse(response=_ErrorSchema, description="KYC not approved, wallet frozen, or circuit breaker active"),
            401: OpenApiResponse(response=_ErrorSchema, description="JWT missing or expired"),
        },
        examples=[
            OpenApiExample(
                "Withdraw 10.5 ARCX",
                request_only=True,
                value={"amount_arcx": "10.5"},
            ),
            OpenApiExample(
                "Withdraw success",
                response_only=True,
                status_codes=["201"],
                value={
                    "transaction_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "gross_inr":      "1069.25",
                    "fee_inr":        "0.35",
                    "inr_returned":   "1068.90",
                    "nav_at_tx":      "101.80",
                    "new_balance":    "38.623456789012345678",
                },
            ),
        ],
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                location=OpenApiParameter.HEADER,
                required=True,
                type=OpenApiTypes.UUID,
                description="A unique UUID v4 per request. Prevents duplicate redemptions on retry.",
            ),
        ],
    )
    def post(self, request):
        serializer = WithdrawRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = WalletService()
        tx      = service.withdraw(
            user_id     = _user_id(request),
            amount_arcx = serializer.validated_data["amount_arcx"],
        )

        wallet = service.get_wallet(_user_id(request))

        return Response(
            {
                "transaction_id": str(tx.id),
                "gross_inr":      str((tx.amount_inr + tx.fee_inr).quantize(Decimal("0.0001"))),
                "fee_inr":        str(tx.fee_inr),
                "inr_returned":   str(tx.amount_inr),
                "nav_at_tx":      str(tx.nav_at_tx),
                "new_balance":    str(wallet.arcx_balance),
            },
            status=status.HTTP_201_CREATED,
        )


class TransactionHistoryView(APIView):
    """
    GET /api/v1/wallet/history?limit=20

    Returns the last N transactions for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Wallet"],
        operation_id="wallet_history",
        summary="Get transaction history",
        description=(
            "Returns the most recent N transactions for the authenticated user, "
            "ordered newest-first. Includes deposits, withdrawals, transfers, and dividends. "
            "Maximum `limit` is capped at 100."
        ),
        parameters=[
            OpenApiParameter(
                name="limit",
                location=OpenApiParameter.QUERY,
                type=OpenApiTypes.INT,
                required=False,
                default=20,
                description="Number of transactions to return. Default 20, max 100.",
            ),
        ],
        responses={
            200: _TransactionListSchema,
            401: OpenApiResponse(response=_ErrorSchema, description="JWT missing or expired"),
        },
    )
    def get(self, request):
        limit = min(int(request.query_params.get("limit", 20)), 100)

        service = WalletService()
        txns    = service.get_transaction_history(_user_id(request), limit=limit)

        serializer = TransactionResponseSerializer(txns, many=True)
        return Response({"transactions": serializer.data, "count": len(serializer.data)})