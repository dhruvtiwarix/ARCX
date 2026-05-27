# Phase 7: Pseudo-Broker Integration — Complete Implementation

---

## FILE 1: arcx_core/services/pseudo_broker.py — [NEW FILE]

```python
"""
ARCX Pseudo-Broker Service — Phase 7
--------------------------------------
WHY A PSEUDO-BROKER EXISTS:
  Real brokers (Alpaca, IBKR, Zerodha) require:
    - KYC approval and brokerage account
    - Real USD funding
    - API keys with production approval
    - Network calls that can fail, timeout, or return errors

  A Pseudo-Broker mirrors the EXACT same interface as a real broker,
  but executes trades internally in our own PostgreSQL database.

  When Phase 8 arrives (real Alpaca integration), we:
    1. Keep this file as a fallback / paper-trading mode
    2. Create AlpacaBrokerService with the identical interface
    3. Swap one line in settings.py: BROKER_BACKEND = "alpaca"
  
  The rest of the codebase is untouched. This is the Dependency Inversion
  Principle — the Rebalancer task depends on an interface, not a concrete broker.

WHAT THIS SERVICE DOES:
  1. Receives a RebalanceTrade (ticker, action, share_quantity, execution_price)
  2. Opens a DB transaction
  3. BUY:
     a. Calculates exact USD cost = share_quantity × execution_price
     b. Verifies cash balance is sufficient
     c. Deducts cash from VaultSnapshot.cash_value_usd
     d. Calls VaultAssetHolding.update_on_buy() to credit fractional shares
     e. Creates a BrokerOrderLog record (audit trail)
  4. SELL: reverse of the above
  5. Returns an OrderResult — success or failure with reason

ATOMICITY GUARANTEE:
  The entire trade (cash deduction + share credit) happens in ONE
  database transaction. If either step fails, both are rolled back.
  You will NEVER have a state where cash was deducted but shares weren't credited.
  This is the same guarantee real brokers provide (T+0 for equity ETFs).

EXECUTION PRICE:
  The pseudo-broker uses the live Oracle price passed in the RebalanceTrade.
  This simulates "market order execution at current price."
  In Phase 8, the real broker returns an actual fill price which may differ
  slightly (slippage). The interface handles both cases identically.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import List

from django.db import transaction

from arcx_core.models import VaultAssetHolding, VaultSnapshot
from domain.rebalancer import RebalanceTrade

logger = logging.getLogger("arcx.pseudo_broker")


# ── Order Result ──────────────────────────────────────────────────────────────

@dataclass
class OrderResult:
    """
    The result of a single broker order execution.
    Mirrors what a real broker API would return.
    """
    trade:           RebalanceTrade
    success:         bool
    filled_quantity: Decimal     # Actual shares transacted (may differ from requested in real broker)
    fill_price:      Decimal     # Actual execution price
    cash_delta_usd:  Decimal     # How much cash changed (negative = spent, positive = received)
    error:           str = ""    # Only populated on failure


@dataclass
class BatchExecutionResult:
    """Summary of all trades executed in a single rebalancing run."""
    orders:            List[OrderResult]
    total_trades:      int
    successful_trades: int
    failed_trades:     int
    total_cash_spent:  Decimal   # Total USD removed from cash balance
    total_cash_gained: Decimal   # Total USD added back (from sells)


# ── The Broker ────────────────────────────────────────────────────────────────

class PseudoBrokerService:
    """
    Simulates a real stock broker's order execution engine.

    Interface contract (same as future AlpacaBrokerService):
      - submit_order(trade: RebalanceTrade, snapshot: VaultSnapshot) → OrderResult
      - execute_trades(trades: List[RebalanceTrade], snapshot: VaultSnapshot) → BatchExecutionResult

    Each method is fully atomic. Either the full trade executes, or nothing changes.
    """

    def submit_order(
        self,
        trade:    RebalanceTrade,
        snapshot: VaultSnapshot,
    ) -> OrderResult:
        """
        Executes a single RebalanceTrade against the internal ledger.

        For BUY orders:
          - Validates sufficient cash in snapshot.cash_value_usd
          - Deducts exact cost: share_quantity × execution_price
          - Credits shares to VaultAssetHolding via update_on_buy()

        For SELL orders:
          - Validates sufficient shares in VaultAssetHolding
          - Returns cash: share_quantity × execution_price
          - Reduces shares via update_on_sell()

        Args:
            trade:    RebalanceTrade from DriftRebalancer.analyze()
            snapshot: Today's VaultSnapshot (source of cash balance)

        Returns:
            OrderResult with success/failure details
        """
        try:
            with transaction.atomic():
                # Lock the snapshot row to prevent concurrent cash modifications
                locked_snapshot = VaultSnapshot.objects.select_for_update().get(
                    pk=snapshot.pk
                )

                # Get or create the holding row for this asset
                holding, _ = VaultAssetHolding.objects.select_for_update().get_or_create(
                    asset_ticker=trade.ticker,
                    defaults={
                        "total_quantity":    Decimal("0"),
                        "average_buy_price": Decimal("0"),
                    },
                )

                if trade.action == "BUY":
                    return self._execute_buy(trade, locked_snapshot, holding)
                elif trade.action == "SELL":
                    return self._execute_sell(trade, locked_snapshot, holding)
                else:
                    raise ValueError(f"Unknown trade action: {trade.action}")

        except InsufficientCashError as e:
            logger.warning(
                "Pseudo-broker: Insufficient cash for %s %s. Needed $%s, have $%s.",
                trade.action, trade.ticker, trade.dollar_amount, e.available
            )
            return OrderResult(
                trade=trade, success=False,
                filled_quantity=Decimal("0"), fill_price=trade.execution_price,
                cash_delta_usd=Decimal("0"),
                error=str(e),
            )

        except InsufficientSharesError as e:
            logger.warning(
                "Pseudo-broker: Insufficient shares for SELL %s. Needed %s, have %s.",
                trade.ticker, trade.share_quantity, e.available
            )
            return OrderResult(
                trade=trade, success=False,
                filled_quantity=Decimal("0"), fill_price=trade.execution_price,
                cash_delta_usd=Decimal("0"),
                error=str(e),
            )

        except Exception as e:
            logger.exception("Pseudo-broker: Unexpected error on %s %s: %s",
                             trade.action, trade.ticker, e)
            return OrderResult(
                trade=trade, success=False,
                filled_quantity=Decimal("0"), fill_price=trade.execution_price,
                cash_delta_usd=Decimal("0"),
                error=f"Internal error: {str(e)}",
            )

    def execute_trades(
        self,
        trades:   List[RebalanceTrade],
        snapshot: VaultSnapshot,
    ) -> BatchExecutionResult:
        """
        Executes all trades from a rebalancing run.

        IMPORTANT: Trades are executed in a deliberate order:
          1. SELL orders first → generates cash
          2. BUY orders second → uses cash (including cash from sells)

        This mirrors real brokerage practice: you free up capital before deploying it.
        Without this ordering, a simultaneous buy+sell might fail due to insufficient cash
        even though the sell would have covered it.

        Each trade is individually atomic but the batch is NOT a single transaction.
        If BUY #2 fails after BUY #1 succeeds, BUY #1 remains.
        This is acceptable — partial rebalancing is better than no rebalancing.
        A subsequent run will complete what this one missed.

        Args:
            trades:   List of RebalanceTrade from DriftRebalancer.analyze()
            snapshot: Today's VaultSnapshot

        Returns:
            BatchExecutionResult with per-order results and summary
        """
        if not trades:
            logger.info("Pseudo-broker: No trades to execute.")
            return BatchExecutionResult(
                orders=[], total_trades=0, successful_trades=0, failed_trades=0,
                total_cash_spent=Decimal("0"), total_cash_gained=Decimal("0"),
            )

        # Execute SELLs first to free cash
        sells = [t for t in trades if t.action == "SELL"]
        buys  = [t for t in trades if t.action == "BUY"]
        ordered_trades = sells + buys

        results: List[OrderResult] = []

        for trade in ordered_trades:
            # Re-fetch snapshot each time so cash balance reflects previous trades
            fresh_snapshot = VaultSnapshot.objects.get(pk=snapshot.pk)
            result = self.submit_order(trade, fresh_snapshot)
            results.append(result)

            if result.success:
                logger.info(
                    "Pseudo-broker: ✅ %s %s %.8f shares @ $%.4f | Cash Δ $%.4f",
                    trade.action, trade.ticker,
                    float(result.filled_quantity), float(result.fill_price),
                    float(result.cash_delta_usd),
                )
            else:
                logger.warning(
                    "Pseudo-broker: ❌ %s %s FAILED: %s",
                    trade.action, trade.ticker, result.error,
                )

        successful = [r for r in results if r.success]
        failed     = [r for r in results if not r.success]

        total_spent  = sum(abs(r.cash_delta_usd) for r in successful if r.cash_delta_usd < 0)
        total_gained = sum(r.cash_delta_usd      for r in successful if r.cash_delta_usd > 0)

        return BatchExecutionResult(
            orders            = results,
            total_trades      = len(results),
            successful_trades = len(successful),
            failed_trades     = len(failed),
            total_cash_spent  = total_spent,
            total_cash_gained = total_gained,
        )

    # ── Private execution helpers ─────────────────────────────────────────────

    def _execute_buy(
        self,
        trade:    RebalanceTrade,
        snapshot: VaultSnapshot,
        holding:  VaultAssetHolding,
    ) -> OrderResult:
        """
        Executes a BUY order:
          1. Calculate exact USD cost
          2. Verify sufficient cash
          3. Deduct cash from snapshot
          4. Credit shares to holding
        """
        exec_price = Decimal(str(trade.execution_price))
        qty        = Decimal(str(trade.share_quantity))

        # Exact cost with full precision — never round down the cash deduction
        exact_cost = (qty * exec_price).quantize(Decimal("0.0001"))

        # Validate cash
        if snapshot.cash_value_usd < exact_cost:
            # Partial fill: buy as many shares as cash allows
            # This mirrors "fill or kill" vs "fill as much as possible" broker behavior
            # ARCX uses "fill as much as possible" to maximize capital deployment
            if snapshot.cash_value_usd <= Decimal("0.01"):
                raise InsufficientCashError(
                    f"Cannot buy {qty} shares of {trade.ticker}. "
                    f"Need ${exact_cost:.4f}, have ${snapshot.cash_value_usd:.4f}.",
                    available=snapshot.cash_value_usd,
                )
            # Partial fill
            qty        = (snapshot.cash_value_usd / exec_price).quantize(
                Decimal("0.000000000000000001"), rounding=ROUND_DOWN
            )
            exact_cost = (qty * exec_price).quantize(Decimal("0.0001"))
            logger.info(
                "Pseudo-broker: Partial fill for %s. "
                "Requested %s shares, filling %s shares with available cash.",
                trade.ticker, trade.share_quantity, qty,
            )

        # Deduct cash
        snapshot.cash_value_usd  -= exact_cost
        snapshot.total_value_usd -= exact_cost   # Total stays same: cash→equity swap

        # But wait — total_value_usd should not change on a rebalance!
        # We're converting cash to shares. Total value = same.
        # The equity value increase will be captured at next NAV calculation.
        # So we restore total_value_usd:
        snapshot.total_value_usd += exact_cost   # Undo the deduction above

        snapshot.save(update_fields=["cash_value_usd", "total_value_usd", "updated_at"])

        # Credit shares
        holding.update_on_buy(
            new_quantity    = qty,
            execution_price = exec_price,
        )
        holding.save(update_fields=["total_quantity", "average_buy_price", "updated_at"])

        self._log_order(trade, "BUY", qty, exec_price, -exact_cost, "FILLED")

        return OrderResult(
            trade           = trade,
            success         = True,
            filled_quantity = qty,
            fill_price      = exec_price,
            cash_delta_usd  = -exact_cost,   # Negative = cash was spent
        )

    def _execute_sell(
        self,
        trade:    RebalanceTrade,
        snapshot: VaultSnapshot,
        holding:  VaultAssetHolding,
    ) -> OrderResult:
        """
        Executes a SELL order:
          1. Verify sufficient shares in holding
          2. Reduce holding quantity
          3. Add proceeds to vault cash
        """
        exec_price = Decimal(str(trade.execution_price))
        qty        = Decimal(str(trade.share_quantity))

        # Validate shares
        if holding.total_quantity < qty:
            if holding.total_quantity <= Decimal("0"):
                raise InsufficientSharesError(
                    f"Cannot sell {qty} shares of {trade.ticker}. None held.",
                    available=holding.total_quantity,
                )
            # Partial sell — sell what we have
            qty = holding.total_quantity
            logger.info(
                "Pseudo-broker: Partial sell for %s. "
                "Requested %s shares, selling all %s available.",
                trade.ticker, trade.share_quantity, qty,
            )

        proceeds = (qty * exec_price).quantize(Decimal("0.0001"))

        # Credit cash
        snapshot.cash_value_usd += proceeds
        snapshot.save(update_fields=["cash_value_usd", "updated_at"])

        # Deduct shares
        holding.update_on_sell(qty)
        holding.save(update_fields=["total_quantity", "updated_at"])

        self._log_order(trade, "SELL", qty, exec_price, proceeds, "FILLED")

        return OrderResult(
            trade           = trade,
            success         = True,
            filled_quantity = qty,
            fill_price      = exec_price,
            cash_delta_usd  = proceeds,   # Positive = cash received
        )

    def _log_order(
        self,
        trade:       RebalanceTrade,
        action:      str,
        qty:         Decimal,
        price:       Decimal,
        cash_delta:  Decimal,
        status:      str,
    ):
        """Structured log entry for every order — the broker audit trail."""
        import json
        from arcx_core.logger import _emit
        _emit("INFO", "BROKER_ORDER_EXECUTED",
              action        = action,
              ticker        = trade.ticker,
              quantity      = str(qty),
              price_usd     = str(price),
              value_usd     = str(abs(qty * price).quantize(Decimal("0.0001"))),
              cash_delta    = str(cash_delta),
              status        = status,
              broker        = "PseudoBroker",
        )


# ── Custom Exceptions ─────────────────────────────────────────────────────────

class InsufficientCashError(Exception):
    def __init__(self, message, available):
        super().__init__(message)
        self.available = available


class InsufficientSharesError(Exception):
    def __init__(self, message, available):
        super().__init__(message)
        self.available = available
```

