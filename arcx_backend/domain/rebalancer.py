"""
ARCX Drift Rebalancer — Phase 6 (Quantity-Based Trades)
---------------------------------------------------------
WHAT CHANGED FROM PHASE 5:
  Old: Trade instruction was "BUY $4.80 of SPY"
       → Cannot execute at broker. Brokers need share counts, not dollar amounts.

  New: Trade instruction is "BUY 0.0096 shares of SPY at $500.00"
       → Directly executable at Alpaca / IBKR / Zerodha via their API.

The Rebalancer still uses the 40/30/20/10 target weights to decide
WHAT to buy/sell and HOW MUCH. But the output is now share quantities,
not dollar amounts. This is what makes Phase 7 (broker integration) possible.

EXECUTION MATH:
  shares_to_trade = dollar_amount_needed / current_live_price
  e.g. Need $4.80 more of SPY. SPY is at $480.
       shares_to_buy = 4.80 / 480 = 0.01 shares

This is fractional share trading — exactly how Alpaca and IBKR work.

THE 40/30/20/10 RULE LIVES HERE AND ONLY HERE.
  The Valuation Engine no longer knows about percentages at all.
  Percentages are a targeting tool (what should we own?), not a valuation
  tool (what do we currently own?).
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

from domain.oracle import MarketPrices

# ── Target Allocation ─────────────────────────────────────────────────────────
# These are the DESIRED weights. The vault tries to stay within ±3% of each.
TARGET_WEIGHTS = {
    "SPY": Decimal("0.40"),   # 40% → US Stocks (S&P 500 ETF)
    "TLT": Decimal("0.30"),   # 30% → Bonds (20+ Year Treasury ETF)
    "GLD": Decimal("0.20"),   # 20% → Gold ETF
    # Cash (10%) is the implicit remainder — not traded via broker
}
CASH_WEIGHT     = Decimal("0.10")
DRIFT_TOLERANCE = Decimal("0.03")   # ±3% from target triggers rebalance


@dataclass
class AssetWeight:
    """Current vs target allocation for one asset."""
    ticker:          str
    target_weight:   Decimal
    actual_weight:   Decimal
    drift:           Decimal          # actual - target (positive = overweight)
    needs_rebalance: bool


@dataclass
class RebalanceTrade:
    """
    A broker-executable trade instruction.

    Phase 6 change: now contains share_quantity and execution_price,
    not just dollar_amount. This is what the broker API receives.

    Phase 7 (Alpaca integration) will read these objects and submit
    fractional share orders directly to the broker.
    """
    ticker:          str
    action:          str              # "BUY" or "SELL"
    share_quantity:  Decimal          # FRACTIONAL shares to buy/sell
    dollar_amount:   Decimal          # USD value of the trade (for logging/reporting)
    execution_price: Decimal          # Live price used to calculate shares
    reason:          str              # Human-readable explanation of why this trade was triggered


@dataclass
class RebalanceReport:
    """Complete rebalancing analysis for one run."""
    weights:          List[AssetWeight]
    trades:           List[RebalanceTrade]
    rebalance_needed: bool
    total_drift:      Decimal
    vault_value_usd:  Decimal


class DriftRebalancer:
    """
    Monitors vault allocation and generates broker-executable trade instructions.

    INPUT:  Current holdings (share values + quantities) + live prices
    OUTPUT: List of RebalanceTrade objects with exact share quantities

    This class does NOT execute trades.
    Phase 7 (Alpaca integration) will read these trades and submit them.

    USAGE (from EOD task):
        from domain.rebalancer import DriftRebalancer

        rebalancer = DriftRebalancer()
        holdings_dict = {
            "SPY": {"value": 4200.00, "qty": 7.924},
            "TLT": {"value": 3100.00, "qty": 32.63},
            "GLD": {"value": 1900.00, "qty": 10.27},
        }
        report = rebalancer.analyze(
            vault_value_usd  = 10000.0,
            holdings         = holdings_dict,
            cash_balance_usd = 1000.0,
            live_prices      = {"SPY": 530.0, "TLT": 95.0, "GLD": 185.0},
        )
    """

    def analyze(
        self,
        vault_value_usd:  float,
        holdings:         dict,    # {"SPY": {"value": 4000, "qty": 7.5}, ...}
        cash_balance_usd: float,
        live_prices:      dict,    # {"SPY": 530.00, "TLT": 95.00, "GLD": 185.00}
    ) -> RebalanceReport:
        """
        Analyzes current holdings vs target weights and generates trade instructions.

        Args:
            vault_value_usd:  Total vault value in USD (equity + cash)
            holdings:         Current holdings dict with value and quantity per ticker
            cash_balance_usd: Current cash balance in USD (not traded via broker)
            live_prices:      Current live prices from Oracle per ticker

        Returns:
            RebalanceReport with broker-executable RebalanceTrade objects
        """
        vault_usd = Decimal(str(vault_value_usd))

        # ── Step 1: Calculate actual weights ─────────────────────────────────
        weights = []
        for ticker, target in TARGET_WEIGHTS.items():
            holding    = holdings.get(ticker, {"value": 0, "qty": 0})
            actual_val = Decimal(str(holding.get("value", 0)))
            actual_wt  = (actual_val / vault_usd) if vault_usd > 0 else Decimal("0")
            drift      = actual_wt - target

            weights.append(AssetWeight(
                ticker          = ticker,
                target_weight   = target,
                actual_weight   = actual_wt.quantize(Decimal("0.0001")),
                drift           = drift.quantize(Decimal("0.0001")),
                needs_rebalance = abs(drift) > DRIFT_TOLERANCE,
            ))

        # ── Step 2: Generate quantity-based trade instructions ─────────────────
        trades: List[RebalanceTrade] = []
        rebalance_needed = any(w.needs_rebalance for w in weights)

        if rebalance_needed:
            for w in weights:
                if abs(w.drift) <= DRIFT_TOLERANCE:
                    continue

                target_value = vault_usd * w.target_weight
                actual_value = Decimal(str(holdings.get(w.ticker, {}).get("value", 0)))
                delta_usd    = target_value - actual_value   # + = need to buy, - = need to sell

                live_price   = Decimal(str(live_prices.get(w.ticker, 1)))
                if live_price <= 0:
                    continue

                # ── THE KEY PHASE 6 CALCULATION ───────────────────────────────
                # Dollar amount needed → fractional shares to trade
                # This is the exact calculation a broker API requires.
                share_quantity = (abs(delta_usd) / live_price).quantize(
                    Decimal("0.000000000000000001")
                )

                action = "BUY" if delta_usd > 0 else "SELL"

                trades.append(RebalanceTrade(
                    ticker          = w.ticker,
                    action          = action,
                    share_quantity  = share_quantity,
                    dollar_amount   = abs(delta_usd).quantize(Decimal("0.01")),
                    execution_price = live_price,
                    reason          = (
                        f"{w.ticker} drifted {float(w.drift) * 100:+.1f}% from target "
                        f"({float(w.actual_weight) * 100:.1f}% actual vs "
                        f"{float(w.target_weight) * 100:.1f}% target). "
                        f"{action} {float(share_quantity):.8f} shares @ ${float(live_price):.2f}"
                    ),
                ))

        total_drift = sum(abs(w.drift) for w in weights)

        return RebalanceReport(
            weights          = weights,
            trades           = trades,
            rebalance_needed = rebalance_needed,
            total_drift      = total_drift.quantize(Decimal("0.0001")),
            vault_value_usd  = vault_usd,
        )
