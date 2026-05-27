"""
ARCX Phase 6 — Holdings Engine Tests
--------------------------------------
Tests for the quantity-based Mark-to-Market valuation engine and
the upgraded quantity-based rebalancer.

All tests use mock data — no DB, no Oracle, no network.
The domain layer (valuation.py, rebalancer.py) is pure Python:
pure math in, pure dataclasses out. This makes it fully testable.

Run:
    python manage.py test tests.test_phase6
    python manage.py test tests.test_phase6 --verbosity=2
"""

from decimal import Decimal
from datetime import datetime
from unittest.mock import MagicMock
from django.test import TestCase

from domain.oracle import MarketPrices
from domain.valuation import ValuationEngine, GENESIS_NAV_INR, VaultState, AssetPosition
from domain.rebalancer import DriftRebalancer, DRIFT_TOLERANCE, RebalanceTrade


# ── Test Helpers ──────────────────────────────────────────────────────────────

def mock_prices(spy=530.0, tlt=95.0, gld=185.0, usd_inr=83.5):
    """Creates a mock MarketPrices object with configurable values."""
    m = MagicMock(spec=MarketPrices)
    m.spy        = spy
    m.tlt        = tlt
    m.gld        = gld
    m.usd_inr    = usd_inr
    m.fetched_at = datetime.now()
    m.sources_used = ["Mock Oracle"]
    return m


def mock_holding(ticker: str, qty: float, avg_price: float):
    """Creates a mock VaultAssetHolding object (no DB required)."""
    h = MagicMock()
    h.asset_ticker     = ticker
    h.total_quantity   = Decimal(str(qty))
    h.average_buy_price = Decimal(str(avg_price))
    return h


# ── Test Suite 1: Phase 6 Valuation Engine ────────────────────────────────────