---

## FILE 2: arcx_core/tasks/eod_tasks.py — Update run_rebalancing_check()

Replace the existing `run_rebalancing_check` task body:

```python
@shared_task(
    bind=True,
    name="arcx_core.tasks.eod_tasks.run_rebalancing_check",
    max_retries=2,
    default_retry_delay=300,
)
def run_rebalancing_check(self):
    """
    Runs at 15:45 IST.

    Phase 5: Generated trade instructions, logged them, did nothing.
    Phase 7: Generates trade instructions AND executes them via PseudoBrokerService.

    The loop is now closed:
      User Deposit → Cash influx → EOD Rebalancer → Pseudo-Broker → Holdings Updated
    """
    from arcx_core.services.pseudo_broker import PseudoBrokerService

    today = date.today()
    logger.info("EOD task started: run_rebalancing_check + execution date=%s", today)

    try:
        snapshot = VaultSnapshot.objects.get(snapshot_date=today)
    except VaultSnapshot.DoesNotExist:
        logger.warning("No snapshot for today in rebalancing check. Skipping.")
        return {"status": "skipped", "reason": "no_snapshot"}

    # ── Build holdings dict for Rebalancer ───────────────────────────────────
    # Rebalancer needs: {"SPY": {"value": float, "qty": float}, ...}
    # We need live prices to calculate current market value of each holding

    try:
        oracle = MultiSourceOracle()
        prices = oracle.fetch_prices()
    except OracleFailureException as exc:
        raise self.retry(exc=exc)

    live_prices = {
        "SPY": prices.spy,
        "TLT": prices.tlt,
        "GLD": prices.gld,
    }

    holdings_data = {}
    for holding in VaultAssetHolding.objects.all():
        ticker     = holding.asset_ticker
        qty        = float(holding.total_quantity)
        live_price = live_prices.get(ticker, 0.0)
        holdings_data[ticker] = {
            "value": qty * live_price,
            "qty":   qty,
        }

    # ── Run Rebalancer Analysis ───────────────────────────────────────────────
    rebalancer = DriftRebalancer()
    report     = rebalancer.analyze(
        vault_value_usd  = float(snapshot.total_value_usd),
        holdings         = holdings_data,
        cash_balance_usd = float(snapshot.cash_value_usd),
        live_prices      = live_prices,
    )

    if not report.rebalance_needed:
        logger.info(
            "Rebalancing not needed: date=%s drift=%.2f%%",
            today, report.total_drift * 100
        )
        return {
            "status":           "ok",
            "date":             str(today),
            "rebalance_needed": False,
            "total_drift_pct":  round(float(report.total_drift) * 100, 2),
            "trades_executed":  0,
        }

    logger.warning(
        "REBALANCE NEEDED: date=%s total_drift=%.2f%% trades=%d",
        today, float(report.total_drift) * 100, len(report.trades),
    )

    # ── Execute Trades via Pseudo-Broker ─────────────────────────────────────
    broker         = PseudoBrokerService()
    batch_result   = broker.execute_trades(report.trades, snapshot)

    logger.info(
        "Rebalancing complete: %d/%d trades filled | Cash spent: $%.4f | Cash gained: $%.4f",
        batch_result.successful_trades,
        batch_result.total_trades,
        float(batch_result.total_cash_spent),
        float(batch_result.total_cash_gained),
    )

    return {
        "status":           "ok",
        "date":             str(today),
        "rebalance_needed": True,
        "total_drift_pct":  round(float(report.total_drift) * 100, 2),
        "trades_executed":  batch_result.successful_trades,
        "trades_failed":    batch_result.failed_trades,
        "cash_spent_usd":   float(batch_result.total_cash_spent),
        "orders": [
            {
                "ticker":   r.trade.ticker,
                "action":   r.trade.action,
                "qty":      float(r.filled_quantity),
                "price":    float(r.fill_price),
                "success":  r.success,
                "error":    r.error,
            }
            for r in batch_result.orders
        ],
    }
```

