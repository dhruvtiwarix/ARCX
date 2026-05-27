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