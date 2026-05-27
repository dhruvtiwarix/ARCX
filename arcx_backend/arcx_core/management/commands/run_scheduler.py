"""
ARCX Phase 12 — run_scheduler Management Command
--------------------------------------------------
Runs the APScheduler in-process scheduler as an alternative to Celery Beat.
No Redis required — runs inside the same Django process.

Usage:
    python manage.py run_scheduler

This registers the same 4 jobs as Celery Beat:
    - 15:30 IST  → take_vault_snapshot
    - 15:45 IST  → run_rebalancing_check  
    - 16:00 IST  → publish_daily_nav
    - 00:01 IST  → accrue_daily_dividends

Keep this running in a separate terminal alongside manage.py runserver.

Job execution history is stored in the `django_apscheduler_djangojob` table.
"""

import logging
import signal
import sys
import time

from django.core.management.base import BaseCommand

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution

logger = logging.getLogger("arcx.scheduler")


# ── The actual job functions (thin wrappers that call the same logic as Celery) ─

def job_take_vault_snapshot():
    """Daily 15:30 IST — Capture market close prices, write VaultSnapshot."""
    import django
    from datetime import date
    from decimal import Decimal
    from django.db import transaction, IntegrityError
    from domain.oracle import MultiSourceOracle, OracleFailureException
    from domain.valuation import ValuationEngine
    from arcx_core.models import VaultSnapshot, VaultAssetHolding
    from arcx_core.logger import arcx_logger

    log = logging.getLogger("arcx.scheduler.snapshot")
    today = date.today()
    log.info("[Scheduler] take_vault_snapshot: %s", today)

    if VaultSnapshot.objects.filter(snapshot_date=today).exists():
        log.info("[Scheduler] Snapshot for %s already exists. Skipping.", today)
        return

    try:
        oracle = MultiSourceOracle()
        prices = oracle.fetch_prices()
    except OracleFailureException as e:
        log.error("[Scheduler] Oracle failure: %s", e)
        return

    try:
        prev = VaultSnapshot.objects.exclude(snapshot_date=today).latest("snapshot_date")
        # Phase 6: load actual share quantities from the holdings ledger
        holdings = list(VaultAssetHolding.objects.all())
        engine = ValuationEngine(
            arcx_supply      = float(prev.arcx_supply),
            cash_balance_usd = float(prev.cash_value_usd),
        )
    except VaultSnapshot.DoesNotExist:
        holdings = []
        engine = ValuationEngine.from_genesis(prices)

    state = engine.calculate_nav(holdings, prices)

    try:
        VaultSnapshot.objects.create(
            snapshot_date   = today,
            total_value_usd = Decimal(str(round(state.total_vault_value_usd, 4))),
            stock_value_usd = Decimal(str(round(state.stock_value_usd, 4))),
            bond_value_usd  = Decimal(str(round(state.bond_value_usd, 4))),
            gold_value_usd  = Decimal(str(round(state.gold_value_usd, 4))),
            cash_value_usd  = Decimal(str(round(state.cash_value_usd, 4))),
            arcx_supply     = Decimal(str(round(engine.arcx_supply, 18))),
            spy_twap        = Decimal(str(round(prices.spy, 4))),
            tlt_twap        = Decimal(str(round(prices.tlt, 4))),
            gld_twap        = Decimal(str(round(prices.gld, 4))),
            usd_inr_rate    = Decimal(str(round(prices.usd_inr, 4))),
        )
        log.info("[Scheduler] ✅ VaultSnapshot created: date=%s nav_inr=%.4f", today, state.nav_inr)
        arcx_logger.info(f"[APScheduler] VaultSnapshot written for {today}: NAV ₹{state.nav_inr:.4f}")
    except IntegrityError:
        log.warning("[Scheduler] VaultSnapshot for %s already exists (concurrent). Skipping.", today)


