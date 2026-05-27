"""
ARCX End-of-Day Celery Tasks — arcx_core/tasks/eod_tasks.py
--------------------------------------------------------------
These four tasks run automatically every day via Celery Beat.
Together they make ARCX autonomous — it runs itself like a real fund.

DAILY TIMELINE (all IST):
  15:30  take_vault_snapshot()    → Capture closing prices, write VaultSnapshot
  15:45  run_rebalancing_check()  → Check drift, log trades needed
  00:01  accrue_daily_dividends() → Add overnight yield to vault
  16:00  publish_daily_nav()      → Write NAVHistory, update price chart

WHY THIS ORDER?
  Snapshot first — you need today's closing prices before you can do anything else.
  Rebalancing second — needs the snapshot to know current weights.
  Dividends at midnight — accrues on the EOD state, not intra-day noise.
  NAV last — the "official" number after all processing is done.

ERROR HANDLING:
  Every task uses self.retry() with exponential-ish backoff.
  If Oracle is down at 15:30, the task retries at 15:31, 15:32, 15:33.
  If all retries fail, arcx_logger.error() fires → you get an alert.
  The task does NOT crash Django — it fails gracefully and logs everything.

IDEMPOTENCY:
  Every task checks "did I already run today?" before doing work.
  VaultSnapshot has UNIQUE on snapshot_date.
  If the task runs twice (e.g., worker restart), the second run is a no-op.
  This is called task idempotency — critical for reliable automation.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from celery import shared_task
from django.db import transaction, IntegrityError
from django.utils import timezone

from domain.oracle import MultiSourceOracle, OracleFailureException
from domain.valuation import ValuationEngine
from domain.dividend import DividendAccrualEngine
from domain.rebalancer import DriftRebalancer
from domain.nav_report import NAVReportGenerator
from arcx_core.services.pseudo_broker import PseudoBrokerService
from arcx_core.models import VaultSnapshot, NAVHistory, CircuitBreakerLog, VaultAssetHolding
from arcx_core.logger import arcx_logger

logger = logging.getLogger("arcx.tasks.eod")


# ── Task 1: Vault Snapshot ────────────────────────────────────────────────────

@shared_task(
    bind=True,
    name="arcx_core.tasks.eod_tasks.take_vault_snapshot",
    max_retries=3,
    default_retry_delay=60,
)
def take_vault_snapshot(self):
    """
    Runs at 15:30 IST (market close).
    Fetches live TWAP prices and writes a VaultSnapshot for today.

    bind=True gives us access to `self` so we can call self.retry().
    max_retries=3 means: try once, then retry up to 3 more times.
    default_retry_delay=60: wait 60 seconds between retries.

    If it fails all 4 attempts, the exception propagates and Celery
    marks the task as FAILURE. The arcx logger captures this.
    """
    today = date.today()
    logger.info("EOD task started: take_vault_snapshot date=%s", today)

    # Idempotency check — if snapshot already exists for today, skip
    if VaultSnapshot.objects.filter(snapshot_date=today).exists():
        logger.info("Snapshot for %s already exists. Skipping.", today)
        return {"status": "skipped", "reason": "already_exists", "date": str(today)}

    try:
        oracle = MultiSourceOracle()
        prices = oracle.fetch_prices()
    except OracleFailureException as exc:
        logger.error("Oracle failure in take_vault_snapshot: %s", exc)
        arcx_logger.oracle_failure(str(exc), ["Yahoo Finance", "Alpha Vantage", "Twelve Data"])
        # Retry — Oracle might recover in 60 seconds
        raise self.retry(exc=exc)

    # Get current vault state from the most recent previous snapshot
    # (or genesis if this is the very first snapshot)
    try:
        prev_snapshot = VaultSnapshot.objects.exclude(
            snapshot_date=today
        ).latest("snapshot_date")
        # Phase 6: Load actual share holdings from the ledger
        holdings = list(VaultAssetHolding.objects.all())
        engine = ValuationEngine(
            arcx_supply      = float(prev_snapshot.arcx_supply),
            cash_balance_usd = float(prev_snapshot.cash_value_usd),
        )
    except VaultSnapshot.DoesNotExist:
        logger.warning("No previous snapshot found. Bootstrapping from genesis.")
        holdings = []   # Day 0: vault is pure cash, no shares yet
        engine = ValuationEngine.from_genesis(prices)

    state = engine.calculate_nav(holdings, prices)

    try:
        snapshot = VaultSnapshot.objects.create(
            snapshot_date   = today,
            total_value_usd = Decimal(str(round(float(state.total_vault_value_usd), 4))),
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
    except IntegrityError:
        # Race condition: another worker beat us. Not an error — just skip.
        logger.warning("IntegrityError on VaultSnapshot — concurrent task won. Skipping.")
        return {"status": "skipped", "reason": "concurrent_write", "date": str(today)}

    logger.info(
        "VaultSnapshot created: date=%s total_usd=%s nav_inr=%s",
        today, state.total_vault_value_usd, state.nav_inr,
    )
    return {
        "status":      "ok",
        "date":        str(today),
        "snapshot_id": str(snapshot.id),
        "nav_inr":     round(state.nav_inr, 4),
    }


# ── Task 2: Dividend Accrual ─────────────────────────────────────────────────

@shared_task(
    bind=True,
    name="arcx_core.tasks.eod_tasks.accrue_daily_dividends",
    max_retries=3,
    default_retry_delay=120,
)
def accrue_daily_dividends(self):
    """
    Runs at 00:01 IST (midnight). Adds overnight yield to the vault.

    How it works:
      1. Load today's VaultSnapshot (written at EOD)
      2. Calculate daily yield across all 4 asset classes
      3. Add yield to vault's total_value_usd
      4. The next NAV calculation automatically reflects the higher vault value
      5. Every ARCX token is now worth slightly more. Silent compounding.

    This is how every money market fund works.
    You don't receive dividends into your bank account —
    the NAV of your units goes up overnight instead.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    logger.info("Midnight task started: accrue_daily_dividends for=%s", yesterday)

    try:
        # Use yesterday's snapshot (the EOD snapshot from hours ago)
        snapshot = VaultSnapshot.objects.get(snapshot_date=yesterday)
    except VaultSnapshot.DoesNotExist:
        logger.warning(
            "No VaultSnapshot for %s found during dividend accrual. "
            "EOD task may have failed. Skipping dividend.", yesterday
        )
        return {"status": "skipped", "reason": "no_snapshot", "date": str(yesterday)}

    try:
        oracle = MultiSourceOracle()
        prices = oracle.fetch_prices()
    except OracleFailureException as exc:
        raise self.retry(exc=exc)

    accrual_engine = DividendAccrualEngine()
    accrual = accrual_engine.accrue_daily_yield(
        vault_value_usd = float(snapshot.total_value_usd),
        arcx_supply     = float(snapshot.arcx_supply),
        prices          = prices,
    )

    # Add the yield to the vault
    # We update the snapshot's total_value_usd so tomorrow's NAV reflects it
    with transaction.atomic():
        ratio = accrual.total_yield_usd / float(snapshot.total_value_usd)
        snapshot.stock_value_usd += snapshot.stock_value_usd * Decimal(str(ratio))
        snapshot.bond_value_usd  += snapshot.bond_value_usd * Decimal(str(ratio))
        snapshot.gold_value_usd  += snapshot.gold_value_usd * Decimal(str(ratio))
        snapshot.cash_value_usd  += snapshot.cash_value_usd * Decimal(str(ratio))
        snapshot.total_value_usd += Decimal(str(accrual.total_yield_usd))
        snapshot.save(update_fields=[
            "total_value_usd", "stock_value_usd",
            "bond_value_usd",  "gold_value_usd", "cash_value_usd",
        ])

    logger.info(
        "Dividend accrued: date=%s total_yield_usd=%s per_arcx_inr=%s",
        yesterday, accrual.total_yield_usd, accrual.yield_per_arcx_inr,
    )
    return {
        "status":              "ok",
        "date":                str(yesterday),
        "total_yield_usd":     accrual.total_yield_usd,
        "total_yield_inr":     accrual.total_yield_inr,
        "yield_per_arcx_inr":  accrual.yield_per_arcx_inr,
    }