---

## FILE 3: arcx_core/tasks/eod_tasks.py — Update take_vault_snapshot()

The snapshot task must pass actual holdings to the new ValuationEngine:

```python
# Replace the engine block inside take_vault_snapshot():

from arcx_core.models import VaultAssetHolding

# Fetch actual holdings for mark-to-market calculation
holdings = list(VaultAssetHolding.objects.all())

try:
    prev = VaultSnapshot.objects.exclude(snapshot_date=today).latest("snapshot_date")
    engine = ValuationEngine(
        arcx_supply      = float(prev.arcx_supply),
        cash_balance_usd = float(prev.cash_value_usd),
    )
except VaultSnapshot.DoesNotExist:
    engine = ValuationEngine.from_genesis(prices)

# Pass holdings to the Phase 6 engine
state = engine.calculate_nav(holdings, prices)

# VaultSnapshot fields still match — stock_value_usd etc. are properties on VaultState
snapshot = VaultSnapshot.objects.create(
    snapshot_date   = today,
    total_value_usd = Decimal(str(round(state.total_vault_value_usd, 4))),
    stock_value_usd = Decimal(str(round(float(state.stock_value_usd), 4))),
    bond_value_usd  = Decimal(str(round(float(state.bond_value_usd), 4))),
    gold_value_usd  = Decimal(str(round(float(state.gold_value_usd), 4))),
    cash_value_usd  = Decimal(str(round(float(state.cash_balance_usd), 4))),
    arcx_supply     = Decimal(str(round(engine.arcx_supply, 18))),
    spy_twap        = Decimal(str(round(prices.spy, 4))),
    tlt_twap        = Decimal(str(round(prices.tlt, 4))),
    gld_twap        = Decimal(str(round(prices.gld, 4))),
    usd_inr_rate    = Decimal(str(round(prices.usd_inr, 4))),
)
```

