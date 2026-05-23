"""
ARCX Drift Rebalancer — Phase 1B
----------------------------------
Over time, asset prices move and the vault drifts from its 40/30/20/10 target.

Example:
  Gold surges 30%. Now your vault is: Stocks 37%, Bonds 28%, Gold 26%, Cash 9%.
  You are overexposed to gold. If gold crashes, your users take a bigger hit
  than they signed up for.

Solution: Rebalance when any asset drifts more than DRIFT_TOLERANCE from target.

Real funds do this:
  - Vanguard:   Monthly rebalancing with 5% tolerance bands
  - BlackRock:  Daily monitoring, rebalance at 2-3% drift
  - ARCX:       Daily monitoring, rebalance at 3% drift (configurable)

How It Works:
  1. Rebalancer checks actual weights vs target weights every day at EOD
  2. If any asset is outside tolerance → generate rebalance trade list
  3. Celery worker executes one bulk trade at 3:00 PM (batch, not instant)
  4. This minimizes broker fees (one trade per day, not per drift event)
"""

from dataclasses import dataclass, field
from typing import List
from arcx_backend.domain.oracle import MarketPrices

# ── Target Allocation ─────────────────────────────────────────────────────────
TARGET_WEIGHTS = {
    "stocks": 0.40,
    "bonds": 0.30,
    "gold": 0.20,
    "cash": 0.10,
}

# ── Drift Tolerance: ±3% from target triggers rebalance ──────────────────────
DRIFT_TOLERANCE = 0.03


@dataclass
class AssetWeight:
    """Current vs target weight for one asset."""
    asset: str
    target_weight: float
    actual_weight: float
    drift: float  # actual - target (positive = overweight)
    needs_rebalance: bool


@dataclass
class RebalanceTrade:
    """A single trade instruction to rebalance one asset."""
    asset: str
    action: str  # "BUY" or "SELL"
    amount_usd: float  # How much to buy or sell
    reason: str


@dataclass
class RebalanceReport:
    """Full rebalancing analysis for today."""
    weights: List[AssetWeight]
    trades: List[RebalanceTrade]
    rebalance_needed: bool
    total_drift: float  # Sum of absolute drifts
    vault_value_usd: float


class DriftRebalancer:
    """
    Monitors vault allocation and generates rebalancing instructions.

    This class only GENERATES trade instructions.
    It does NOT execute trades directly.
    In Phase 3 (Django), the Celery EOD task will read these instructions
    and execute them via the broker API.
    """

    def analyze(
            self,
            vault_value_usd: float,
            stock_value_usd: float,
            bond_value_usd: float,
            gold_value_usd: float,
            cash_value_usd: float,
    ) -> RebalanceReport:
        """
        Analyzes current vault allocation vs targets.
        Returns a RebalanceReport with trade instructions if needed.
        """
        actual_values = {
            "stocks": stock_value_usd,
            "bonds": bond_value_usd,
            "gold": gold_value_usd,
            "cash": cash_value_usd,
        }

        # ── Step 1: Calculate actual weights ─────────────────────────────
        weights = []
        for asset, target in TARGET_WEIGHTS.items():
            actual = actual_values[asset] / vault_value_usd if vault_value_usd > 0 else 0
            drift = actual - target
            weights.append(AssetWeight(
                asset=asset,
                target_weight=target,
                actual_weight=round(actual, 4),
                drift=round(drift, 4),
                needs_rebalance=abs(drift) > DRIFT_TOLERANCE,
            ))

        # ── Step 2: Generate trade instructions ───────────────────────────
        trades = []
        rebalance_needed = any(w.needs_rebalance for w in weights)

        if rebalance_needed:
            for w in weights:
                if abs(w.drift) > DRIFT_TOLERANCE:
                    target_value = vault_value_usd * w.target_weight
                    actual_value = actual_values[w.asset]
                    delta_usd = target_value - actual_value

                    action = "BUY" if delta_usd > 0 else "SELL"
                    trades.append(RebalanceTrade(
                        asset=w.asset,
                        action=action,
                        amount_usd=round(abs(delta_usd), 2),
                        reason=(
                            f"{w.asset} drifted {w.drift * 100:+.1f}% from target. "
                            f"Actual: {w.actual_weight * 100:.1f}%, "
                            f"Target: {w.target_weight * 100:.1f}%"
                        ),
                    ))

        total_drift = round(sum(abs(w.drift) for w in weights), 4)

        return RebalanceReport(
            weights=weights,
            trades=trades,
            rebalance_needed=rebalance_needed,
            total_drift=total_drift,
            vault_value_usd=vault_value_usd,
        )
