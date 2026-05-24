"""
ARCX Phase 5 — Tests for Circuit Breaker and Celery Tasks
-----------------------------------------------------------
Goes in: arcx_backend/tests/test_phase5.py

Two test classes:
  TestCircuitBreakerEngine  — pure domain logic, zero DB, zero mocks needed
  TestEODTasks              — Celery tasks with DB + mocked Oracle

Run: python manage.py test tests.test_phase5

The circuit breaker tests are fast because they test PURE Python.
No Django, no DB, no Oracle. Just numbers in, decisions out.
This is why the circuit breaker is in domain/ and not in arcx_core/.
"""

from decimal import Decimal
from datetime import date
from unittest.mock import patch, MagicMock
from datetime import datetime

from django.test import TestCase

import arcx_core.tasks.eod_tasks  # noqa: F401 — pre-import so @patch can resolve the dotted path

from domain.circuit_breaker import (
    CircuitBreakerEngine,
    CircuitBreakerTier,
    TIER_1_MARKET_DROP,
    TIER_2_MARKET_DROP,
    TIER_3_MARKET_DROP,
    TVL_SPIKE_THRESHOLD,
)


# ── Circuit Breaker Domain Tests ──────────────────────────────────────────────
# These need ZERO Django setup. Pure Python. Runs instantly.

class TestCircuitBreakerEngine(TestCase):

    def setUp(self):
        self.engine = CircuitBreakerEngine()

    # ── All-clear scenarios ───────────────────────────────────────────────

    def test_no_drop_returns_none_tier(self):
        decision = self.engine.evaluate(
            spy_current_price = 540.00,
            spy_open_price    = 540.00,
        )
        self.assertEqual(decision.tier, CircuitBreakerTier.NONE)
        self.assertTrue(decision.deposits_allowed)
        self.assertTrue(decision.withdrawals_allowed)
        self.assertTrue(decision.transfers_allowed)

    def test_market_up_returns_none_tier(self):
        """Rising market must never trip a circuit breaker."""
        decision = self.engine.evaluate(
            spy_current_price = 560.00,   # Up 3.7% from open
            spy_open_price    = 540.00,
        )
        self.assertEqual(decision.tier, CircuitBreakerTier.NONE)
        self.assertEqual(decision.market_drop_pct, 0.0)   # Clamped at zero

    def test_drop_just_below_tier1_threshold_is_clear(self):
        """4.99% drop must NOT trigger Tier 1 (threshold is 5%)."""
        open_price    = 540.00
        current_price = open_price * (1 - 0.0499)   # -4.99%
        decision = self.engine.evaluate(
            spy_current_price = current_price,
            spy_open_price    = open_price,
        )
        self.assertEqual(decision.tier, CircuitBreakerTier.NONE)

    # ── Tier 1 scenarios ──────────────────────────────────────────────────

    def test_5pct_drop_triggers_tier1(self):
        open_price    = 540.00
        current_price = open_price * (1 - TIER_1_MARKET_DROP / 100)
        decision = self.engine.evaluate(
            spy_current_price = current_price,
            spy_open_price    = open_price,
        )
        self.assertEqual(decision.tier, CircuitBreakerTier.TIER_1)

    def test_tier1_blocks_deposits_only(self):
        """Tier 1: deposits blocked, withdrawals and transfers still allowed."""
        decision = self.engine.evaluate(
            spy_current_price = 513.00,   # -5% from 540
            spy_open_price    = 540.00,
        )
        self.assertEqual(decision.tier,           CircuitBreakerTier.TIER_1)
        self.assertFalse(decision.deposits_allowed)
        self.assertTrue(decision.withdrawals_allowed)
        self.assertTrue(decision.transfers_allowed)

    # ── Tier 2 scenarios ──────────────────────────────────────────────────

    def test_10pct_drop_triggers_tier2(self):
        open_price    = 540.00
        current_price = open_price * (1 - TIER_2_MARKET_DROP / 100)
        decision = self.engine.evaluate(
            spy_current_price = current_price,
            spy_open_price    = open_price,
        )
        self.assertEqual(decision.tier, CircuitBreakerTier.TIER_2)

    def test_tier2_blocks_deposits_and_transfers(self):
        """Tier 2: deposits and transfers blocked, withdrawals allowed."""
        decision = self.engine.evaluate(
            spy_current_price = 486.00,   # -10% from 540
            spy_open_price    = 540.00,
        )
        self.assertFalse(decision.deposits_allowed)
        self.assertTrue(decision.withdrawals_allowed)
        self.assertFalse(decision.transfers_allowed)

    # ── Tier 3 scenarios ──────────────────────────────────────────────────

    def test_20pct_drop_triggers_tier3(self):
        open_price    = 540.00
        current_price = open_price * (1 - TIER_3_MARKET_DROP / 100)
        decision = self.engine.evaluate(
            spy_current_price = current_price,
            spy_open_price    = open_price,
        )
        self.assertEqual(decision.tier, CircuitBreakerTier.TIER_3)

    def test_tier3_blocks_everything(self):
        """Tier 3: FULL HALT. Nothing allowed."""
        decision = self.engine.evaluate(
            spy_current_price = 432.00,   # -20% from 540
            spy_open_price    = 540.00,
        )
        self.assertFalse(decision.deposits_allowed)
        self.assertFalse(decision.withdrawals_allowed)
        self.assertFalse(decision.transfers_allowed)

    def test_tier3_supersedes_tier2(self):
        """A 25% drop must trigger Tier 3, not Tier 2."""
        decision = self.engine.evaluate(
            spy_current_price = 405.00,   # -25% from 540
            spy_open_price    = 540.00,
        )
        self.assertEqual(decision.tier, CircuitBreakerTier.TIER_3)

    # ── TVL Spike scenarios ───────────────────────────────────────────────

    def test_tvl_spike_triggers_tier2(self):
        """20%+ of TVL withdrawn in 1 hour triggers Tier 2 even without market drop."""
        tvl_usd          = 100_000.0
        withdrawn_1h_usd = 21_000.0    # 21% of TVL
        decision = self.engine.evaluate(
            spy_current_price = 540.00,   # No market drop
            spy_open_price    = 540.00,
            tvl_usd           = tvl_usd,
            withdrawn_1h_usd  = withdrawn_1h_usd,
        )
        self.assertEqual(decision.tier, CircuitBreakerTier.TIER_2)

    def test_tvl_spike_below_threshold_is_clear(self):
        """19% TVL withdrawal must not trigger circuit breaker."""
        decision = self.engine.evaluate(
            spy_current_price = 540.00,
            spy_open_price    = 540.00,
            tvl_usd           = 100_000.0,
            withdrawn_1h_usd  = 19_000.0,   # 19% — below 20% threshold
        )
        self.assertEqual(decision.tier, CircuitBreakerTier.NONE)

    def test_zero_tvl_no_crash(self):
        """TVL of zero must not cause ZeroDivisionError."""
        decision = self.engine.evaluate(
            spy_current_price = 540.00,
            spy_open_price    = 540.00,
            tvl_usd           = 0.0,
            withdrawn_1h_usd  = 50_000.0,
        )
        # With zero TVL the TVL check is skipped (0 TVL = division by zero guard)
        self.assertEqual(decision.tier, CircuitBreakerTier.NONE)

    def test_market_drop_takes_priority_over_tvl_spike(self):
        """
        If both a 25% market drop AND a TVL spike occur simultaneously,
        the TIER_3 (from market drop) must win over TIER_2 (from TVL spike).
        """
        decision = self.engine.evaluate(
            spy_current_price = 405.00,   # -25% crash
            spy_open_price    = 540.00,
            tvl_usd           = 100_000.0,
            withdrawn_1h_usd  = 30_000.0,   # Also 30% TVL spike
        )
        self.assertEqual(decision.tier, CircuitBreakerTier.TIER_3)

    def test_reason_string_contains_drop_percentage(self):
        """The human-readable reason must include the actual drop percentage."""
        decision = self.engine.evaluate(
            spy_current_price = 486.00,
            spy_open_price    = 540.00,
        )
        self.assertIn("10.0%", decision.reason)

    def test_market_drop_calculation_precision(self):
        """Verify the drop calculation is mathematically correct."""
        open_p    = 1000.0
        current_p = 900.0   # exactly 10% drop
        decision  = self.engine.evaluate(
            spy_current_price = current_p,
            spy_open_price    = open_p,
        )
        self.assertAlmostEqual(decision.market_drop_pct, 10.0, places=1)


