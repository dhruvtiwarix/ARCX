"""
ARCX Phase 1B — Unit Tests
----------------------------
Tests for dividend accrual, drift rebalancer, and multi-source oracle.
All tests use mock data. No internet required.

Run with: python -m pytest tests/ -v
"""

import pytest
from datetime import datetime
from arcx_backend.domain.oracle import MarketPrices
from arcx_backend.domain.valuation import ValuationEngine, GenesisVault
from arcx_backend.domain.dividend import DividendAccrualEngine, ANNUAL_YIELDS, WEIGHTS, DAYS_IN_YEAR
from arcx_backend.domain.rebalancer import DriftRebalancer, DRIFT_TOLERANCE

MOCK_PRICES = MarketPrices(
    spy=530.00, tlt=95.00, gld=185.00, usd_inr=83.50,
    fetched_at=datetime.now(),
)


# ── Dividend Tests ────────────────────────────────────────────────────────────

class TestDividendAccrual:

    def setup_method(self):
        self.engine = DividendAccrualEngine()
        self.vault_usd = 100_000 / MOCK_PRICES.usd_inr  # ~$1197.60
        self.supply = 1000.0

    def test_gold_yields_zero(self):
        """Gold pays no dividends. Ever."""
        result = self.engine.accrue_daily_yield(self.vault_usd, self.supply, MOCK_PRICES)
        assert result.gold_yield_usd == 0.0

    def test_bonds_yield_most(self):
        """Bonds (4%) should yield more daily than stocks (1.3%) or cash."""
        result = self.engine.accrue_daily_yield(self.vault_usd, self.supply, MOCK_PRICES)
        assert result.bond_yield_usd > result.stock_yield_usd

    def test_total_yield_positive(self):
        """Total daily yield must always be positive."""
        result = self.engine.accrue_daily_yield(self.vault_usd, self.supply, MOCK_PRICES)
        assert result.total_yield_usd > 0

    def test_annual_projection_blended_yield(self):
        """Blended annual yield: 40*1.3 + 30*4.0 + 20*0 + 10*5.0 = 2.22%"""
        projection = self.engine.project_annual_yield(self.vault_usd, MOCK_PRICES)
        expected = (0.40*1.30 + 0.30*4.00 + 0.20*0 + 0.10*5.00)
        assert abs(projection["total"]["blended_yield_pct"] - expected) < 0.01

    def test_daily_yield_times_365_equals_annual(self):
        """Daily yield * 365 should approximately equal annual yield."""
        result = self.engine.accrue_daily_yield(self.vault_usd, self.supply, MOCK_PRICES)
        projection = self.engine.project_annual_yield(self.vault_usd, MOCK_PRICES)
        assert abs(result.total_yield_usd * 365 - projection["total"]["annual_yield_usd"]) < 0.01


# ── Rebalancer Tests ──────────────────────────────────────────────────────────

class TestDriftRebalancer:

    def setup_method(self):
        self.rebalancer = DriftRebalancer()
        self.vault_usd = 10_000.0

    def test_no_rebalance_when_perfectly_balanced(self):
        """Perfect 40/30/20/10 split should not trigger rebalance."""
        report = self.rebalancer.analyze(
            vault_value_usd=self.vault_usd,
            stock_value_usd=4000, bond_value_usd=3000,
            gold_value_usd=2000,  cash_value_usd=1000,
        )
        assert report.rebalance_needed is False
        assert len(report.trades) == 0

    def test_rebalance_triggered_when_gold_surges(self):
        """If gold becomes 30% (drifted +10%), rebalance must trigger."""
        report = self.rebalancer.analyze(
            vault_value_usd=self.vault_usd,
            stock_value_usd=3500, bond_value_usd=2500,
            gold_value_usd=3000,  cash_value_usd=1000,
        )
        assert report.rebalance_needed is True

    def test_rebalance_sell_overweight_asset(self):
        """Overweight asset must generate a SELL trade."""
        report = self.rebalancer.analyze(
            vault_value_usd=self.vault_usd,
            stock_value_usd=3500, bond_value_usd=2500,
            gold_value_usd=3000,  cash_value_usd=1000,
        )
        gold_trade = next((t for t in report.trades if t.asset == "gold"), None)
        assert gold_trade is not None
        assert gold_trade.action == "SELL"

    def test_rebalance_buy_underweight_asset(self):
        """Underweight asset must generate a BUY trade."""
        report = self.rebalancer.analyze(
            vault_value_usd=self.vault_usd,
            stock_value_usd=3500, bond_value_usd=2500,
            gold_value_usd=3000,  cash_value_usd=1000,
        )
        # Stocks and bonds are underweight
        buy_trades = [t for t in report.trades if t.action == "BUY"]
        assert len(buy_trades) > 0

    def test_tolerance_boundary(self):
        """Drift exactly at tolerance should NOT trigger rebalance."""
        # Gold at exactly 23% (20% target + 3% tolerance = boundary)
        gold_value = self.vault_usd * (0.20 + DRIFT_TOLERANCE)
        remaining  = self.vault_usd - gold_value
        report = self.rebalancer.analyze(
            vault_value_usd=self.vault_usd,
            stock_value_usd=remaining * 0.50,
            bond_value_usd=remaining  * 0.375,
            gold_value_usd=gold_value,
            cash_value_usd=remaining  * 0.125,
        )
        gold_weight = next(w for w in report.weights if w.asset == "gold")
        assert not gold_weight.needs_rebalance
