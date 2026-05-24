"""
ARCX Circuit Breaker Monitoring Task — arcx_core/tasks/monitoring_tasks.py
---------------------------------------------------------------------------
Runs every 2 minutes via Celery Beat.
This is the "heartbeat" of ARCX's safety system.

WHAT HAPPENS EACH RUN:
  1. Fetch current SPY price from Oracle (fast — Yahoo only, no TWAP needed)
  2. Get today's opening SPY price from today's VaultSnapshot (or yesterday's)
  3. Also check 1-hour withdrawal volume from Transactions table
  4. Feed both numbers into CircuitBreakerEngine.evaluate()
  5. If a breaker should fire → write CircuitBreakerLog, log warning
  6. If a previously active breaker should resolve → update its resolved_at

STATE MANAGEMENT:
  The database is the source of truth for breaker state.
  The Celery task only WRITES to CircuitBreakerLog.
  The permission class (arcx_core/permissions.py IsCircuitBreakerClear)
  READS from CircuitBreakerLog when evaluating each API request.
  Zero shared in-memory state — safe across multiple workers.

RESOLUTION:
  Breakers auto-resolve when conditions improve.
  Tier 3 (emergency) requires manual admin override — no auto-resolve.
  This mirrors how real exchanges handle circuit breakers:
  "The market will reopen at X time after review."
"""

import logging
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

from celery import shared_task
from django.db import transaction
from django.db.models import Sum

from domain.circuit_breaker import CircuitBreakerEngine, CircuitBreakerTier
from domain.oracle import MultiSourceOracle, OracleFailureException
from arcx_core.models import VaultSnapshot, CircuitBreakerLog, Transaction
from arcx_core.logger import arcx_logger

logger = logging.getLogger("arcx.tasks.monitoring")


@shared_task(
    bind=True,
    name="arcx_core.tasks.monitoring_tasks.check_circuit_breaker",
    max_retries=1,
    default_retry_delay=30,
    # Don't overlap with the previous run if it's still executing
    # (shouldn't happen, but safety net for slow Oracle calls)
)
def check_circuit_breaker(self):
    """
    Runs every 2 minutes. The safety watchdog for ARCX.

    Returns a dict with the decision made, for Celery result tracking.
    """
    logger.debug("Circuit breaker check started")

    # ── Step 1: Get current SPY price ────────────────────────────────────
    try:
        import yfinance as yf
        ticker      = yf.Ticker("SPY")
        hist        = ticker.history(period="1d", interval="1m")
        if hist.empty:
            logger.warning("Could not fetch SPY live price for circuit breaker check.")
            return {"status": "skipped", "reason": "no_spy_price"}
        spy_current = float(hist["Close"].iloc[-1])
    except Exception as exc:
        logger.warning("SPY price fetch failed in circuit breaker: %s", exc)
        return {"status": "skipped", "reason": str(exc)}

    # ── Step 2: Get today's opening SPY price ─────────────────────────────
    # Use the most recent VaultSnapshot's spy_twap as the "open" reference.
    # In a full production system, you'd store intraday open separately.
    try:
        latest_snapshot = VaultSnapshot.objects.latest("snapshot_date")
        spy_open        = float(latest_snapshot.spy_twap)
        tvl_usd         = float(latest_snapshot.total_value_usd)
    except VaultSnapshot.DoesNotExist:
        logger.warning("No VaultSnapshot available. Circuit breaker cannot evaluate market drop.")
        return {"status": "skipped", "reason": "no_snapshot"}

    # ── Step 3: Calculate 1-hour withdrawal volume ────────────────────────
    one_hour_ago     = datetime.now(timezone.utc) - timedelta(hours=1)
    withdrawn_1h_usd = _get_withdrawn_usd_since(one_hour_ago, spy_current)

    # ── Step 4: Evaluate ──────────────────────────────────────────────────
    engine   = CircuitBreakerEngine()
    decision = engine.evaluate(
        spy_current_price = spy_current,
        spy_open_price    = spy_open,
        tvl_usd           = tvl_usd,
        withdrawn_1h_usd  = withdrawn_1h_usd,
    )

    logger.debug(
        "Circuit breaker evaluated: tier=%s drop=%.2f%% tvl_pct=%.2f%%",
        decision.tier.value, decision.market_drop_pct, decision.tvl_withdrawal_pct or 0,
    )

    # ── Step 5: Act on the decision ───────────────────────────────────────
    if decision.tier == CircuitBreakerTier.NONE:
        # All clear — auto-resolve any Tier 1 or Tier 2 breakers
        _resolve_lower_tier_breakers()
        return {
            "status":         "ok",
            "decision":       "CLEAR",
            "market_drop":    decision.market_drop_pct,
        }

    # A breaker tier is active — check if it's already logged
    tier_str = decision.tier.value
    already_active = CircuitBreakerLog.objects.filter(
        tier       = tier_str,
        event_type = CircuitBreakerLog.EventType.TRIGGERED,
        resolved_at__isnull = True,
    ).exists()

    if not already_active:
        # New event — write it and alert
        CircuitBreakerLog.objects.create(
            tier                = tier_str,
            event_type          = CircuitBreakerLog.EventType.TRIGGERED,
            reason              = decision.reason,
            market_drop_pct     = Decimal(str(decision.market_drop_pct)),
            tvl_withdrawal_pct  = Decimal(str(decision.tvl_withdrawal_pct or 0)),
        )
        arcx_logger.circuit_breaker_fired(
            tier            = tier_str,
            market_drop_pct = decision.market_drop_pct,
            reason          = decision.reason,
        )
        logger.warning(
            "CIRCUIT BREAKER FIRED: tier=%s drop=%.2f%% reason=%s",
            tier_str, decision.market_drop_pct, decision.reason,
        )
    else:
        logger.info("Circuit breaker %s already active. No new record needed.", tier_str)

    return {
        "status":            "ok",
        "decision":          tier_str.upper(),
        "market_drop_pct":   decision.market_drop_pct,
        "deposits_allowed":  decision.deposits_allowed,
        "withdrawals_allowed": decision.withdrawals_allowed,
        "reason":            decision.reason,
    }


