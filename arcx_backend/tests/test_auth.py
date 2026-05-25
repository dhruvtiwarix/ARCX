"""
ARCX Phase 6 — Auth & KYC Tests
----------------------------------
Goes in: arcx_backend/tests/test_auth.py

Tests the complete user onboarding lifecycle:
  Register → Get profile → Submit KYC → Deposit → Logout

Run: python manage.py test tests.test_auth
"""

import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock
from datetime import datetime

from django.test import TestCase, Client
from django.contrib.auth.models import User as AuthUser

from arcx_core.models import User as ArcxUser, Wallet, KYCRecord
from arcx_core.services.auth_service import AuthService, RegistrationError


# ── Fixtures ──────────────────────────────────────────────────────────────────

def mock_prices():
    m = MagicMock()
    m.spy = 530.0; m.tlt = 95.0; m.gld = 185.0; m.usd_inr = 83.5
    m.fetched_at   = datetime.now()
    m.sources_used = ["Yahoo Finance (mock)"]
    m.spy_readings = [("Yahoo Finance (mock)", 530.0)]
    m.tlt_readings = [("Yahoo Finance (mock)", 95.0)]
    m.gld_readings = [("Yahoo Finance (mock)", 185.0)]
    return m


# ── AuthService Unit Tests ────────────────────────────────────────────────────

class TestAuthService(TestCase):

    def setUp(self):
        self.service = AuthService()

    def test_register_creates_arcx_user(self):
        user = self.service.register(
            email     = "test@arcx.in",
            password  = "password123",
            full_name = "Test User",
        )
        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, "test@arcx.in")
        self.assertEqual(user.kyc_status, "pending")

    def test_register_creates_wallet_atomically(self):
        """Wallet must exist immediately after registration — no separate step."""
        user = self.service.register(
            email="wallet_test@arcx.in", password="pass12345", full_name="Wallet User"
        )
        wallet = Wallet.objects.get(user=user)
        self.assertEqual(wallet.arcx_balance, Decimal("0"))
        self.assertFalse(wallet.is_frozen)

    def test_register_creates_django_auth_user(self):
        """JWT auth requires a matching Django auth.User."""
        user = self.service.register(
            email="auth_test@arcx.in", password="pass12345", full_name="Auth User"
        )
        auth_user = AuthUser.objects.get(username=str(user.id))
        self.assertEqual(auth_user.username, str(user.id))
        self.assertTrue(auth_user.check_password("pass12345"))

    def test_register_normalizes_email_lowercase(self):
        user = self.service.register(
            email="UPPER@ARCX.IN", password="pass12345", full_name="Upper User"
        )
        self.assertEqual(user.email, "upper@arcx.in")

    def test_register_duplicate_email_raises_error(self):
        self.service.register(email="dup@arcx.in", password="pass12345", full_name="First")
        with self.assertRaises(RegistrationError):
            self.service.register(email="dup@arcx.in", password="pass12345", full_name="Second")

    def test_register_with_phone(self):
        user = self.service.register(
            email="phone@arcx.in", password="pass12345",
            full_name="Phone User", phone="+91 98765 43210"
        )
        self.assertEqual(user.phone, "+91 98765 43210")


# ── Registration API Tests ────────────────────────────────────────────────────

class TestRegisterEndpoint(TestCase):

    def setUp(self):
        self.client = Client()

    def _post(self, body):
        return self.client.post(
            "/api/v1/auth/register",
            data=body,
            content_type="application/json",
        )

    def test_register_returns_201_with_tokens(self):
        response = self._post({
            "email":     "new@arcx.in",
            "password":  "password123",
            "full_name": "New User",
        })
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("access_token",  data)
        self.assertIn("refresh_token", data)
        self.assertIn("user_id",       data)
        self.assertEqual(data["kyc_status"], "pending")

    def test_register_no_auth_required(self):
        """Registration must be public — no JWT needed."""
        response = self._post({
            "email": "public@arcx.in", "password": "pass1234", "full_name": "Public"
        })
        self.assertNotEqual(response.status_code, 401)

    def test_register_duplicate_email_returns_409(self):
        self._post({"email": "dup@arcx.in", "password": "pass1234", "full_name": "First"})
        response = self._post({"email": "dup@arcx.in", "password": "pass1234", "full_name": "Second"})
        self.assertEqual(response.status_code, 409)

    def test_register_short_password_rejected(self):
        response = self._post({
            "email": "weak@arcx.in", "password": "123", "full_name": "Weak"
        })
        self.assertEqual(response.status_code, 400)

    def test_register_invalid_email_rejected(self):
        response = self._post({
            "email": "not-an-email", "password": "pass1234", "full_name": "Bad Email"
        })
        self.assertEqual(response.status_code, 400)

    def test_register_missing_full_name_rejected(self):
        response = self._post({"email": "nofullname@arcx.in", "password": "pass1234"})
        self.assertEqual(response.status_code, 400)


# ── Me Endpoint Tests ─────────────────────────────────────────────────────────

