"""
ARCX Serializers — Phase 3
-----------------------------
Serializers do two jobs:
  1. INPUT: Validate and clean incoming request data
  2. OUTPUT: Shape model data into the JSON response

Design principle: The view should never touch raw request.data directly.
request.data goes into a serializer. If serializer.is_valid() passes,
only then does the service layer get called.

Why Decimal for amounts?
  The COERCE_DECIMAL_TO_STRING setting in DRF means DecimalField values
  are sent as strings in JSON: "amount_inr": "5000.00"
  This is intentional. JavaScript's float64 loses precision above 2^53.
  A frontend doing JSON.parse on {"amount": 1000000000000000.1} will
  silently get the wrong number. String → Decimal on the backend is exact.
"""

from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from arcx_core.models import User, Wallet, Transaction, NAVHistory, VaultSnapshot
from rest_framework import serializers
from arcx_core.models import User, Wallet, KYCRecord
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes

# ─────────────────────────────────────────────────────────────────────────────
# Wallet Serializers
# ─────────────────────────────────────────────────────────────────────────────

class DepositRequestSerializer(serializers.Serializer):
    """
    Validates a deposit request.

    amount_inr: How much INR the user wants to convert to ARCX.
    Minimum ₹100. No maximum (KYC tier limit enforced in service layer).
    """
    amount_inr = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        min_value=Decimal("100.00"),
    )

    def validate_amount_inr(self, value):
        # Extra check: reject values with too many decimal places for INR
        if value != round(value, 2):
            raise serializers.ValidationError("Amount must have at most 2 decimal places.")
        return value


class WithdrawRequestSerializer(serializers.Serializer):
    """
    Validates a withdrawal request.

    amount_arcx: How many ARCX tokens to sell back.
    Minimum 0.01 ARCX.
    """
    amount_arcx = serializers.DecimalField(
        max_digits=28,
        decimal_places=18,
        min_value=Decimal("0.01"),
    )


class WalletResponseSerializer(serializers.ModelSerializer):
    """
    Shapes wallet data for the response.
    Never exposes internal fields like is_frozen or cost_basis directly.
    unrealized_pnl_inr is a computed field — not stored in DB.
    """
    user_email       = serializers.EmailField(source="user.email", read_only=True)
    unrealized_pnl_inr = serializers.SerializerMethodField()

    class Meta:
        model  = Wallet
        fields = [
            "id",
            "user_email",
            "arcx_balance",
            "cost_basis_inr",
            "unrealized_pnl_inr",
            "updated_at",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_unrealized_pnl_inr(self, wallet):
        """
        P&L = (current_value) - (what_you_paid)
        current_value = arcx_balance * current_nav_inr

        current_nav_inr is injected via serializer context from the view.
        If not available (e.g., oracle down), returns None gracefully.
        Returns a decimal string or null.
        """
        current_nav = self.context.get("current_nav_inr")
        if current_nav is None:
            return None
        try:
            current_value = Decimal(str(wallet.arcx_balance)) * Decimal(str(current_nav))
            return str(round(current_value - wallet.cost_basis_inr, 4))
        except (InvalidOperation, TypeError):
            return None


class TransactionResponseSerializer(serializers.ModelSerializer):
    """Output shape for a single transaction."""
    class Meta:
        model  = Transaction
        fields = [
            "id",
            "tx_type",
            "amount_arcx",
            "amount_inr",
            "fee_inr",
            "nav_at_tx",
            "status",
            "settlement_date",
            "created_at",
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Transfer Serializer
# ─────────────────────────────────────────────────────────────────────────────

class TransferRequestSerializer(serializers.Serializer):
    """
    Validates a peer-to-peer ARCX transfer.

    to_user_email: The recipient. We look up their wallet server-side.
                   We never expose wallet IDs to clients.
    amount_arcx:   How much to send.
    note:          Optional message (think UPI "note" field).
    """
    to_user_email = serializers.EmailField()
    amount_arcx   = serializers.DecimalField(
        max_digits=28,
        decimal_places=18,
        min_value=Decimal("0.000001"),
    )
    note = serializers.CharField(max_length=140, required=False, allow_blank=True)

    def validate_to_user_email(self, value):
        # Make sure the recipient exists and is active
        try:
            User.objects.get(
                email=value,
                deleted_at__isnull=True,
                is_active=True,
            )
        except User.DoesNotExist:
            raise serializers.ValidationError("Recipient not found or inactive.")
        return value


# ─────────────────────────────────────────────────────────────────────────────
# Oracle / NAV Serializers
# ─────────────────────────────────────────────────────────────────────────────

class OraclePriceResponseSerializer(serializers.Serializer):
    """
    Response shape for /api/v1/oracle/price.
    Shows full TWAP breakdown per asset + final NAV.
    """
    spy_usd      = serializers.DecimalField(max_digits=12, decimal_places=4)
    tlt_usd      = serializers.DecimalField(max_digits=12, decimal_places=4)
    gld_usd      = serializers.DecimalField(max_digits=12, decimal_places=4)
    usd_inr      = serializers.DecimalField(max_digits=10, decimal_places=4)
    nav_usd      = serializers.DecimalField(max_digits=20, decimal_places=8)
    nav_inr      = serializers.DecimalField(max_digits=20, decimal_places=4)
    spy_change   = serializers.DecimalField(max_digits=10, decimal_places=4, required=False)
    tlt_change   = serializers.DecimalField(max_digits=10, decimal_places=4, required=False)
    gld_change   = serializers.DecimalField(max_digits=10, decimal_places=4, required=False)
    arcx_supply  = serializers.DecimalField(max_digits=28, decimal_places=18, required=False)
    market_open  = serializers.BooleanField(required=False, default=True)
    sources_used = serializers.ListField(child=serializers.CharField())
    fetched_at   = serializers.DateTimeField()


class NAVHistorySerializer(serializers.ModelSerializer):
    """Output shape for historical NAV data (price chart)."""
    class Meta:
        model  = NAVHistory
        fields = ["nav_date", "nav_usd", "nav_inr", "dividend_accrued_inr"]