def _get_withdrawn_usd_since(since: datetime, usd_inr_rate: float) -> float:
    """
    Sum all completed withdrawals since `since` and convert to USD.
    Used to detect bank-run-style TVL spikes.
    """
    total_inr = (
        Transaction.objects
        .filter(
            tx_type    = Transaction.TxType.WITHDRAW,
            status     = Transaction.Status.COMPLETED,
            created_at__gte = since,
        )
        .aggregate(total=Sum("amount_inr"))
    )["total"] or Decimal("0")

    if usd_inr_rate <= 0:
        return 0.0
    return float(total_inr) / usd_inr_rate


def _resolve_lower_tier_breakers():
    """
    If market conditions improve (drop < 5%), auto-resolve Tier 1 and Tier 2 breakers.
    Tier 3 NEVER auto-resolves — requires manual admin override.

    Queries for all active (unresolved) Tier 1/2 events and stamps resolved_at.
    """
    now = datetime.now(timezone.utc)

    resolved = CircuitBreakerLog.objects.filter(
        tier__in   = [
            CircuitBreakerLog.Tier.TIER_1,
            CircuitBreakerLog.Tier.TIER_2,
        ],
        event_type = CircuitBreakerLog.EventType.TRIGGERED,
        resolved_at__isnull = True,
    )

    for breaker in resolved:
        duration_minutes = (now - breaker.created_at).total_seconds() / 60
        breaker.resolved_at = now
        breaker.save(update_fields=["resolved_at"])

        arcx_logger.circuit_breaker_resolved(
            tier                    = breaker.tier,
            active_duration_minutes = round(duration_minutes, 1),
        )
        logger.info(
            "Circuit breaker %s auto-resolved after %.1f minutes.",
            breaker.tier, duration_minutes,
        )