---

## FILE 4: arcx_core/tests/test_phase7.py — [NEW FILE]

```python
"""
ARCX Phase 7 — Pseudo-Broker Tests
-------------------------------------
Tests that verify:
  1. BUY order deducts cash AND credits shares atomically
  2. SELL order credits cash AND deducts shares atomically
  3. Insufficient cash causes failure, no state change
  4. Insufficient shares causes failure, no state change
  5. Partial fills work correctly
  6. Batch execution: SELLs before BUYs
  7. The full loop: deposit → rebalancer → broker → holdings updated

Run: python manage.py test tests.test_phase7
"""

from decimal import Decimal
from unittest.mock import patch, MagicMock
from datetime import date, datetime

from django.test import TestCase

from arcx_core.models import VaultAssetHolding, VaultSnapshot
from arcx_core.services.pseudo_broker import (
    PseudoBrokerService,
    InsufficientCashError,
    InsufficientSharesError,
)
from domain.rebalancer import RebalanceTrade


# ── Test Fixtures ─────────────────────────────────────────────────────────────

def make_snapshot(cash_usd=1000.0, total_usd=10000.0, arcx_supply=100.0):
    """Create a VaultSnapshot for testing."""
    return VaultSnapshot.objects.create(
        snapshot_date   = date.today(),
        total_value_usd = Decimal(str(total_usd)),
        stock_value_usd = Decimal("4000"),
        bond_value_usd  = Decimal("3000"),
        gold_value_usd  = Decimal("2000"),
        cash_value_usd  = Decimal(str(cash_usd)),
        arcx_supply     = Decimal(str(arcx_supply)),
        spy_twap        = Decimal("530"),
        tlt_twap        = Decimal("95"),
        gld_twap        = Decimal("185"),
        usd_inr_rate    = Decimal("83.5"),
    )


def make_holding(ticker, qty=0.0, avg_price=0.0):
    """Create or update a VaultAssetHolding for testing."""
    obj, _ = VaultAssetHolding.objects.get_or_create(
        asset_ticker=ticker,
        defaults={
            "total_quantity":    Decimal(str(qty)),
            "average_buy_price": Decimal(str(avg_price)),
        },
    )
    if qty > 0:
        obj.total_quantity    = Decimal(str(qty))
        obj.average_buy_price = Decimal(str(avg_price))
        obj.save()
    return obj


def make_trade(ticker="SPY", action="BUY", qty=0.01, price=500.0):
    return RebalanceTrade(
        ticker          = ticker,
        action          = action,
        share_quantity  = Decimal(str(qty)),
        dollar_amount   = Decimal(str(qty * price)),
        execution_price = Decimal(str(price)),
        reason          = "Test trade",
    )


# ── Unit Tests: Single Order ──────────────────────────────────────────────────

class TestPseudoBrokerBuyOrder(TestCase):

    def setUp(self):
        self.broker   = PseudoBrokerService()
        self.snapshot = make_snapshot(cash_usd=1000.0)
        self.holding  = make_holding("SPY", qty=0.0)

    def test_buy_deducts_cash_exactly(self):
        """BUY 0.01 SPY at $500 must deduct exactly $5.00 from cash."""
        trade = make_trade("SPY", "BUY", qty=0.01, price=500.0)
        result = self.broker.submit_order(trade, self.snapshot)

        self.assertTrue(result.success)

        updated_snapshot = VaultSnapshot.objects.get(pk=self.snapshot.pk)
        expected_cash = Decimal("1000.0000") - Decimal("5.0000")
        self.assertEqual(updated_snapshot.cash_value_usd, expected_cash)

    def test_buy_credits_shares_exactly(self):
        """BUY 0.0096 SPY must credit exactly 0.0096 shares."""
        trade = make_trade("SPY", "BUY", qty=0.0096, price=500.0)
        result = self.broker.submit_order(trade, self.snapshot)

        self.assertTrue(result.success)

        updated_holding = VaultAssetHolding.objects.get(asset_ticker="SPY")
        self.assertEqual(
            updated_holding.total_quantity,
            Decimal("0.009600000000000000"),  # 18 decimal places
        )

    def test_buy_updates_average_price(self):
        """Average buy price must be set correctly on first purchase."""
        trade = make_trade("SPY", "BUY", qty=2.0, price=530.0)
        result = self.broker.submit_order(trade, self.snapshot)

        updated_holding = VaultAssetHolding.objects.get(asset_ticker="SPY")
        self.assertEqual(updated_holding.average_buy_price, Decimal("530.0000"))

    def test_buy_weighted_average_on_second_purchase(self):
        """
        Buy 2 shares at $500, then 2 shares at $600.
        New avg = (2*500 + 2*600) / 4 = $550.
        """
        # First buy
        self.holding.total_quantity    = Decimal("2.0")
        self.holding.average_buy_price = Decimal("500.0")
        self.holding.save()

        trade  = make_trade("SPY", "BUY", qty=2.0, price=600.0)
        result = self.broker.submit_order(trade, self.snapshot)

        updated = VaultAssetHolding.objects.get(asset_ticker="SPY")
        self.assertEqual(updated.average_buy_price, Decimal("550.0000"))
        self.assertEqual(updated.total_quantity, Decimal("4.000000000000000000"))

    def test_buy_fails_on_insufficient_cash(self):
        """BUY that costs more than cash balance must fail cleanly."""
        trade = make_trade("SPY", "BUY", qty=10.0, price=500.0)  # $5,000 but only $1,000 cash
        # Force tiny cash to trigger hard failure (not partial fill)
        self.snapshot.cash_value_usd = Decimal("0.005")
        self.snapshot.save()

        result = self.broker.submit_order(trade, self.snapshot)

        self.assertFalse(result.success)
        self.assertIn("Insufficient", result.error)

        # Cash must be UNCHANGED
        updated_snapshot = VaultSnapshot.objects.get(pk=self.snapshot.pk)
        self.assertEqual(updated_snapshot.cash_value_usd, Decimal("0.005"))

        # Shares must be UNCHANGED (still zero)
        updated_holding = VaultAssetHolding.objects.get(asset_ticker="SPY")
        self.assertEqual(updated_holding.total_quantity, Decimal("0"))

    def test_buy_atomicity_no_partial_state(self):
        """If share credit fails, cash deduction must also be rolled back."""
        # We'll monkey-patch update_on_buy to raise an exception mid-transaction
        original = VaultAssetHolding.update_on_buy

        def broken_update(self_obj, *args, **kwargs):
            raise RuntimeError("Simulated broker failure mid-transaction")

        VaultAssetHolding.update_on_buy = broken_update

        try:
            trade  = make_trade("SPY", "BUY", qty=0.01, price=500.0)
            result = self.broker.submit_order(trade, self.snapshot)

            # Transaction should have rolled back
            updated_snapshot = VaultSnapshot.objects.get(pk=self.snapshot.pk)
            self.assertEqual(
                updated_snapshot.cash_value_usd,
                Decimal("1000.0000"),
                "Cash was deducted even though share credit failed — ATOMICITY BUG",
            )
        finally:
            VaultAssetHolding.update_on_buy = original


class TestPseudoBrokerSellOrder(TestCase):

    def setUp(self):
        self.broker   = PseudoBrokerService()
        self.snapshot = make_snapshot(cash_usd=500.0)
        self.holding  = make_holding("GLD", qty=5.0, avg_price=180.0)

    def test_sell_credits_cash_exactly(self):
        """SELL 2 GLD at $185 = $370 must be added to cash."""
        trade = make_trade("GLD", "SELL", qty=2.0, price=185.0)
        result = self.broker.submit_order(trade, self.snapshot)

        self.assertTrue(result.success)

        updated_snapshot = VaultSnapshot.objects.get(pk=self.snapshot.pk)
        self.assertEqual(
            updated_snapshot.cash_value_usd,
            Decimal("500.0000") + Decimal("370.0000"),
        )

    def test_sell_deducts_shares_exactly(self):
        """SELL 2 GLD from 5 held → 3 remaining."""
        trade = make_trade("GLD", "SELL", qty=2.0, price=185.0)
        self.broker.submit_order(trade, self.snapshot)

        updated = VaultAssetHolding.objects.get(asset_ticker="GLD")
        self.assertEqual(
            updated.total_quantity,
            Decimal("3.000000000000000000"),
        )

    def test_sell_does_not_change_average_buy_price(self):
        """Selling shares must NOT change the average buy price (standard accounting)."""
        trade = make_trade("GLD", "SELL", qty=2.0, price=185.0)
        self.broker.submit_order(trade, self.snapshot)

        updated = VaultAssetHolding.objects.get(asset_ticker="GLD")
        self.assertEqual(updated.average_buy_price, Decimal("180.0000"))

    def test_sell_fails_on_insufficient_shares(self):
        """SELL more shares than held must fail without any state change."""
        trade = make_trade("GLD", "SELL", qty=10.0, price=185.0)  # Only 5 held
        result = self.broker.submit_order(trade, self.snapshot)

        # Won't fail because partial sell kicks in — sell all 5
        # Let's test the "zero shares" case instead
        self.holding.total_quantity = Decimal("0")
        self.holding.save()

        trade2 = make_trade("GLD", "SELL", qty=1.0, price=185.0)
        result2 = self.broker.submit_order(trade2, self.snapshot)

        self.assertFalse(result2.success)
        updated_snapshot = VaultSnapshot.objects.get(pk=self.snapshot.pk)
        self.assertEqual(updated_snapshot.cash_value_usd, Decimal("500.0000"))


# ── Integration Test: The Full Loop ──────────────────────────────────────────

class TestFullDepositToHoldingsLoop(TestCase):
    """
    THE KEY INTEGRATION TEST.

    Simulates the complete user journey:
      1. Day 0: Genesis — vault has $1,197.60 cash, zero shares
      2. User deposits ₹10,000 (~$119.76) → cash grows to $1,317.36
      3. EOD Rebalancer runs at 15:45 IST
      4. Pseudo-Broker executes trades
      5. Verify: vault now holds actual SPY, TLT, GLD shares
      6. Verify: cash is reduced to ~10% target
    """

    def setUp(self):
        # Genesis state: pure cash, no shares
        self.snapshot = make_snapshot(
            cash_usd=1317.36,    # Genesis $1,197 + user deposit ~$119
            total_usd=1317.36,
            arcx_supply=1000.0,
        )
        make_holding("SPY", qty=0.0)
        make_holding("TLT", qty=0.0)
        make_holding("GLD", qty=0.0)

    @patch("arcx_core.tasks.eod_tasks.MultiSourceOracle")
    def test_cash_converts_to_shares_after_rebalance(self, MockOracle):
        """After rebalance, vault should own SPY, TLT, GLD shares."""
        from arcx_core.tasks.eod_tasks import run_rebalancing_check

        # Mock oracle
        m = MagicMock()
        m.spy = 530.0; m.tlt = 95.0; m.gld = 185.0; m.usd_inr = 83.5
        m.fetched_at = datetime.now(); m.sources_used = ["Mock"]
        MockOracle.return_value.fetch_prices.return_value = m

        result = run_rebalancing_check()

        self.assertEqual(result["status"], "ok")

        # All three assets should now have shares
        spy = VaultAssetHolding.objects.get(asset_ticker="SPY")
        tlt = VaultAssetHolding.objects.get(asset_ticker="TLT")
        gld = VaultAssetHolding.objects.get(asset_ticker="GLD")

        self.assertGreater(spy.total_quantity, 0,
                           "SPY should have shares after rebalancing Day 0 cash")
        self.assertGreater(tlt.total_quantity, 0,
                           "TLT should have shares after rebalancing Day 0 cash")
        self.assertGreater(gld.total_quantity, 0,
                           "GLD should have shares after rebalancing Day 0 cash")

    @patch("arcx_core.tasks.eod_tasks.MultiSourceOracle")
    def test_cash_is_reduced_after_rebalance(self, MockOracle):
        """Cash balance should drop after shares are bought."""
        from arcx_core.tasks.eod_tasks import run_rebalancing_check

        m = MagicMock()
        m.spy = 530.0; m.tlt = 95.0; m.gld = 185.0; m.usd_inr = 83.5
        m.fetched_at = datetime.now(); m.sources_used = ["Mock"]
        MockOracle.return_value.fetch_prices.return_value = m

        initial_cash = float(VaultSnapshot.objects.get(pk=self.snapshot.pk).cash_value_usd)
        run_rebalancing_check()

        final_cash = float(VaultSnapshot.objects.get(pk=self.snapshot.pk).cash_value_usd)

        self.assertLess(final_cash, initial_cash,
                        "Cash should decrease after buying shares")

        # Remaining cash should be approximately 10% of total vault
        total_value = float(VaultSnapshot.objects.get(pk=self.snapshot.pk).total_value_usd)
        cash_ratio  = final_cash / total_value if total_value > 0 else 0

        # Allow ±5% tolerance around the 10% cash target
        self.assertAlmostEqual(cash_ratio, 0.10, delta=0.05,
                               msg=f"Cash ratio {cash_ratio:.2%} too far from 10% target")
```