# ── EOD Task Integration Tests ────────────────────────────────────────────────

def _mock_prices():
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


class TestEODTasks(TestCase):
    """
    Tests for Celery task logic.
    We call the task function directly (not via Celery worker)
    and mock the Oracle so no live prices are needed.
    """

    @patch("arcx_core.tasks.eod_tasks.MultiSourceOracle")
    def test_take_vault_snapshot_creates_record(self, MockOracle):
        from arcx_core.tasks.eod_tasks import take_vault_snapshot
        from arcx_core.models import VaultSnapshot

        MockOracle.return_value.fetch_prices.return_value = _mock_prices()

        # Call task directly (bypasses Celery worker)
        result = take_vault_snapshot()

        self.assertEqual(result["status"], "ok")
        self.assertTrue(VaultSnapshot.objects.filter(snapshot_date=date.today()).exists())

    @patch("arcx_core.tasks.eod_tasks.MultiSourceOracle")
    def test_take_vault_snapshot_is_idempotent(self, MockOracle):
        """Running the snapshot task twice on the same day must not crash or duplicate."""
        from arcx_core.tasks.eod_tasks import take_vault_snapshot
        from arcx_core.models import VaultSnapshot

        MockOracle.return_value.fetch_prices.return_value = _mock_prices()

        take_vault_snapshot()
        result2 = take_vault_snapshot()   # Second call same day

        self.assertEqual(result2["status"], "skipped")
        self.assertEqual(VaultSnapshot.objects.filter(snapshot_date=date.today()).count(), 1)

    @patch("arcx_core.tasks.eod_tasks.MultiSourceOracle")
    def test_publish_daily_nav_creates_history_record(self, MockOracle):
        from arcx_core.tasks.eod_tasks import take_vault_snapshot, publish_daily_nav
        from arcx_core.models import NAVHistory

        MockOracle.return_value.fetch_prices.return_value = _mock_prices()

        # Must snapshot first
        take_vault_snapshot()
        result = publish_daily_nav()

        self.assertEqual(result["status"], "ok")
        self.assertIn("nav_inr", result)
        self.assertIn("report_hash", result)
        self.assertTrue(NAVHistory.objects.filter(nav_date=date.today()).exists())

    @patch("arcx_core.tasks.eod_tasks.MultiSourceOracle")
    def test_publish_daily_nav_is_idempotent(self, MockOracle):
        from arcx_core.tasks.eod_tasks import take_vault_snapshot, publish_daily_nav
        from arcx_core.models import NAVHistory

        MockOracle.return_value.fetch_prices.return_value = _mock_prices()

        take_vault_snapshot()
        publish_daily_nav()
        result2 = publish_daily_nav()

        self.assertEqual(result2["status"], "skipped")
        self.assertEqual(NAVHistory.objects.filter(nav_date=date.today()).count(), 1)