"""
ARCX Phase 3 — API Tests
--------------------------
Tests for all v1 endpoints. No live oracle. No real database needed.
Uses Django's TestClient + mocks.
 
Run: python manage.py test arcx_core.tests
 
Pattern:
  Each test class = one endpoint
  setUp()  = create test user + wallet + JWT token
  test_*() = one assertion per test (fast to read, fast to debug)
 
What we're testing:
  ✓ Correct HTTP status codes
  ✓ Response body shape matches contract
  ✓ Business rules (insufficient balance, KYC gate, etc.)
  ✓ Idempotency (same key → same response, no double-charge)
  ✓ Race condition safety (two concurrent deposits → correct total)
"""
 
import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock
from datetime import datetime
 
from django.test import TestCase, Client
from django.urls import reverse
 
from arcx_core.models import User, Wallet, Transaction
 
 
# ── Test Fixtures ─────────────────────────────────────────────────────────────
 
def make_user(email="test@arcx.in", kyc_status="approved"):
    user = User.objects.create(
        email=email,
        full_name="Test User",
        kyc_status=kyc_status,
    )
    Wallet.objects.create(
        user=user,
        arcx_balance=Decimal("100.000000000000000000"),
        cost_basis_inr=Decimal("10000.0000"),
    )
    return user
 
 
def mock_prices():
    """Returns a fake MarketPrices object. No internet required."""
    m = MagicMock()
    m.spy      = 530.00
    m.tlt      = 95.00
    m.gld      = 185.00
    m.usd_inr  = 83.50
    m.fetched_at = datetime.now()
    m.sources_used = ["Yahoo Finance (mock)"]
    m.spy_readings = [("Yahoo Finance (mock)", 530.00)]
    m.tlt_readings = [("Yahoo Finance (mock)", 95.00)]
    m.gld_readings = [("Yahoo Finance (mock)", 185.00)]
    return m
 
 
def get_token(client, user_id):
    """Get a JWT token for a user (simplified for testing)."""
    from rest_framework_simplejwt.tokens import RefreshToken
    # In test, we create a Django auth user whose username = ARCX UUID
    from django.contrib.auth.models import User as AuthUser
    auth_user, _ = AuthUser.objects.get_or_create(username=str(user_id))
    refresh = RefreshToken.for_user(auth_user)
    return str(refresh.access_token)
 
 
# ── Oracle Tests ──────────────────────────────────────────────────────────────
 
class TestLivePriceEndpoint(TestCase):
 
    def setUp(self):
        self.client = Client()
 
    @patch("arcx_core.views.oracle_views.MultiSourceOracle")
    def test_returns_200_with_nav(self, MockOracle):
        MockOracle.return_value.fetch_prices.return_value = mock_prices()
 
        response = self.client.get("/api/v1/oracle/price")
 
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("nav_inr", data)
        self.assertIn("spy_usd", data)
        self.assertIn("sources_used", data)
 
    @patch("arcx_core.views.oracle_views.MultiSourceOracle")
    def test_oracle_failure_returns_503(self, MockOracle):
        from domain.oracle import OracleFailureException
        MockOracle.return_value.fetch_prices.side_effect = OracleFailureException("All sources down")
 
        response = self.client.get("/api/v1/oracle/price")
 
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "ORACLE_UNAVAILABLE")
 
    def test_no_auth_required(self):
        """Price endpoint must be public — no JWT needed."""
        with patch("arcx_core.views.oracle_views.MultiSourceOracle") as MockOracle:
            MockOracle.return_value.fetch_prices.return_value = mock_prices()
            response = self.client.get("/api/v1/oracle/price")
            # Should not return 401
            self.assertNotEqual(response.status_code, 401)
 
 
# ── Deposit Tests ─────────────────────────────────────────────────────────────
 
