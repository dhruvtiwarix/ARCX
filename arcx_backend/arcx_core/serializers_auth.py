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

    document_ref: The external ID returned by your KYC provider
                  (DigiLocker, Onfido, CKYC, etc.).
                  We never store the actual document — only this reference.
    """
    tier = serializers.ChoiceField(choices=[
        ("tier_1", "Tier 1 — Aadhaar OTP"),
        ("tier_2", "Tier 2 — PAN + Selfie"),
        ("tier_3", "Tier 3 — Full Address Proof"),
    ])
    document_type = serializers.ChoiceField(choices=[
        ("aadhaar",  "Aadhaar Card"),
        ("pan",      "PAN Card"),
        ("passport", "Passport"),
        ("dl",       "Driving License"),
    ])
    document_ref = serializers.CharField(
        max_length  = 255,
        help_text   = "External reference ID from KYC provider. Never send raw document data.",
    )

    def validate(self, data):
        """Ensure the document type makes sense for the tier."""
        tier = data.get("tier")
        doc  = data.get("document_type")

        if tier == "tier_1" and doc not in ("aadhaar", "dl"):
            raise serializers.ValidationError(
                "Tier 1 accepts Aadhaar or Driving License only."
            )
        if tier == "tier_2" and doc not in ("pan", "passport"):
            raise serializers.ValidationError(
                "Tier 2 accepts PAN or Passport only."
            )
        return data


class LogoutRequestSerializer(serializers.Serializer):
    """
    POST /api/v1/auth/logout

    Takes the refresh token. Blacklists it so it can't be used to
    generate new access tokens. The current access token expires
    naturally (30 min) — there's no server-side access token invalidation
    in the simplejwt default setup.
    """
    refresh_token = serializers.CharField()