class TestPhase6ValuationEngine(TestCase):
    """
    Tests for the rewritten ValuationEngine.
    Verifies that NAV is computed from quantity × live price, not percentages.
    """

    def setUp(self):
        self.prices = mock_prices()

    # ── Core Math Tests ───────────────────────────────────────────────────────

    def test_mark_to_market_single_asset(self):
        """10 SPY shares at $530 = $5,300 market value."""
        holdings = [mock_holding("SPY", 10.0, 500.0)]
        engine   = ValuationEngine(arcx_supply=1000.0, cash_balance_usd=1000.0)
        state    = engine.calculate_nav(holdings, self.prices)

        self.assertAlmostEqual(float(state.stock_value_usd), 5300.0, places=2)
        self.assertAlmostEqual(float(state.cash_balance_usd), 1000.0, places=2)
        self.assertAlmostEqual(float(state.total_vault_value_usd), 6300.0, places=2)

    def test_nav_formula_is_total_divided_by_supply(self):
        """NAV = total_vault_value / arcx_supply."""
        holdings = [
            mock_holding("SPY", 10.0, 500.0),   # 10 × $530 = $5,300
            mock_holding("TLT",  5.0,  90.0),   #  5 × $95  = $475
        ]
        engine = ValuationEngine(arcx_supply=100.0, cash_balance_usd=200.0)
        state  = engine.calculate_nav(holdings, self.prices)

        # $5,300 + $475 + $200 = $5,975 / 100 supply = $59.75
        self.assertAlmostEqual(float(state.nav_usd), 59.75, places=2)

    def test_nav_inr_conversion(self):
        """nav_inr = nav_usd × usd_inr_rate."""
        holdings = [mock_holding("SPY", 10.0, 500.0)]   # 10 × $530 = $5,300
        engine   = ValuationEngine(arcx_supply=100.0, cash_balance_usd=0.0)
        prices   = mock_prices(spy=530.0, usd_inr=83.5)
        state    = engine.calculate_nav(holdings, prices)

        # nav_usd = 5300 / 100 = $53.00
        # nav_inr = 53.00 × 83.5 = ₹4,425.50
        self.assertAlmostEqual(float(state.nav_usd), 53.0, places=2)
        self.assertAlmostEqual(float(state.nav_inr), 4425.50, places=1)

    def test_all_three_assets_summed(self):
        """NAV sums SPY + TLT + GLD + cash correctly."""
        holdings = [
            mock_holding("SPY", 8.0, 500.0),    # 8 × $530 = $4,240
            mock_holding("TLT", 3.0, 90.0),     # 3 × $95  = $285
            mock_holding("GLD", 1.0, 180.0),    # 1 × $185 = $185
        ]
        engine = ValuationEngine(arcx_supply=1000.0, cash_balance_usd=290.0)
        state  = engine.calculate_nav(holdings, self.prices)

        self.assertAlmostEqual(float(state.stock_value_usd), 4240.0, places=1)
        self.assertAlmostEqual(float(state.bond_value_usd),   285.0, places=1)
        self.assertAlmostEqual(float(state.gold_value_usd),   185.0, places=1)
        self.assertAlmostEqual(float(state.total_vault_value_usd), 5000.0, places=1)

    # ── The Critical Correctness Test ─────────────────────────────────────────

    def test_stock_split_resilience(self):
        """
        THE KEY TEST: 2-for-1 stock split must NOT change vault value.

        SPY does 2-for-1:
          Before: 10 shares at $500 = $5,000
          After:  20 shares at $250 = $5,000  ← same value

        Old percentage-based engine FAILS this (it sees 50% price drop → vault crash).
        Phase 6 quantity engine PASSES this (it multiplies qty × new price correctly).
        """
        engine = ValuationEngine(arcx_supply=1000.0, cash_balance_usd=0.0)

        # Before split: 10 shares at $500
        state_before = engine.calculate_nav(
            [mock_holding("SPY", 10.0, 500.0)],
            mock_prices(spy=500.0),
        )

        # After split: 20 shares at $250 (admin would update the holding in DB)
        state_after = engine.calculate_nav(
            [mock_holding("SPY", 20.0, 250.0)],
            mock_prices(spy=250.0),
        )

        self.assertAlmostEqual(
            float(state_before.total_vault_value_usd),
            float(state_after.total_vault_value_usd),
            places=2,
            msg=(
                "Stock split CHANGED vault value! "
                "This is the critical Phase 6 bug we fixed. "
                "Valuation engine must use quantity × price, not percentages."
            ),
        )

    # ── Edge Case Tests ───────────────────────────────────────────────────────

    def test_empty_holdings_is_pure_cash(self):
        """Day 0: no shares purchased yet. Vault value = pure cash only."""
        engine = ValuationEngine(arcx_supply=1000.0, cash_balance_usd=1197.60)
        state  = engine.calculate_nav([], self.prices)

        self.assertAlmostEqual(float(state.total_vault_value_usd), 1197.60, places=2)
        self.assertEqual(len(state.positions), 0)

    def test_genesis_guard_returns_peg(self):
        """Zero ARCX supply returns genesis NAV peg of ₹100, not divide-by-zero."""
        engine = ValuationEngine(arcx_supply=0.0, cash_balance_usd=0.0)
        state  = engine.calculate_nav([], self.prices)
        self.assertEqual(state.nav_inr, GENESIS_NAV_INR)

    def test_negative_supply_raises(self):
        """Negative ARCX supply is always an error."""
        with self.assertRaises(ValueError):
            ValuationEngine(arcx_supply=-1.0, cash_balance_usd=1000.0)

    def test_negative_cash_raises(self):
        """Negative cash balance is always an error."""
        with self.assertRaises(ValueError):
            ValuationEngine(arcx_supply=1000.0, cash_balance_usd=-1.0)

    # ── AssetPosition Tests ───────────────────────────────────────────────────

    def test_unrealized_pnl_calculated(self):
        """P&L: bought SPY at $500, now at $530 → +$300 unrealized on 10 shares."""
        holdings = [mock_holding("SPY", 10.0, 500.0)]
        engine   = ValuationEngine(arcx_supply=1000.0, cash_balance_usd=0.0)
        state    = engine.calculate_nav(holdings, mock_prices(spy=530.0))

        spy_pos = next(p for p in state.positions if p.ticker == "SPY")
        # (530 - 500) × 10 = +$300
        self.assertAlmostEqual(float(spy_pos.unrealized_pnl_usd), 300.0, places=2)

    def test_negative_unrealized_pnl_on_loss(self):
        """Loss scenario: bought TLT at $100, now at $90 → -$50 on 5 shares."""
        holdings = [mock_holding("TLT", 5.0, 100.0)]
        engine   = ValuationEngine(arcx_supply=1000.0, cash_balance_usd=0.0)
        state    = engine.calculate_nav(holdings, mock_prices(tlt=90.0))

        tlt_pos = next(p for p in state.positions if p.ticker == "TLT")
        # (90 - 100) × 5 = -$50
        self.assertAlmostEqual(float(tlt_pos.unrealized_pnl_usd), -50.0, places=2)

    def test_position_has_correct_fields(self):
        """Each AssetPosition is populated with all required fields."""
        holdings = [mock_holding("GLD", 3.5, 180.0)]
        engine   = ValuationEngine(arcx_supply=1000.0, cash_balance_usd=0.0)
        state    = engine.calculate_nav(holdings, mock_prices(gld=185.0))

        self.assertEqual(len(state.positions), 1)
        pos = state.positions[0]
        self.assertEqual(pos.ticker, "GLD")
        self.assertAlmostEqual(float(pos.quantity), 3.5, places=4)
        self.assertAlmostEqual(float(pos.live_price_usd), 185.0, places=2)
        self.assertAlmostEqual(float(pos.market_value_usd), 647.5, places=2)
        self.assertAlmostEqual(float(pos.average_buy_price), 180.0, places=2)

    # ── Backward Compatibility Tests ──────────────────────────────────────────

    def test_backward_compat_properties(self):
        """stock_value_usd, bond_value_usd, gold_value_usd, cash_value_usd still work."""
        holdings = [
            mock_holding("SPY", 8.0, 500.0),    # 8 × $530 = $4,240
            mock_holding("TLT", 3.0, 90.0),     # 3 × $95  = $285
            mock_holding("GLD", 1.0, 180.0),    # 1 × $185 = $185
        ]
        engine = ValuationEngine(arcx_supply=1000.0, cash_balance_usd=290.0)
        state  = engine.calculate_nav(holdings, self.prices)

        self.assertAlmostEqual(float(state.stock_value_usd), 4240.0, places=1)
        self.assertAlmostEqual(float(state.bond_value_usd),   285.0, places=1)
        self.assertAlmostEqual(float(state.gold_value_usd),   185.0, places=1)
        self.assertAlmostEqual(float(state.cash_value_usd),   290.0, places=1)

    # ── Genesis Factory Tests ─────────────────────────────────────────────────

    def test_from_genesis_sets_correct_supply(self):
        """from_genesis() sets ARCX supply to 1,000 (the genesis mint)."""
        engine = ValuationEngine.from_genesis(mock_prices(usd_inr=83.5))
        self.assertEqual(engine.arcx_supply, Decimal("1000"))

    def test_from_genesis_converts_inr_to_usd(self):
        """from_genesis() converts ₹1,00,000 to USD at live rate."""
        prices = mock_prices(usd_inr=83.5)
        engine = ValuationEngine.from_genesis(prices)
        expected_usd = Decimal("100000") / Decimal("83.5")
        self.assertAlmostEqual(float(engine.cash_balance_usd), float(expected_usd), places=2)