def job_publish_daily_nav():
    """Daily 16:00 IST — Write NAVHistory, update price chart."""
    import django
    from datetime import date
    from decimal import Decimal
    from django.db import IntegrityError
    from domain.oracle import MultiSourceOracle, OracleFailureException
    from domain.valuation import ValuationEngine
    from domain.dividend import DividendAccrualEngine
    from domain.rebalancer import DriftRebalancer
    from domain.nav_report import NAVReportGenerator
    from arcx_core.models import VaultSnapshot, NAVHistory, VaultAssetHolding
    from arcx_core.logger import arcx_logger

    log = logging.getLogger("arcx.scheduler.nav")
    today = date.today()
    log.info("[Scheduler] publish_daily_nav: %s", today)

    if NAVHistory.objects.filter(nav_date=today).exists():
        log.info("[Scheduler] NAV for %s already published. Skipping.", today)
        return

    try:
        snapshot = VaultSnapshot.objects.get(snapshot_date=today)
    except VaultSnapshot.DoesNotExist:
        log.error("[Scheduler] No VaultSnapshot for %s. Snapshot task may have failed.", today)
        return

    try:
        oracle  = MultiSourceOracle()
        prices  = oracle.fetch_prices()
    except OracleFailureException as e:
        log.error("[Scheduler] Oracle failure on NAV publish: %s", e)
        return

    # Phase 6: load actual holdings for Mark-to-Market valuation
    holdings = list(VaultAssetHolding.objects.all())
    engine   = ValuationEngine(
        arcx_supply      = float(snapshot.arcx_supply),
        cash_balance_usd = float(snapshot.cash_value_usd),
    )
    state = engine.calculate_nav(holdings, prices)

    accrual_engine = DividendAccrualEngine()
    accrual = accrual_engine.accrue_daily_yield(
        vault_value_usd = float(snapshot.total_value_usd),
        arcx_supply     = float(snapshot.arcx_supply),
        prices          = prices,
    )

    # Phase 6: build holdings dict for rebalancer
    live_prices_dict = {"SPY": float(prices.spy), "TLT": float(prices.tlt), "GLD": float(prices.gld)}
    holdings_dict = {}
    for h in holdings:
        qty = float(h.total_quantity)
        holdings_dict[h.asset_ticker] = {
            "value": qty * live_prices_dict.get(h.asset_ticker, 0),
            "qty":   qty,
        }

    rebalancer   = DriftRebalancer()
    rebal_report = rebalancer.analyze(
        vault_value_usd  = float(state.total_vault_value_usd),
        holdings         = holdings_dict,
        cash_balance_usd = float(state.cash_balance_usd),
        live_prices      = live_prices_dict,
    )

    reporter    = NAVReportGenerator()
    report_data = reporter.generate(prices, state, accrual, rebal_report)
    report_hash = report_data["signature"]["hash"]

    try:
        NAVHistory.objects.create(
            snapshot             = snapshot,
            nav_date             = today,
            nav_usd              = Decimal(str(round(state.nav_usd, 8))),
            nav_inr              = Decimal(str(round(state.nav_inr, 4))),
            dividend_accrued_inr = Decimal(str(accrual.total_yield_inr)),
            report_hash          = report_hash,
        )
        log.info("[Scheduler] ✅ NAV published: date=%s nav_inr=%.4f", today, state.nav_inr)
        arcx_logger.nav_published(
            nav_date=str(today),
            nav_inr=float(state.nav_inr),
            report_hash=report_hash,
        )
    except IntegrityError:
        log.warning("[Scheduler] NAVHistory for %s already exists (concurrent). Skipping.", today)


