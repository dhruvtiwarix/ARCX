"""
ARCX Celery Application — arcx_backend/arcx_backend/celery.py
---------------------------------------------------------------
Celery is a task queue. It lets Django schedule and run background jobs
without blocking the HTTP request-response cycle.

WHY CELERY FOR ARCX?
  Some jobs cannot happen during an API request:
    - Publishing daily NAV: takes 5+ seconds (Oracle fetch + DB write)
    - Checking circuit breaker: must run every 60 seconds, 24/7
    - Accruing dividends: must run at midnight every night precisely

  If you tried to run these inside a view:
    - User waits 5 seconds for "deposit" to respond (NAV fetch blocks)
    - Circuit breaker only fires when someone makes a request (wrong)
    - Dividends never accrue on days with no API traffic (wrong)

  With Celery + Celery Beat (the scheduler):
    - Jobs run on their own schedule, independent of API traffic
    - API responses stay under 200ms (Oracle fetch is async / pre-cached)
    - System is autonomous — runs itself even at 3 AM with zero users

ARCHITECTURE:
  Django App → publishes task to Redis (the broker)
  Celery Worker → picks up task from Redis → executes it → writes result to DB
  Celery Beat → the scheduler, fires tasks on a cron-like schedule

SETUP:
  1. Install Redis: brew install redis / apt install redis
  2. pip install celery redis
  3. Start worker:   celery -A arcx_backend worker -l INFO
  4. Start beat:     celery -A arcx_backend beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
  5. Or both at once (dev only): celery -A arcx_backend worker --beat -l INFO

The -A arcx_backend flag tells Celery where to find this file.
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "arcx_backend.settings")

app = Celery("arcx_backend")

# Read config from Django settings, namespaced under CELERY_
# e.g. settings.CELERY_BROKER_URL, settings.CELERY_RESULT_BACKEND
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in every installed app's tasks/ directory
# Finds: arcx_core/tasks/eod_tasks.py, arcx_core/tasks/monitoring_tasks.py, etc.
app.autodiscover_tasks()


# ── Celery Beat Schedule ──────────────────────────────────────────────────────
# This is the "cron" for ARCX. All scheduled jobs defined here.
# Times are in UTC. Add USE_TZ = True and TIME_ZONE = "UTC" in settings.py.

app.conf.beat_schedule = {

    # ── Market Monitoring: every 2 minutes ───────────────────────────────
    # Checks if circuit breaker should fire.
    # 2 minutes is fast enough to catch crashes, slow enough to not hammer Oracle.
    "circuit-breaker-check": {
        "task":     "arcx_core.tasks.monitoring_tasks.check_circuit_breaker",
        "schedule": 120,   # seconds
    },

    # ── End of Day: 3:30 PM IST = 10:00 AM UTC ───────────────────────────
    # Why 3:30 PM IST? NSE/BSE close at 3:30 PM IST.
    # We snapshot after markets close so the NAV reflects final closing prices,
    # not mid-session volatility. This is how every mutual fund in India works.
    "eod-vault-snapshot": {
        "task":     "arcx_core.tasks.eod_tasks.take_vault_snapshot",
        "schedule": crontab(hour=10, minute=0),   # 10:00 UTC = 15:30 IST
    },

    # ── EOD Rebalancing: 3:45 PM IST = 10:15 AM UTC ──────────────────────
    # Run 15 minutes after snapshot so the snapshot is committed to DB first.
    "eod-rebalancing-check": {
        "task":     "arcx_core.tasks.eod_tasks.run_rebalancing_check",
        "schedule": crontab(hour=10, minute=15),
    },

    # ── Midnight Dividend Accrual: 00:01 IST = 18:31 UTC (prev day) ──────
    # Runs just after midnight IST. Adds overnight yield to vault.
    # Users wake up to slightly more ARCX. The "dopamine hit."
    "midnight-dividend-accrual": {
        "task":     "arcx_core.tasks.eod_tasks.accrue_daily_dividends",
        "schedule": crontab(hour=18, minute=31),   # 18:31 UTC = 00:01 IST
    },

    # ── Daily NAV Publish: 4:00 PM IST = 10:30 AM UTC ────────────────────
    # Published 30 minutes after market close.
    # By this point: snapshot done, rebalancing assessed, prices settled.
    # This creates the NAVHistory record users see in their price chart.
    "publish-daily-nav": {
        "task":     "arcx_core.tasks.eod_tasks.publish_daily_nav",
        "schedule": crontab(hour=10, minute=30),
    },

}

app.conf.timezone = "UTC"