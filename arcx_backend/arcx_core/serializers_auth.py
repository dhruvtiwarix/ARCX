"""
ARCX Auth & KYC Serializers — Phase 6
----------------------------------------
Goes in: arcx_backend/arcx_core/serializers.py
ADD these classes to the existing serializers.py from Phase 3.
Do not replace — append below the last class.
"""

# ─── ADD these imports at the top of serializers.py ──────────────────────────
# from arcx_core.models import User, Wallet, Transaction, NAVHistory, KYCRecord
# (KYCRecord is the new addition to the existing import)

from rest_framework import serializers
from arcx_core.models import User, Wallet, KYCRecord


# ─────────────────────────────────────────────────────────────────────────────
# Registration Serializers
# ─────────────────────────────────────────────────────────────────────────────

class RegisterRequestSerializer(serializers.Serializer):
    """
    Validates new user registration.

    password:  Must be at least 8 characters. We don't enforce complexity
               rules here (too annoying for demos) but production should.
    phone:     Optional at registration. Can be added during Tier 1 KYC.
    """
    email      = serializers.EmailField()
    password   = serializers.CharField(
        write_only = True,
        min_length = 8,
        style      = {"input_type": "password"},
    )
    full_name  = serializers.CharField(max_length=255)
    phone      = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, value):
        return value.lower().strip()

    def validate_phone(self, value):
        if value:
            # Strip non-digits for storage, keep + prefix
            digits = value.replace(" ", "").replace("-", "")
            if not digits.replace("+", "").isdigit():
                raise serializers.ValidationError("Phone must contain only digits, spaces, or hyphens.")
        return value or None


class RegisterResponseSerializer(serializers.Serializer):
    """
    What we return after successful registration.
    We return JWT tokens immediately so the user is logged in right away.
    No separate login step required.
    """
    user_id      = serializers.UUIDField()
    email        = serializers.EmailField()
    full_name    = serializers.CharField()
    kyc_status   = serializers.CharField()
    access_token  = serializers.CharField()
    refresh_token = serializers.CharField()
    message      = serializers.CharField()


# ─────────────────────────────────────────────────────────────────────────────
# User Profile Serializer
# ─────────────────────────────────────────────────────────────────────────────

class UserProfileSerializer(serializers.ModelSerializer):
    """
    GET /api/v1/auth/me — full profile with wallet summary.
    The wallet balance is nested in the response — one API call gets everything.
    """
    arcx_balance   = serializers.DecimalField(
        source         = "wallet.arcx_balance",
        max_digits     = 28,
        decimal_places = 18,
        read_only      = True,
    )
    cost_basis_inr = serializers.DecimalField(
        source         = "wallet.cost_basis_inr",
        max_digits     = 20,
        decimal_places = 4,
        read_only      = True,
    )
    wallet_id = serializers.UUIDField(
        source    = "wallet.id",
        read_only = True,
    )

    class Meta:
        model  = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "kyc_status",
            "is_active",
            "wallet_id",
            "arcx_balance",
            "cost_basis_inr",
            "created_at",
        ]


# ─────────────────────────────────────────────────────────────────────────────
# KYC Serializers
# ─────────────────────────────────────────────────────────────────────────────

class KYCSubmitSerializer(serializers.Serializer):
    """
    POST /api/v1/kyc/submit
    
    pan_number: 10 character alphanumeric PAN.
    pin:        6-digit transaction PIN set during KYC.
    """
    pan_number = serializers.CharField(
        max_length=10, 
        min_length=10, 
        help_text="10-character alphanumeric PAN"
    )
    pin = serializers.CharField(
        max_length=6, 
        min_length=6, 
        help_text="Set your 6-digit transaction PIN during KYC verification."
    )

    def validate_pan_number(self, value):
        value = value.upper()
        if not value.isalnum():
            raise serializers.ValidationError("PAN must be alphanumeric.")
        return value


class LogoutRequestSerializer(serializers.Serializer):
    """
    POST /api/v1/auth/logout

    Takes the refresh token. Blacklists it so it can't be used to
    generate new access tokens. The current access token expires
    naturally (30 min) — there's no server-side access token invalidation
    in the simplejwt default setup.
    """
    refresh_token = serializers.CharField()

class ResetPinRequestSerializer(serializers.Serializer):
    """
    POST /api/v1/auth/reset-pin/
    """
    otp = serializers.CharField(max_length=6, min_length=6, help_text="6-digit OTP received via email")
    new_pin = serializers.CharField(max_length=6, min_length=6, help_text="New 6-digit transaction PIN")