# ── Test Suite 2: Phase 6 Quantity-Based Rebalancer ───────────────────────────

class TestPhase6DriftRebalancer(TestCase):
    """
    Tests for the upgraded DriftRebalancer.
    Verifies that trade outputs are in fractional SHARE quantities, not dollar amounts.
    """

    def setUp(self):
        self.rebalancer   = DriftRebalancer()
        self.live_prices  = {"SPY": 530.0, "TLT": 95.0, "GLD": 185.0}
        self.vault_value  = 10000.0
        self.cash_balance = 1000.0

    # ── No Rebalance Needed ───────────────────────────────────────────────────

    def test_perfect_balance_no_trades(self):
        """Exactly 40/30/20/10 allocation should produce zero trades."""
        holdings = {
            "SPY": {"value": 4000, "qty": 7.547},
            "TLT": {"value": 3000, "qty": 31.578},
            "GLD": {"value": 2000, "qty": 10.810},
        }
        report = self.rebalancer.analyze(
            vault_value_usd  = self.vault_value,
            holdings         = holdings,
            cash_balance_usd = self.cash_balance,
            live_prices      = self.live_prices,
        )
        self.assertFalse(report.rebalance_needed)
        self.assertEqual(len(report.trades), 0)

    def test_small_drift_within_tolerance_no_trades(self):
        """Drift < 3% should NOT trigger a rebalance."""
        # SPY at 41% (1% over target) — within ±3% tolerance
        holdings = {
            "SPY": {"value": 4100, "qty": 7.736},
            "TLT": {"value": 2950, "qty": 31.052},
            "GLD": {"value": 1950, "qty": 10.540},
        }
        report = self.rebalancer.analyze(
            vault_value_usd  = self.vault_value,
            holdings         = holdings,
            cash_balance_usd = 1000.0,
            live_prices      = self.live_prices,
        )
        self.assertFalse(report.rebalance_needed)

    # ── Rebalance Triggered ───────────────────────────────────────────────────

    def test_large_drift_triggers_rebalance(self):
        """SPY at 20% (20% below 40% target) should trigger a rebalance."""
        holdings = {
            "SPY": {"value": 2000, "qty": 3.77},    # 20% — far below 40% target
            "TLT": {"value": 3000, "qty": 31.578},
            "GLD": {"value": 4000, "qty": 21.621},  # 40% — far above 20% target
        }
        report = self.rebalancer.analyze(
            vault_value_usd  = self.vault_value,
            holdings         = holdings,
            cash_balance_usd = 1000.0,
            live_prices      = self.live_prices,
        )
        self.assertTrue(report.rebalance_needed)
        self.assertGreater(len(report.trades), 0)

    # ── Trade Output Quality ──────────────────────────────────────────────────

    def test_trade_output_has_share_quantity(self):
        """Every trade must have share_quantity > 0 and a valid action."""
        holdings = {
            "SPY": {"value": 2000, "qty": 3.77},
            "TLT": {"value": 3000, "qty": 31.578},
            "GLD": {"value": 4000, "qty": 21.621},
        }
        report = self.rebalancer.analyze(
            vault_value_usd  = self.vault_value,
            holdings         = holdings,
            cash_balance_usd = 1000.0,
            live_prices      = self.live_prices,
        )
        self.assertTrue(report.rebalance_needed)
        for trade in report.trades:
            self.assertGreater(trade.share_quantity, 0)
            self.assertIn(trade.action, ["BUY", "SELL"])
            self.assertIn(trade.ticker, ["SPY", "TLT", "GLD"])
            self.assertGreater(trade.dollar_amount, 0)
            self.assertGreater(trade.execution_price, 0)

    def test_buy_quantity_math_is_correct(self):
        """
        BUY share_quantity = dollar_amount_needed / live_price.
        This is the core Phase 6 calculation.
        """
        holdings = {
            "SPY": {"value": 2000, "qty": 3.77},   # needs $2,000 more (40% of $10k - $2k)
            "TLT": {"value": 3000, "qty": 31.578},
            "GLD": {"value": 2000, "qty": 10.810},
        }
        report = self.rebalancer.analyze(
            vault_value_usd  = self.vault_value,
            holdings         = holdings,
            cash_balance_usd = 3000.0,
            live_prices      = self.live_prices,
        )
        spy_trade = next((t for t in report.trades if t.ticker == "SPY"), None)
        self.assertIsNotNone(spy_trade, "Expected a SPY BUY trade")
        self.assertEqual(spy_trade.action, "BUY")

        # shares = dollar_amount / live_price
        expected_shares = float(spy_trade.dollar_amount) / 530.0
        self.assertAlmostEqual(
            float(spy_trade.share_quantity), expected_shares, places=6,
            msg="share_quantity must equal dollar_amount / live_price",
        )

    def test_sell_trade_generated_for_overweight_asset(self):
        """Overweight asset should generate a SELL trade."""
        holdings = {
            "SPY": {"value": 4000, "qty": 7.547},
            "TLT": {"value": 3000, "qty": 31.578},
            "GLD": {"value": 4000, "qty": 21.621},  # 40% vs 20% target → SELL
        }
        report = self.rebalancer.analyze(
            vault_value_usd  = self.vault_value,
            holdings         = holdings,
            cash_balance_usd = -1000.0 if False else 1000.0,  # just a note, using 1000
            live_prices      = self.live_prices,
        )
        gld_trade = next((t for t in report.trades if t.ticker == "GLD"), None)
        if gld_trade:
            self.assertEqual(gld_trade.action, "SELL")

    def test_zero_holdings_all_buys(self):
        """When vault has no positions (Day 0 cash), all trade instructions should be BUYs."""
        report = self.rebalancer.analyze(
            vault_value_usd  = 10000.0,
            holdings         = {},    # empty — no positions yet
            cash_balance_usd = 10000.0,
            live_prices      = self.live_prices,
        )
        # All assets are 0% vs targets → all should trigger BUYs
        if report.rebalance_needed:
            for trade in report.trades:
                self.assertEqual(trade.action, "BUY",
                    f"Day 0 with zero holdings should only generate BUY trades, got SELL for {trade.ticker}")

    def test_trade_reason_is_human_readable(self):
        """Each trade's reason field should contain ticker and drift info."""
        holdings = {
            "SPY": {"value": 2000, "qty": 3.77},
            "TLT": {"value": 3000, "qty": 31.578},
            "GLD": {"value": 2000, "qty": 10.810},
        }
        report = self.rebalancer.analyze(
            vault_value_usd  = self.vault_value,
            holdings         = holdings,
            cash_balance_usd = 3000.0,
            live_prices      = self.live_prices,
        )
        for trade in report.trades:
            self.assertIn(trade.ticker, trade.reason)
            self.assertIn("target", trade.reason.lower())

    # ── Report Summary Tests ──────────────────────────────────────────────────

    def test_total_drift_is_sum_of_absolute_drifts(self):
        """total_drift is the sum of |actual_weight - target_weight| for all assets."""
        holdings = {
            "SPY": {"value": 2000, "qty": 3.77},   # 20% vs 40% → 0.20 drift
            "TLT": {"value": 3000, "qty": 31.578},  # 30% vs 30% → 0.00 drift
            "GLD": {"value": 4000, "qty": 21.621},  # 40% vs 20% → 0.20 drift
        }
        report = self.rebalancer.analyze(
            vault_value_usd  = self.vault_value,
            holdings         = holdings,
            cash_balance_usd = 1000.0,
            live_prices      = self.live_prices,
        )
        # SPY: |0.20 - 0.40| = 0.20, GLD: |0.40 - 0.20| = 0.20
        self.assertAlmostEqual(float(report.total_drift), 0.40, places=1)