def job_accrue_dividends():
    """Daily 00:01 IST — Compound overnight yield."""
    import django
    from datetime import date, timedelta
    from decimal import Decimal
    from domain.oracle import MultiSourceOracle, OracleFailureException
    from domain.dividend import DividendAccrualEngine
    from arcx_core.models import VaultSnapshot

    log = logging.getLogger("arcx.scheduler.dividend")
    yesterday = date.today() - timedelta(days=1)
    log.info("[Scheduler] accrue_daily_dividends for: %s", yesterday)

    try:
        snapshot = VaultSnapshot.objects.get(snapshot_date=yesterday)
    except VaultSnapshot.DoesNotExist:
        log.warning("[Scheduler] No snapshot for %s. Skipping dividend.", yesterday)
        return

    try:
        oracle  = MultiSourceOracle()
        prices  = oracle.fetch_prices()
    except OracleFailureException as e:
        log.error("[Scheduler] Oracle failure on dividend accrual: %s", e)
        return

    accrual_engine = DividendAccrualEngine()
    accrual = accrual_engine.accrue_daily_yield(
        vault_value_usd=float(snapshot.total_value_usd),
        arcx_supply=float(snapshot.arcx_supply),
        prices=prices,
    )

    from django.db import transaction
    with transaction.atomic():
        ratio = accrual.total_yield_usd / float(snapshot.total_value_usd)
        snapshot.stock_value_usd += snapshot.stock_value_usd * Decimal(str(ratio))
        snapshot.bond_value_usd  += snapshot.bond_value_usd * Decimal(str(ratio))
        snapshot.gold_value_usd  += snapshot.gold_value_usd * Decimal(str(ratio))
        snapshot.cash_value_usd  += snapshot.cash_value_usd * Decimal(str(ratio))
        snapshot.total_value_usd += Decimal(str(accrual.total_yield_usd))
        snapshot.save(update_fields=[
            "total_value_usd", "stock_value_usd",
            "bond_value_usd", "gold_value_usd", "cash_value_usd",
        ])

    log.info(
        "[Scheduler] ✅ Dividend accrued: date=%s yield_inr=%.8f per_arcx_inr=%.8f",
        yesterday, accrual.total_yield_inr, accrual.yield_per_arcx_inr
    )


# ── Management Command ─────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Run the APScheduler in-process scheduler (Phase 12 — no Redis needed)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n🕐 ARCX Phase 12 — In-Process Scheduler Starting...\n"
        ))

        scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # ── Register jobs (IST times) ─────────────────────────────────────────

        # 15:30 IST — Take VaultSnapshot after NSE/BSE market close
        scheduler.add_job(
            job_take_vault_snapshot,
            trigger     = CronTrigger(hour=15, minute=30, timezone="Asia/Kolkata"),
            id          = "take_vault_snapshot",
            name        = "EOD Vault Snapshot (15:30 IST)",
            replace_existing = True,
            max_instances    = 1,
            misfire_grace_time = 600,
        )

        # 15:45 IST — Rebalancing check
        scheduler.add_job(
            lambda: __import__("arcx_core.tasks.eod_tasks", fromlist=["run_rebalancing_check"]).run_rebalancing_check(),
            trigger     = CronTrigger(hour=15, minute=45, timezone="Asia/Kolkata"),
            id          = "run_rebalancing_check",
            name        = "Rebalancing Check (15:45 IST)",
            replace_existing = True,
            max_instances    = 1,
        )

        # 16:00 IST — Publish official daily NAV
        scheduler.add_job(
            job_publish_daily_nav,
            trigger     = CronTrigger(hour=16, minute=0, timezone="Asia/Kolkata"),
            id          = "publish_daily_nav",
            name        = "Publish Daily NAV (16:00 IST)",
            replace_existing = True,
            max_instances    = 1,
            misfire_grace_time = 600,
        )

        # 00:01 IST — Midnight dividend accrual
        scheduler.add_job(
            job_accrue_dividends,
            trigger     = CronTrigger(hour=0, minute=1, timezone="Asia/Kolkata"),
            id          = "accrue_daily_dividends",
            name        = "Midnight Dividend Accrual (00:01 IST)",
            replace_existing = True,
            max_instances    = 1,
        )

        scheduler.start()

        self.stdout.write(self.style.SUCCESS(
            "  ✅ Scheduler running! Registered jobs:\n"
            "     📸 15:30 IST → take_vault_snapshot\n"
            "     ⚖️  15:45 IST → run_rebalancing_check\n"
            "     📊 16:00 IST → publish_daily_nav\n"
            "     💰 00:01 IST → accrue_daily_dividends\n\n"
            "  Press Ctrl+C to stop.\n"
        ))

        # ── Graceful shutdown ─────────────────────────────────────────────────
        def _shutdown(signum, frame):
            self.stdout.write("\n  ⏹️  Shutting down scheduler...")
            scheduler.shutdown()
            self.stdout.write(self.style.SUCCESS("  ✓ Scheduler stopped cleanly."))
            sys.exit(0)

        signal.signal(signal.SIGINT,  _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        # Keep alive
        try:
            while True:
                time.sleep(30)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
