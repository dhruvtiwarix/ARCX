"""
ARCX Circuit Breaker — domain/circuit_breaker.py
---------------------------------------------------
Listed in Phase 1 but never built. This is the safety system.

WHAT IS A CIRCUIT BREAKER?
  Named after the electrical device in your house.
  When current gets dangerous, the breaker trips — cutting power
  before your appliances burn. It doesn't destroy the appliance;
  it protects it until conditions are safe again.

  In fintech, a circuit breaker halts trading/withdrawals when
  market conditions become dangerously volatile.

  Real examples:
    NYSE "Limit Up/Limit Down" (LULD) — halts trading when a stock
    moves >5-10% in 5 minutes.

    SEBI's index circuit breakers:
      10% move → 45-minute halt
      15% move → 1 hour 45-minute halt
      20% move → rest-of-day halt

  ARCX's system mirrors this logic in 3 tiers.

ARCX CIRCUIT BREAKER TIERS:
┌─────────────────────────────────────────────────────────────────┐
│  Tier 1 — CAUTION     Market drop > 5%                         │
│    Action: New deposits blocked. Withdrawals still allowed.     │
│    Reason: Users might panic-sell in a falling market.          │
│    Allow withdrawals so users don't feel trapped.               │
│                                                                 │
│  Tier 2 — WARNING     Market drop > 10%                        │
│    Action: All new deposits AND new transfers blocked.          │
│    Withdrawals still allowed (can't trap users).                │
│    Reason: Severe volatility. NAV is moving fast.               │
│                                                                 │
│  Tier 3 — EMERGENCY   Market drop > 20%                        │
│    Action: Complete halt. Read-only mode.                       │
│    Reason: Black swan event (2008-level crash).                 │
│    Both deposits AND withdrawals halted to protect vault.       │
│    Manual admin override required to resume.                    │
└─────────────────────────────────────────────────────────────────┘

SECOND TRIGGER — TVL Withdrawal Spike:
  Even without a market crash, if too many users withdraw too fast,
  the vault may not have enough liquidity to honour all requests.

  If >20% of Total Value Locked (TVL) is withdrawn in 1 hour:
    → Tier 2 triggered (slow down, reassess)

  This is called a "bank run" in traditional finance.
  ARCX's circuit breaker handles it the same way banks do:
  temporarily pause, assess, resume when safe.

IMPORTANT — This is a PURE PYTHON class.
  Zero Django. Zero database. Zero imports from arcx_core.
  It only takes numbers in, returns a decision out.
  The Celery task (arcx_core/tasks/monitoring_tasks.py) calls this
  and writes the result to the database.
  Clean Architecture at work.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CircuitBreakerTier(Enum):
    """
    The four possible states of the ARCX circuit breaker.
    NONE means everything is normal — the happy path.
    """
    NONE      = "none"       # All clear. Normal operations.
    TIER_1    = "tier_1"     # Caution. Deposits blocked.
    TIER_2    = "tier_2"     # Warning. Deposits + transfers blocked.
    TIER_3    = "tier_3"     # Emergency. Full halt.


@dataclass
class CircuitBreakerDecision:
    """
    The output of evaluate(). Tells the caller:
      - What tier fired (or NONE if all clear)
      - Whether deposits are allowed
      - Whether withdrawals are allowed
      - Whether transfers are allowed
      - A human-readable reason (logged + shown to users)
    """
    tier:               CircuitBreakerTier
    deposits_allowed:   bool
    withdrawals_allowed: bool
    transfers_allowed:  bool
    reason:             str
    market_drop_pct:    float
    tvl_withdrawal_pct: Optional[float] = None


# ── Trigger Thresholds ────────────────────────────────────────────────────────
TIER_1_MARKET_DROP  = 5.0    # 5%  drop triggers Tier 1
TIER_2_MARKET_DROP  = 10.0   # 10% drop triggers Tier 2
TIER_3_MARKET_DROP  = 20.0   # 20% drop triggers Tier 3
TVL_SPIKE_THRESHOLD = 20.0   # 20% of TVL withdrawn in 1 hour → Tier 2


class CircuitBreakerEngine:
    """
    Pure evaluation logic. No side effects. Fully testable.

    Takes in market numbers, returns a CircuitBreakerDecision.
    Never writes to the database — that is the Celery task's job.

    This design means you can run the full circuit breaker logic
    in a unit test with no database, no network, no Django.
    """

    def evaluate(
        self,
        spy_current_price:  float,
        spy_open_price:     float,
        tvl_usd:            float            = 0.0,
        withdrawn_1h_usd:   float            = 0.0,
    ) -> CircuitBreakerDecision:
        """
        Evaluate current market conditions and return a circuit breaker decision.

        Args:
            spy_current_price:  SPY price right now (from Oracle)
            spy_open_price:     SPY price at market open today (from VaultSnapshot)
            tvl_usd:            Total Value Locked in the ARCX vault (USD)
            withdrawn_1h_usd:   Total USD value withdrawn in the last hour

        Returns:
            CircuitBreakerDecision — the caller decides what to do with it
        """
        market_drop_pct   = self._market_drop_pct(spy_current_price, spy_open_price)
        tvl_withdrawal_pct = self._tvl_withdrawal_pct(tvl_usd, withdrawn_1h_usd)

        # Market drop check — checked first (takes priority)
        if market_drop_pct >= TIER_3_MARKET_DROP:
            return CircuitBreakerDecision(
                tier                = CircuitBreakerTier.TIER_3,
                deposits_allowed    = False,
                withdrawals_allowed = False,
                transfers_allowed   = False,
                reason              = (
                    f"EMERGENCY: Market dropped {market_drop_pct:.1f}% today. "
                    f"Full halt active. Manual admin override required to resume."
                ),
                market_drop_pct     = market_drop_pct,
                tvl_withdrawal_pct  = tvl_withdrawal_pct,
            )

        if market_drop_pct >= TIER_2_MARKET_DROP:
            return CircuitBreakerDecision(
                tier                = CircuitBreakerTier.TIER_2,
                deposits_allowed    = False,
                withdrawals_allowed = True,
                transfers_allowed   = False,
                reason              = (
                    f"WARNING: Market dropped {market_drop_pct:.1f}% today. "
                    f"New deposits and transfers suspended. Withdrawals still available."
                ),
                market_drop_pct     = market_drop_pct,
                tvl_withdrawal_pct  = tvl_withdrawal_pct,
            )

        if market_drop_pct >= TIER_1_MARKET_DROP:
            return CircuitBreakerDecision(
                tier                = CircuitBreakerTier.TIER_1,
                deposits_allowed    = False,
                withdrawals_allowed = True,
                transfers_allowed   = True,
                reason              = (
                    f"CAUTION: Market dropped {market_drop_pct:.1f}% today. "
                    f"New deposits paused. All other operations normal."
                ),
                market_drop_pct     = market_drop_pct,
                tvl_withdrawal_pct  = tvl_withdrawal_pct,
            )

        # TVL spike check — bank run detection
        if tvl_usd > 0 and tvl_withdrawal_pct >= TVL_SPIKE_THRESHOLD:
            return CircuitBreakerDecision(
                tier                = CircuitBreakerTier.TIER_2,
                deposits_allowed    = False,
                withdrawals_allowed = True,
                transfers_allowed   = False,
                reason              = (
                    f"WARNING: {tvl_withdrawal_pct:.1f}% of vault TVL withdrawn "
                    f"in the last hour. Unusual outflow detected. "
                    f"New deposits suspended while vault liquidity is assessed."
                ),
                market_drop_pct     = market_drop_pct,
                tvl_withdrawal_pct  = tvl_withdrawal_pct,
            )

        # All clear
        return CircuitBreakerDecision(
            tier                = CircuitBreakerTier.NONE,
            deposits_allowed    = True,
            withdrawals_allowed = True,
            transfers_allowed   = True,
            reason              = "All systems normal.",
            market_drop_pct     = market_drop_pct,
            tvl_withdrawal_pct  = tvl_withdrawal_pct,
        )

    def _market_drop_pct(self, current: float, open_price: float) -> float:
        """
        Calculate today's market drop as a positive percentage.
        Returns 0.0 if market is flat or up (circuit breaker only cares about drops).

        Example:
          open=540, current=486 → drop = (540-486)/540 * 100 = 10.0%
        """
        if open_price <= 0:
            return 0.0
        change_pct = ((open_price - current) / open_price) * 100
        return round(max(change_pct, 0.0), 2)   # Clamp at 0 — rising markets don't trip breakers

    def _tvl_withdrawal_pct(self, tvl_usd: float, withdrawn_usd: float) -> float:
        """
        What % of TVL has been withdrawn in the last hour?
        Returns 0.0 if TVL is zero (guard against division by zero).
        """
        if tvl_usd <= 0:
            return 0.0
        return round((withdrawn_usd / tvl_usd) * 100, 2)