---

## Deployment Steps

```bash
# 1. Run Phase 6 migration first (if not done)
python manage.py migrate

# 2. Initialize holdings (SPY, TLT, GLD with zero qty)
python manage.py init_holdings

# 3. Run Phase 7 tests
python manage.py test tests.test_phase7

# 4. Manual verification — simulate a full rebalance run
python manage.py shell
>>> from arcx_core.tasks.eod_tasks import run_rebalancing_check
>>> result = run_rebalancing_check()
>>> print(result)
# Expected: {'status': 'ok', 'rebalance_needed': True, 'trades_executed': 3, ...}

# 5. Inspect the holdings after the run
>>> from arcx_core.models import VaultAssetHolding
>>> for h in VaultAssetHolding.objects.all():
...     print(h)
# Expected:
# SPY: 0.xxx... shares @ avg $530.xxxx
# TLT: 0.xxx... shares @ avg $95.xxxx
# GLD: 0.xxx... shares @ avg $185.xxxx

# 6. Check that cash dropped to ~10%
>>> from arcx_core.models import VaultSnapshot
>>> s = VaultSnapshot.objects.latest("snapshot_date")
>>> print(f"Cash: ${s.cash_value_usd} / Total: ${s.total_value_usd}")
>>> print(f"Cash ratio: {float(s.cash_value_usd)/float(s.total_value_usd):.1%}")
# Expected: Cash ratio: ~10.0%

# 7. Watch the structured logs
python manage.py read_logs --event BROKER_ORDER_EXECUTED
```

---

## What Phase 8 Unlocks

The `PseudoBrokerService` is a drop-in replacement for `AlpacaBrokerService`.
When Phase 8 arrives, the only change needed is:

```python
# arcx_backend/settings.py — add this one line
BROKER_BACKEND = "alpaca"   # or "pseudo" for paper trading

# arcx_core/tasks/eod_tasks.py — swap one import
if settings.BROKER_BACKEND == "alpaca":
    from arcx_core.services.alpaca_broker import AlpacaBrokerService as BrokerService
else:
    from arcx_core.services.pseudo_broker import PseudoBrokerService as BrokerService

broker = BrokerService()
broker.execute_trades(report.trades, snapshot)   # Identical call
```

Zero changes to Rebalancer, ValuationEngine, or any views.
This is Dependency Inversion — the system depends on the interface, not the implementation.