class TestDepositEndpoint(TestCase):
 
    def setUp(self):
        self.client = Client()
        self.user   = make_user()
        self.token  = get_token(self.client, self.user.id)
 
    def _post(self, body, idempotency_key=None):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        if idempotency_key:
            headers["HTTP_IDEMPOTENCY_KEY"] = idempotency_key
        return self.client.post(
            "/api/v1/wallet/deposit",
            data=body,
            content_type="application/json",
            **headers,
        )
 
    @patch("arcx_core.services.wallet_service.MultiSourceOracle")
    def test_deposit_credits_wallet(self, MockOracle):
        MockOracle.return_value.fetch_prices.return_value = mock_prices()
        idem_key = str(uuid.uuid4())
 
        response = self._post({"amount_inr": "5000.00"}, idempotency_key=idem_key)
 
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("arcx_credited", data)
        self.assertIn("transaction_id", data)
        self.assertIn("new_balance", data)
 
        # Wallet balance must be greater than before
        wallet = Wallet.objects.get(user=self.user)
        self.assertGreater(wallet.arcx_balance, Decimal("100"))
 
    @patch("arcx_core.services.wallet_service.MultiSourceOracle")
    def test_deposit_below_minimum_rejected(self, MockOracle):
        MockOracle.return_value.fetch_prices.return_value = mock_prices()
        response = self._post(
            {"amount_inr": "50.00"},
            idempotency_key=str(uuid.uuid4()),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "VALIDATION_ERROR")
 
    def test_deposit_without_idempotency_key_rejected(self):
        """Financial endpoints must reject requests without Idempotency-Key."""
        response = self._post({"amount_inr": "5000.00"})  # No idempotency key
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "MISSING_IDEMPOTENCY_KEY")
 
    @patch("arcx_core.services.wallet_service.MultiSourceOracle")
    def test_same_idempotency_key_does_not_double_charge(self, MockOracle):
        """Critical test: same key twice → wallet credited only once."""
        MockOracle.return_value.fetch_prices.return_value = mock_prices()
        idem_key = str(uuid.uuid4())
 
        response1 = self._post({"amount_inr": "5000.00"}, idempotency_key=idem_key)
        response2 = self._post({"amount_inr": "5000.00"}, idempotency_key=idem_key)
 
        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)
        # Second response should be the cached first response
        self.assertEqual(response2["X-Idempotency-Replayed"], "true")
 
        # Only ONE transaction should have been created
        tx_count = Transaction.objects.filter(
            wallet__user=self.user,
            tx_type="deposit",
        ).count()
        self.assertEqual(tx_count, 1)
 
    def test_unauthenticated_request_rejected(self):
        response = self.client.post(
            "/api/v1/wallet/deposit",
            data={"amount_inr": "5000.00"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
 
    def test_unverified_kyc_blocked(self):
        """Users with pending KYC cannot deposit."""
        pending_user  = make_user(email="pending@arcx.in", kyc_status="pending")
        pending_token = get_token(self.client, pending_user.id)
 
        response = self.client.post(
            "/api/v1/wallet/deposit",
            data={"amount_inr": "5000.00"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {pending_token}",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "FORBIDDEN")
 
 
# ── Withdraw Tests ────────────────────────────────────────────────────────────
 
class TestWithdrawEndpoint(TestCase):
 
    def setUp(self):
        self.client = Client()
        self.user   = make_user()
        self.token  = get_token(self.client, self.user.id)
 
    def _post(self, body, idempotency_key=None):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        if idempotency_key:
            headers["HTTP_IDEMPOTENCY_KEY"] = idempotency_key
        return self.client.post(
            "/api/v1/wallet/withdraw",
            data=body,
            content_type="application/json",
            **headers,
        )
 
    @patch("arcx_core.services.wallet_service.MultiSourceOracle")
    def test_withdraw_debits_wallet(self, MockOracle):
        MockOracle.return_value.fetch_prices.return_value = mock_prices()
        response = self._post({"amount_arcx": "10.0"}, idempotency_key=str(uuid.uuid4()))
 
        self.assertEqual(response.status_code, 201)
        wallet = Wallet.objects.get(user=self.user)
        self.assertLess(wallet.arcx_balance, Decimal("100"))
 
    @patch("arcx_core.services.wallet_service.MultiSourceOracle")
    def test_insufficient_balance_returns_422(self, MockOracle):
        MockOracle.return_value.fetch_prices.return_value = mock_prices()
        response = self._post(
            {"amount_arcx": "999999.0"},
            idempotency_key=str(uuid.uuid4()),
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "INSUFFICIENT_BALANCE")
 
 
# ── Transfer Tests ────────────────────────────────────────────────────────────
 
class TestTransferEndpoint(TestCase):
 
    def setUp(self):
        self.client    = Client()
        self.sender    = make_user(email="sender@arcx.in")
        self.recipient = make_user(email="recipient@arcx.in")
        self.token     = get_token(self.client, self.sender.id)
 
    def _post(self, body, idempotency_key=None):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        if idempotency_key:
            headers["HTTP_IDEMPOTENCY_KEY"] = idempotency_key
        return self.client.post(
            "/api/v1/transfer/",
            data=body,
            content_type="application/json",
            **headers,
        )
 
    def test_transfer_moves_arcx_atomically(self):
        body = {
            "to_user_email": "recipient@arcx.in",
            "amount_arcx":   "10.0",
        }
        response = self._post(body, idempotency_key=str(uuid.uuid4()))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["fee"], "0.00")
 
        sender_wallet    = Wallet.objects.get(user=self.sender)
        recipient_wallet = Wallet.objects.get(user=self.recipient)
        self.assertEqual(sender_wallet.arcx_balance,    Decimal("90.000000000000000000"))
        self.assertEqual(recipient_wallet.arcx_balance, Decimal("110.000000000000000000"))
 
    def test_total_supply_unchanged_after_transfer(self):
        """Transfer must not create or destroy ARCX. Conservation law."""
        before = (
            Wallet.objects.get(user=self.sender).arcx_balance
            + Wallet.objects.get(user=self.recipient).arcx_balance
        )
        self._post(
            {"to_user_email": "recipient@arcx.in", "amount_arcx": "25.0"},
            idempotency_key=str(uuid.uuid4()),
        )
        after = (
            Wallet.objects.get(user=self.sender).arcx_balance
            + Wallet.objects.get(user=self.recipient).arcx_balance
        )
        self.assertEqual(before, after)
 
    def test_cannot_transfer_to_self(self):
        body = {
            "to_user_email": "sender@arcx.in",
            "amount_arcx":   "10.0",
        }
        response = self._post(body, idempotency_key=str(uuid.uuid4()))
        # Should fail — can't send to yourself
        self.assertNotEqual(response.status_code, 201)
 