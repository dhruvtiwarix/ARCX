"""
ARCX Phase 12 — backfill_nav Management Command
-------------------------------------------------
Replaces the fake GBM-generated NAV history with REAL historical market data
fetched directly from yfinance.

Usage:
    python manage.py backfill_nav              # Last 60 trading days
    python manage.py backfill_nav --days 90   # Last 90 trading days
    python manage.py backfill_nav --overwrite  # Delete existing and redo

How it works:
    1. Fetches historical OHLCV for SPY, TLT, GLD, USD/INR from yfinance
    2. For each trading day, creates the same ValuationEngine calculation
       as the live oracle
    3. Writes VaultSnapshot + NAVHistory records
    4. Idempotent by default — skips days that already have a VaultSnapshot

This gives us a REAL 60-day price history for the ARCX dashboard chart.
"""

import sys
import logging
from datetime import date, timedelta
from decimal import Decimal
from dataclasses import dataclass
from typing import List

import yfinance as yf
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError

from domain.oracle import MarketPrices
from domain.valuation import ValuationEngine
from domain.dividend import DividendAccrualEngine
from domain.nav_report import NAVReportGenerator
from domain.rebalancer import DriftRebalancer
from arcx_core.models import VaultSnapshot, NAVHistory

logger = logging.getLogger("arcx.management.backfill_nav")


# ── Asset tickers ──────────────────────────────────────────────────────────────
TICKERS = {
    "spy":    "SPY",       # US Large Cap stocks proxy
    "tlt":    "TLT",       # US Long-Term bonds proxy
    "gld":    "GLD",       # Gold ETF proxy
    "usd_inr": "USDINR=X", # USD/INR forex
}

# ── Genesis constants (same as ValuationEngine.from_genesis) ──────────────────
GENESIS_ARCX_SUPPLY     = 1000.0
GENESIS_VAULT_VALUE_USD = 1200.0   # $1,200 = 1000 ARCX × $1.20 NAV


