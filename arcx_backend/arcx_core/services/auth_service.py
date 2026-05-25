"""
ARCX Auth Service — Phase 6
------------------------------
Goes in: arcx_backend/arcx_core/services/auth_service.py

This is the entry point into ARCX. Before this existed, the system
had no way to create a user. You could run the server, hit the API,
and get 401 on every single endpoint. Phase 6 fixes that.

REGISTRATION FLOW:
  1. Validate email uniqueness (serializer layer)
  2. Open one atomic transaction
  3. Create Django auth.User  (needed by simplejwt for token issuance)
  4. Create ARCX User         (our business record, UUID primary key)
  5. Create ARCX Wallet       (one wallet per user, created at registration)
  6. Commit all three at once — or rollback all three on any failure
  7. Return the new ARCX User for the response

WHY ONE TRANSACTION?
  If step 3 succeeds but step 5 fails (e.g., DB briefly down),
  the user can log in but has no wallet. They get 500 on every
  financial endpoint. Nightmare for support. Atomic block prevents this.

JWT SUBJECT CLAIM:
  simplejwt puts auth.User.username into the JWT "sub" field.
  We set username = str(arcx_user.id) at registration time.
  Every view does request.user.username to get the ARCX UUID.
  This is the convention the entire codebase relies on — do not change it.

PASSWORD HANDLING:
  We never store plaintext passwords. auth.User.set_password() runs
  Django's PBKDF2+SHA256 hasher before saving. Standard and sufficient.
"""

import logging
from decimal import Decimal
from typing import Optional

from django.contrib.auth.models import User as AuthUser
from django.db import transaction

from arcx_core.models import User as ArcxUser, Wallet

logger = logging.getLogger("arcx.auth")


class RegistrationError(Exception):
    """Raised when registration cannot proceed due to a business rule."""
    code = "REGISTRATION_FAILED"


class AuthService:

    @transaction.atomic
    def register(
        self,
        email:      str,
        password:   str,
        full_name:  str,
        phone:      Optional[str] = None,
    ) -> ArcxUser:
        """
        Create an ARCX user account in one atomic operation.

        Creates three records atomically:
          1. Django auth.User  → needed for JWT token issuance
          2. ARCX User         → business record with UUID pk + KYC status
          3. ARCX Wallet       → zero-balance wallet, ready for first deposit

        Args:
            email:      Must be unique. Checked by DB constraint.
            password:   Plaintext — hashed by Django before storage.
            full_name:  User's display name.
            phone:      Optional. Can be added later during KYC.

        Returns:
            The newly created ArcxUser instance.

        Raises:
            RegistrationError: If email is already taken.
        """
        email = email.lower().strip()

        # Guard: friendly error before hitting the DB unique constraint
        if ArcxUser.objects.filter(email=email, deleted_at__isnull=True).exists():
            raise RegistrationError(
                f"An account with email '{email}' already exists."
            )

        # Step 1: Create the Django auth user (needed by simplejwt)
        # We'll set username = arcx_user.id AFTER creating the arcx user below.
        # But we need auth user first for the FK. Chicken-and-egg solved by
        # setting username to email temporarily, then updating after.
        auth_user = AuthUser.objects.create_user(
            username = email,   # temporary — overwritten in step 3
            email    = email,
            password = password,
        )

        # Step 2: Create the ARCX user (our real user record)
        arcx_user = ArcxUser.objects.create(
            email      = email,
            full_name  = full_name.strip(),
            phone      = phone.strip() if phone else None,
            kyc_status = ArcxUser.KycStatus.PENDING,
            is_active  = True,
        )

        # Step 3: Update auth_user.username to be the ARCX UUID
        # This is what every view reads from request.user.username
        auth_user.username = str(arcx_user.id)
        auth_user.save(update_fields=["username"])

        # Step 4: Create the wallet (zero balance at start)
        Wallet.objects.create(
            user           = arcx_user,
            arcx_balance   = Decimal("0"),
            cost_basis_inr = Decimal("0"),
            is_frozen      = False,
        )

        logger.info(
            "Registration complete: user_id=%s email=%s",
            arcx_user.id, email,
        )
        return arcx_user

    def get_arcx_user(self, user_id: str) -> ArcxUser:
        """
        Fetch the ARCX User by UUID.
        Used by MeView and KYC views to get the full profile.
        """
        return ArcxUser.objects.select_related("wallet").get(
            id             = user_id,
            deleted_at__isnull = True,
            is_active      = True,
        )