# ── Task 3: Rebalancing Check ─────────────────────────────────────────────────

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


# ── Task 4: Publish Daily NAV ─────────────────────────────────────────────────

@shared_task(
    bind=True,
    name="arcx_core.tasks.eod_tasks.publish_daily_nav",
    max_retries=3,
    default_retry_delay=60,
)
def publish_daily_nav(self):
    """
    Runs at 16:00 IST. The official daily NAV publication.
    Creates a NAVHistory record that users see in their price chart.
    Generates the SHA256-signed JSON report (from Phase 1's nav_report.py).

    Idempotent: if NAVHistory for today already exists, skip.
    """
    today = date.today()
    logger.info("EOD task started: publish_daily_nav date=%s", today)

    if NAVHistory.objects.filter(nav_date=today).exists():
        logger.info("NAV for %s already published. Skipping.", today)
        return {"status": "skipped", "reason": "already_published", "date": str(today)}

    try:
        snapshot = VaultSnapshot.objects.get(snapshot_date=today)
    except VaultSnapshot.DoesNotExist:
        logger.error("Cannot publish NAV: no snapshot for %s", today)
        raise self.retry(exc=RuntimeError(f"No snapshot for {today}"))

    try:
        oracle = MultiSourceOracle()
        prices = oracle.fetch_prices()
    except OracleFailureException as exc:
        raise self.retry(exc=exc)

    # Phase 6: Load actual holdings from the ledger
    holdings = list(VaultAssetHolding.objects.all())
    engine = ValuationEngine(
        arcx_supply      = float(snapshot.arcx_supply),
        cash_balance_usd = float(snapshot.cash_value_usd),
    )
    state = engine.calculate_nav(holdings, prices)

    # Calculate today's dividend for the report
    accrual_engine = DividendAccrualEngine()
    accrual = accrual_engine.accrue_daily_yield(
        vault_value_usd = float(snapshot.total_value_usd),
        arcx_supply     = float(snapshot.arcx_supply),
        prices          = prices,
    )

    # Generate and save the signed JSON report (Phase 1 nav_report.py)
    # Phase 6: Build holdings dict for the rebalancer from actual DB holdings
    holdings_dict  = {}
    live_prices_dict = {
        "SPY": float(prices.spy),
        "TLT": float(prices.tlt),
        "GLD": float(prices.gld),
    }
    for h in holdings:
        qty = float(h.total_quantity)
        price = live_prices_dict.get(h.asset_ticker, 0)
        holdings_dict[h.asset_ticker] = {
            "value": qty * price,
            "qty":   qty,
        }

    rebalancer = DriftRebalancer()
    rebalance  = rebalancer.analyze(
        vault_value_usd  = float(state.total_vault_value_usd),
        holdings         = holdings_dict,
        cash_balance_usd = float(state.cash_balance_usd),
        live_prices      = live_prices_dict,
    )

    reporter    = NAVReportGenerator()
    report_data = reporter.generate(prices, state, accrual, rebalance)
    report_hash = report_data["signature"]["hash"]

    try:
        nav_record = NAVHistory.objects.create(
            snapshot             = snapshot,
            nav_date             = today,
            nav_usd              = Decimal(str(round(state.nav_usd, 8))),
            nav_inr              = Decimal(str(round(state.nav_inr, 4))),
            dividend_accrued_inr = Decimal(str(accrual.total_yield_inr)),
            report_hash          = report_hash,
        )
    except IntegrityError:
        logger.warning("NAVHistory for %s already exists (concurrent write). Skipping.", today)
        return {"status": "skipped", "reason": "concurrent_write"}

    arcx_logger.nav_published(
        nav_date    = str(today),
        nav_inr     = float(state.nav_inr),
        report_hash = report_hash,
    )

    logger.info(
        "NAV published: date=%s nav_inr=%s hash=%s...",
        today, state.nav_inr, report_hash[:16],
    )
    return {
        "status":      "ok",
        "date":        str(today),
        "nav_inr":     round(state.nav_inr, 4),
        "nav_usd":     round(state.nav_usd, 8),
        "report_hash": report_hash,
        "nav_id":      str(nav_record.id),
    }