class Command(BaseCommand):
    help = "Backfill real historical NAV data from yfinance (Phase 12)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=60,
            help="Number of calendar days to backfill (default: 60)"
        )
        parser.add_argument(
            "--overwrite", action="store_true",
            help="Delete existing VaultSnapshot/NAVHistory before backfilling"
        )

    def handle(self, *args, **options):
        days      = options["days"]
        overwrite = options["overwrite"]

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n[*] ARCX Phase 12 -- Real NAV Backfill ({days} days)\n"
        ))

        # -- Step 1: Optional wipe -----------------------------------------------
        if overwrite:
            self.stdout.write("  [!] --overwrite: deleting all existing NAV history...")
            NAVHistory.objects.all().delete()
            VaultSnapshot.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Done.\n"))

        # -- Step 2: Fetch historical data from yfinance --------------------------
        end_date   = date.today()
        start_date = end_date - timedelta(days=days + 10)  # +10 buffer for weekends

        self.stdout.write(f"  [~] Fetching from yfinance: {start_date} -> {end_date}")

        try:
            raw = yf.download(
                tickers   = list(TICKERS.values()),
                start     = str(start_date),
                end       = str(end_date),
                progress  = False,
                auto_adjust = True,
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"  [X] yfinance download failed: {e}"))
            sys.exit(1)

        if raw.empty:
            self.stderr.write(self.style.ERROR("  [X] No data returned from yfinance."))
            sys.exit(1)

        # Extract closing prices for each ticker
        try:
            close = raw["Close"]
        except KeyError:
            close = raw

        self.stdout.write(f"  [+] Got {len(close)} rows of market data.\n")

        # -- Step 3: Process each trading day -------------------------------------
        created_count = 0
        skipped_count = 0
        error_count   = 0

        # We'll carry forward vault state day by day
        # But we must use the TRUE live supply from Wallets so we don't corrupt the live DB!
        from arcx_core.models import Wallet
        from django.db.models import Sum
        true_supply = Wallet.objects.aggregate(Sum('arcx_balance'))['arcx_balance__sum']
        
        current_supply    = float(true_supply) if true_supply else GENESIS_ARCX_SUPPLY
        # Anchor the vault value to the supply (approx $1.20 per token starting NAV)
        current_vault_usd = current_supply * 1.20
        self.stdout.write(f"  [-] Starting backfill simulation anchored to true supply: {current_supply}")

        # Iterate over dates with valid data
        sorted_dates = sorted(close.index)

        for dt_index in sorted_dates:
            nav_date = dt_index.date() if hasattr(dt_index, "date") else dt_index

            if nav_date >= date.today():
                continue

            if VaultSnapshot.objects.filter(snapshot_date=nav_date).exists():
                skipped_count += 1
                continue

            try:
                spy_row    = close.get(TICKERS["spy"])
                tlt_row    = close.get(TICKERS["tlt"])
                gld_row    = close.get(TICKERS["gld"])
                usd_inr_row = close.get(TICKERS["usd_inr"])

                spy_price    = float(spy_row.loc[dt_index])
                tlt_price    = float(tlt_row.loc[dt_index])
                gld_price    = float(gld_row.loc[dt_index])
                usd_inr_rate = float(usd_inr_row.loc[dt_index])

                if any(pd.isna([spy_price, tlt_price, gld_price, usd_inr_rate])):
                    self.stdout.write(f"  [?] {nav_date}: NaN prices, skipping.")
                    skipped_count += 1
                    continue

                if usd_inr_rate < 50 or usd_inr_rate > 110:
                    usd_inr_rate = 83.5

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  [?] {nav_date}: price extraction error ({e}), skipping."))
                skipped_count += 1
                continue

            from datetime import datetime as dt
            prices = MarketPrices(
                spy          = spy_price,
                tlt          = tlt_price,
                gld          = gld_price,
                usd_inr      = usd_inr_rate,
                sources_used = ["yfinance (backfill)"],
                fetched_at   = dt.combine(nav_date, dt.min.time()),
            )

            # Phase 6: backfill uses cash-only engine (no actual DB holdings exist for history)
            # The vault value is carried forward as cash_balance_usd between days.
            engine = ValuationEngine(
                arcx_supply      = current_supply,
                cash_balance_usd = current_vault_usd,
            )
            state = engine.calculate_nav([], prices)   # empty holdings = pure cash simulation

            dividend_engine = DividendAccrualEngine()
            accrual = dividend_engine.accrue_daily_yield(
                vault_value_usd = current_vault_usd,
                arcx_supply     = current_supply,
                prices          = prices,
            )

            # Phase 6: rebalancer now takes holdings dict + live_prices
            rebalancer   = DriftRebalancer()
            rebal_report = rebalancer.analyze(
                vault_value_usd  = float(state.total_vault_value_usd),
                holdings         = {},   # no actual holdings in backfill simulation
                cash_balance_usd = float(state.cash_balance_usd),
                live_prices      = {"SPY": spy_price, "TLT": tlt_price, "GLD": gld_price},
            )
            reporter    = NAVReportGenerator()
            report_data = reporter.generate(prices, state, accrual, rebal_report)
            report_hash = report_data["signature"]["hash"]

            try:
                with transaction.atomic():
                    snapshot = VaultSnapshot.objects.create(
                        snapshot_date   = nav_date,
                        total_value_usd = Decimal(str(round(float(state.total_vault_value_usd), 4))),
                        stock_value_usd = Decimal(str(round(float(state.stock_value_usd), 4))),
                        bond_value_usd  = Decimal(str(round(float(state.bond_value_usd), 4))),
                        gold_value_usd  = Decimal(str(round(float(state.gold_value_usd), 4))),
                        cash_value_usd  = Decimal(str(round(float(state.cash_value_usd), 4))),
                        arcx_supply     = Decimal(str(round(current_supply, 18))),
                        spy_twap        = Decimal(str(round(spy_price, 4))),
                        tlt_twap        = Decimal(str(round(tlt_price, 4))),
                        gld_twap        = Decimal(str(round(gld_price, 4))),
                        usd_inr_rate    = Decimal(str(round(usd_inr_rate, 4))),
                    )

                    NAVHistory.objects.create(
                        snapshot             = snapshot,
                        nav_date             = nav_date,
                        nav_usd              = Decimal(str(round(state.nav_usd, 8))),
                        nav_inr              = Decimal(str(round(state.nav_inr, 4))),
                        dividend_accrued_inr = Decimal(str(round(accrual.total_yield_inr, 8))),
                        report_hash          = report_hash,
                    )

                    current_vault_usd = float(state.total_vault_value_usd) + accrual.total_yield_usd

                created_count += 1
                self.stdout.write(
                    f"  [+] {nav_date}  SPY=${spy_price:.2f}  GLD=${gld_price:.2f}"
                    f"  ARCX=INR{state.nav_inr:.4f}  (${state.nav_usd:.6f})"
                )

            except IntegrityError:
                skipped_count += 1
                self.stdout.write(f"  [~] {nav_date}: already exists (race). Skipping.")
            except Exception as e:
                error_count += 1
                self.stderr.write(self.style.ERROR(f"  [X] {nav_date}: DB write failed -- {e}"))

        # -- Step 4: Summary -------------------------------------------------------
        self.stdout.write("\n" + "-" * 60)
        self.stdout.write(self.style.SUCCESS(
            f"  Backfill complete!\n"
            f"     Created:  {created_count} records\n"
            f"     Skipped:  {skipped_count} (already existed or no data)\n"
            f"     Errors:   {error_count}\n"
        ))

        total = NAVHistory.objects.count()
        latest = NAVHistory.objects.order_by("-nav_date").first()
        if latest:
            self.stdout.write(
                f"  Total NAV history records: {total}\n"
                f"  Latest NAV: {latest.nav_date}  INR{latest.nav_inr}  (${latest.nav_usd})\n"
            )