class TestMeEndpoint(TestCase):

    def setUp(self):
        self.client   = Client()
        # Register via API so we get a real token
        response = self.client.post(
            "/api/v1/auth/register",
            data={"email": "me@arcx.in", "password": "pass1234", "full_name": "Me User"},
            content_type="application/json",
        )
        self.token = response.json()["access_token"]

    def test_me_returns_profile_with_wallet(self):
        response = self.client.get(
            "/api/v1/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"],       "me@arcx.in")
        self.assertIn("arcx_balance",         data)
        self.assertIn("wallet_id",            data)
        self.assertIn("kyc_status",           data)

    def test_me_unauthenticated_returns_401(self):
        response = self.client.get("/api/v1/auth/me")
        self.assertEqual(response.status_code, 401)


# ── KYC Flow Tests ────────────────────────────────────────────────────────────

class TestKYCFlow(TestCase):

    def setUp(self):
        self.client = Client()
        response = self.client.post(
            "/api/v1/auth/register",
            data={"email": "kyc@arcx.in", "password": "pass1234", "full_name": "KYC User"},
            content_type="application/json",
        )
        self.token   = response.json()["access_token"]
        self.user_id = response.json()["user_id"]

    def _auth_post(self, url, body):
        return self.client.post(
            url, data=body, content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

    def _auth_get(self, url):
        return self.client.get(url, HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_kyc_submit_approves_and_upgrades_status(self):
        response = self._auth_post("/api/v1/kyc/submit", {
            "tier":          "tier_1",
            "document_type": "aadhaar",
            "document_ref":  "DEMO_AADHAAR_REF_001",
        })
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "approved")
        self.assertIn("tier_1", data["message"])

        # User's kyc_status must now be 'approved'
        user = ArcxUser.objects.get(id=self.user_id)
        self.assertEqual(user.kyc_status, "approved")

    def test_kyc_status_shows_all_records(self):
        # Submit first
        self._auth_post("/api/v1/kyc/submit", {
            "tier": "tier_1", "document_type": "aadhaar", "document_ref": "REF_001",
        })
        # Then check status
        response = self._auth_get("/api/v1/kyc/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["kyc_status"],   "approved")
        self.assertEqual(data["highest_tier"], "tier_1")
        self.assertEqual(len(data["records"]), 1)

    def test_kyc_wrong_document_for_tier_rejected(self):
        """Tier 1 only accepts Aadhaar or DL. PAN should fail."""
        response = self._auth_post("/api/v1/kyc/submit", {
            "tier": "tier_1", "document_type": "pan", "document_ref": "PAN123",
        })
        self.assertEqual(response.status_code, 400)

    def test_duplicate_kyc_tier_returns_409(self):
        self._auth_post("/api/v1/kyc/submit", {
            "tier": "tier_1", "document_type": "aadhaar", "document_ref": "REF_A",
        })
        response = self._auth_post("/api/v1/kyc/submit", {
            "tier": "tier_1", "document_type": "aadhaar", "document_ref": "REF_B",
        })
        self.assertEqual(response.status_code, 409)


# ── Full Onboarding Flow Test ─────────────────────────────────────────────────

class TestFullOnboardingFlow(TestCase):
    """
    The complete happy path:
      Register → Get profile → Submit KYC → Deposit → Check balance → Logout
    """

    def setUp(self):
        self.client = Client()

    @patch("arcx_core.services.wallet_service.MultiSourceOracle")
    def test_complete_lifecycle(self, MockOracle):
        MockOracle.return_value.fetch_prices.return_value = mock_prices()

        # Step 1: Register
        r = self.client.post(
            "/api/v1/auth/register",
            data={"email": "full@arcx.in", "password": "pass1234", "full_name": "Full Flow"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        token         = r.json()["access_token"]
        refresh_token = r.json()["refresh_token"]
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        # Step 2: Get profile — wallet exists, balance is 0
        r = self.client.get("/api/v1/auth/me", **headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["arcx_balance"], "0.000000000000000000")

        # Step 3: Try deposit before KYC — should fail (403)
        r = self.client.post(
            "/api/v1/wallet/deposit",
            data={"amount_inr": "1000.00"},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            **headers,
        )
        self.assertEqual(r.status_code, 403)   # KYC not approved yet

        # Step 4: Submit KYC
        r = self.client.post(
            "/api/v1/kyc/submit",
            data={"tier": "tier_1", "document_type": "aadhaar", "document_ref": "REF_DEMO"},
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["status"], "approved")

        # Step 5: Now deposit succeeds
        r = self.client.post(
            "/api/v1/wallet/deposit",
            data={"amount_inr": "1000.00"},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            **headers,
        )
        self.assertEqual(r.status_code, 201)
        self.assertIn("arcx_credited", r.json())

        # Step 6: Check balance is no longer 0
        r = self.client.get("/api/v1/auth/me", **headers)
        balance = Decimal(r.json()["arcx_balance"])
        self.assertGreater(balance, Decimal("0"))

        # Step 7: Logout
        r = self.client.post(
            "/api/v1/auth/logout",
            data={"refresh_token": refresh_token},
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r.status_code, 200)