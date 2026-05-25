"""
Phase 9 — Simulation Seed Engine
==================================
Creates a fully populated test environment with:

  ✓ 5 realistic test users (Alice, Bob, Charlie, Diana, Eve)
  ✓ Each user: KYC approved, wallet created
  ✓ 30 days of VaultSnapshot + NAVHistory (with realistic price drift)
  ✓ Seeded transactions (deposits, transfers, dividends) spread across 30 days

Usage:
    python manage.py seed_simulation
    python manage.py seed_simulation --flush   (wipe & re-seed)

Design:
    We simulate a ₹100 genesis peg on Day -30 and let it drift realistically
    using Brownian motion (the same math used to model stock prices).
    This gives a chart that looks like a real fintech product — not a flat line.
"""

import uuid
import math
import random
import hashlib
import json
from datetime import date, timedelta, datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from arcx_core.models import (
    User, Wallet, Transaction, VaultSnapshot, NAVHistory, KYCRecord
)

DjangoUser = get_user_model()

# ── Simulation Parameters ────────────────────────────────────────────────────

DAYS          = 30
GENESIS_INR   = Decimal("100.0000")   # 1 ARCX = ₹100 on Day 0
GENESIS_USD   = Decimal("1.2000")     # 1 ARCX = $1.20 on Day 0
USD_INR       = Decimal("83.5000")    # Fixed rate for simulation
SUPPLY_START  = Decimal("1000.0")     # Starting ARCX supply (founder tokens)
VAULT_START   = Decimal("100000.0")   # ₹1,00,000 founder deposit → USD equivalent

# Brownian motion parameters (realistic fund-like drift)
DAILY_DRIFT   = 0.0008    # +0.08% daily expected return (~20% annual)
DAILY_VOL     = 0.0035    # 0.35% daily volatility (moderate, not crypto-crazy)

# ── Test Users ───────────────────────────────────────────────────────────────

TEST_USERS = [
    {"name": "Alice Sharma",   "email": "alice@arcxtest.com",   "password": "Test@12345"},
    {"name": "Bob Mehta",      "email": "bob@arcxtest.com",     "password": "Test@12345"},
    {"name": "Charlie Rao",    "email": "charlie@arcxtest.com", "password": "Test@12345"},
    {"name": "Diana Patel",    "email": "diana@arcxtest.com",   "password": "Test@12345"},
    {"name": "Eve Krishnan",   "email": "eve@arcxtest.com",     "password": "Test@12345"},
]


class Command(BaseCommand):
    help = "Phase 9: Seed 5 test users, 30 days of NAV history, and realistic transactions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all simulation data before seeding (clean re-seed).",
        )

    def handle(self, *args, **options):
        random.seed(42)   # Deterministic — same chart every time you seed

        if options["flush"]:
            self._flush()

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Phase 9: Simulation Seed Engine ===\n"))

        nav_series = self._generate_nav_series()
        self._seed_nav_history(nav_series)
        users_wallets = self._seed_users()
        self._seed_transactions(users_wallets, nav_series)

        self.stdout.write(self.style.SUCCESS("\n✓ Simulation seed complete!\n"))
        self.stdout.write("  Dashboard chart will now show 30 days of history.")
        self.stdout.write("  Login credentials:\n")
        for u in TEST_USERS:
            self.stdout.write(f"    {u['email']}  /  {u['password']}")
        self.stdout.write("")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1 — Generate NAV series using Geometric Brownian Motion
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_nav_series(self) -> list[dict]:
        """
        Generates DAYS days of synthetic NAV data using Geometric Brownian Motion.
        GBM is the industry-standard model for asset price simulation (Black-Scholes uses it).

        Formula:
          S(t+1) = S(t) * exp((mu - sigma²/2)*dt + sigma*sqrt(dt)*Z)
          where Z ~ N(0,1) (standard normal random variable)
        """
        self.stdout.write(self.style.MIGRATE_LABEL("  [1/3] Generating 30-day NAV series..."))

        today      = date.today()
        start_date = today - timedelta(days=DAYS - 1)

        nav_inr    = float(GENESIS_INR)
        vault_usd  = float(VAULT_START) / float(USD_INR)   # Convert ₹1L to USD
        supply     = float(SUPPLY_START)

        series = []
        for i in range(DAYS):
            day = start_date + timedelta(days=i)

            # Geometric Brownian Motion step
            z       = random.gauss(0, 1)
            dt      = 1.0
            log_ret = (DAILY_DRIFT - 0.5 * DAILY_VOL ** 2) * dt + DAILY_VOL * math.sqrt(dt) * z
            nav_inr = nav_inr * math.exp(log_ret)

            # Derive USD NAV from INR NAV using fixed USD/INR
            nav_usd = nav_inr / float(USD_INR)

            # Back-calculate vault_usd from NAV and supply
            vault_usd = nav_usd * supply

            # Simulate asset breakdown (40/30/20/10)
            stock_usd = vault_usd * 0.40
            bond_usd  = vault_usd * 0.30
            gold_usd  = vault_usd * 0.20
            cash_usd  = vault_usd * 0.10

            # Simulated realistic underlying asset prices
            spy = 530.0 + random.uniform(-15, 15) + i * 0.3
            tlt = 93.0  + random.uniform(-2, 2)
            gld = 185.0 + random.uniform(-3, 3) + i * 0.1

            series.append({
                "date":       day,
                "nav_inr":    round(nav_inr, 4),
                "nav_usd":    round(nav_usd, 8),
                "vault_usd":  round(vault_usd, 4),
                "supply":     round(supply, 18),
                "stock_usd":  round(stock_usd, 4),
                "bond_usd":   round(bond_usd, 4),
                "gold_usd":   round(gold_usd, 4),
                "cash_usd":   round(cash_usd, 4),
                "spy":        round(spy, 4),
                "tlt":        round(tlt, 4),
                "gld":        round(gld, 4),
                "usd_inr":    float(USD_INR),
            })

        self.stdout.write(
            f"    NAV range: ₹{min(s['nav_inr'] for s in series):.4f} → "
            f"₹{max(s['nav_inr'] for s in series):.4f}"
        )
        return series

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2 — Write VaultSnapshot + NAVHistory rows
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_nav_history(self, nav_series: list[dict]):
        self.stdout.write(self.style.MIGRATE_LABEL("  [2/3] Writing VaultSnapshot + NAVHistory rows..."))

        created_snapshots = 0
        created_nav       = 0

        for entry in nav_series:
            day = entry["date"]

            # Skip if already exists (idempotent)
            if VaultSnapshot.objects.filter(snapshot_date=day).exists():
                continue

            with transaction.atomic():
                # Build minimal report for hash (mirrors NAVReportGenerator)
                report_data = {
                    "date":     day.isoformat(),
                    "nav_inr":  entry["nav_inr"],
                    "nav_usd":  entry["nav_usd"],
                    "supply":   entry["supply"],
                    "vault_usd": entry["vault_usd"],
                }
                report_hash = hashlib.sha256(
                    json.dumps(report_data, sort_keys=True).encode()
                ).hexdigest()

                snapshot = VaultSnapshot.objects.create(
                    snapshot_date   = day,
                    total_value_usd = Decimal(str(entry["vault_usd"])),
                    stock_value_usd = Decimal(str(entry["stock_usd"])),
                    bond_value_usd  = Decimal(str(entry["bond_usd"])),
                    gold_value_usd  = Decimal(str(entry["gold_usd"])),
                    cash_value_usd  = Decimal(str(entry["cash_usd"])),
                    arcx_supply     = Decimal(str(entry["supply"])),
                    spy_twap        = Decimal(str(entry["spy"])),
                    tlt_twap        = Decimal(str(entry["tlt"])),
                    gld_twap        = Decimal(str(entry["gld"])),
                    usd_inr_rate    = Decimal(str(entry["usd_inr"])),
                )
                created_snapshots += 1

                NAVHistory.objects.create(
                    snapshot              = snapshot,
                    nav_date              = day,
                    nav_usd               = Decimal(str(entry["nav_usd"])),
                    nav_inr               = Decimal(str(entry["nav_inr"])),
                    dividend_accrued_inr  = Decimal("0.0000"),
                    report_hash           = report_hash,
                )
                created_nav += 1

        self.stdout.write(f"    Created {created_snapshots} VaultSnapshots, {created_nav} NAVHistory rows.")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3 — Create test users + wallets
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_users(self) -> list[tuple]:
        """Returns list of (arcx_user, wallet) tuples."""
        self.stdout.write(self.style.MIGRATE_LABEL("  [3/3] Creating test users & wallets..."))

        result = []
        for u in TEST_USERS:
            # Create Django auth user (for login)
            django_user, created = DjangoUser.objects.get_or_create(
                username=u["email"],
                defaults={"email": u["email"], "first_name": u["name"].split()[0]},
            )
            if created:
                django_user.set_password(u["password"])
                django_user.save()

            # Create ARCX domain user
            arcx_user, _ = User.objects.get_or_create(
                email=u["email"],
                defaults={
                    "full_name":  u["name"],
                    "kyc_status": User.KycStatus.APPROVED,
                    "is_active":  True,
                },
            )
            # Ensure KYC approved
            if arcx_user.kyc_status != User.KycStatus.APPROVED:
                arcx_user.kyc_status = User.KycStatus.APPROVED
                arcx_user.save(update_fields=["kyc_status", "updated_at"])

            # Create KYC record if missing
            if not KYCRecord.objects.filter(user=arcx_user, status=KYCRecord.Status.APPROVED).exists():
                KYCRecord.objects.create(
                    user          = arcx_user,
                    tier          = KYCRecord.Tier.TIER_2,
                    status        = KYCRecord.Status.APPROVED,
                    document_type = KYCRecord.DocumentType.PAN,
                    document_ref  = f"SEED_REF_{arcx_user.id.hex[:8].upper()}",
                    verified_at   = timezone.now() - timedelta(days=31),
                )

            # Create wallet if missing
            wallet, _ = Wallet.objects.get_or_create(user=arcx_user)

            result.append((arcx_user, wallet))
            self.stdout.write(f"    ✓ {u['name']} ({u['email']})")

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Step 4 — Seed realistic transactions
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_transactions(self, users_wallets: list[tuple], nav_series: list[dict]):
        """
        For each user, seeds:
          - An initial large deposit in the first week
          - 1-2 smaller deposits across the month
          - A peer transfer between users (mid-month)
          - Daily dividend accruals (every 3 days for simulation)
        """
        self.stdout.write(self.style.MIGRATE_LABEL("\n  Seeding transactions..."))

        # Deposit schedules per user (day_index, inr_amount)
        deposit_schedule = [
            [(0,  50_000), (10, 25_000), (22, 10_000)],   # Alice   — aggressive
            [(1,  30_000), (15, 15_000)],                  # Bob     — moderate
            [(2,  75_000), (20, 30_000)],                  # Charlie — high value
            [(3,  20_000), (12, 20_000), (25, 10_000)],   # Diana   — steady DCA
            [(5,  10_000), (18, 10_000)],                  # Eve     — small
        ]

        for idx, (arcx_user, wallet) in enumerate(users_wallets):
            total_arcx   = Decimal("0")
            total_cost   = Decimal("0")

            # ── Deposits ──────────────────────────────────────────────────
            for day_i, inr_amt in deposit_schedule[idx]:
                entry     = nav_series[day_i]
                nav_inr   = Decimal(str(entry["nav_inr"]))
                arcx_qty  = Decimal(str(inr_amt)) / nav_inr
                tx_time   = datetime.combine(entry["date"], datetime.min.time()) \
                            + timedelta(hours=random.randint(9, 17), minutes=random.randint(0, 59))
                tx_time   = timezone.make_aware(tx_time)

                Transaction.objects.get_or_create(
                    idempotency_key = uuid.uuid5(uuid.NAMESPACE_DNS, f"deposit-{arcx_user.id}-{day_i}"),
                    defaults={
                        "wallet":      wallet,
                        "tx_type":     Transaction.TxType.DEPOSIT,
                        "amount_arcx": arcx_qty,
                        "amount_inr":  Decimal(str(inr_amt)),
                        "nav_at_tx":   nav_inr,
                        "status":      Transaction.Status.COMPLETED,
                        "created_at":  tx_time,
                    },
                )
                total_arcx += arcx_qty
                total_cost += Decimal(str(inr_amt))

            # ── Peer Transfer: Alice → Bob on day 14 ─────────────────────
            if arcx_user.email == "alice@arcxtest.com":
                entry      = nav_series[14]
                nav_inr    = Decimal(str(entry["nav_inr"]))
                send_qty   = Decimal("50.000000000000000000")
                bob_user, bob_wallet = users_wallets[1]
                tx_time    = datetime.combine(entry["date"], datetime.min.time()) \
                             + timedelta(hours=11, minutes=30)
                tx_time    = timezone.make_aware(tx_time)

                Transaction.objects.get_or_create(
                    idempotency_key = uuid.uuid5(uuid.NAMESPACE_DNS, f"transfer-alice-bob-14"),
                    defaults={
                        "wallet":               wallet,
                        "tx_type":              Transaction.TxType.TRANSFER,
                        "amount_arcx":          -send_qty,
                        "amount_inr":           Decimal("0"),
                        "nav_at_tx":            nav_inr,
                        "status":               Transaction.Status.COMPLETED,
                        "counterparty_wallet":  bob_wallet,
                        "created_at":           tx_time,
                    },
                )
                total_arcx -= send_qty

                # Bob receives credit
                Transaction.objects.get_or_create(
                    idempotency_key = uuid.uuid5(uuid.NAMESPACE_DNS, f"transfer-alice-bob-14-recv"),
                    defaults={
                        "wallet":               bob_wallet,
                        "tx_type":              Transaction.TxType.TRANSFER,
                        "amount_arcx":          send_qty,
                        "amount_inr":           Decimal("0"),
                        "nav_at_tx":            nav_inr,
                        "status":               Transaction.Status.COMPLETED,
                        "counterparty_wallet":  wallet,
                        "created_at":           tx_time + timedelta(seconds=1),
                    },
                )

            # ── Dividends (every 3 days from when user first deposited) ──
            first_day_i = deposit_schedule[idx][0][0]
            for day_i in range(first_day_i + 3, DAYS, 3):
                entry      = nav_series[day_i]
                nav_inr    = Decimal(str(entry["nav_inr"]))
                # ~5% annual yield / 365 * 3 days
                yield_rate = Decimal("0.05") / Decimal("365") * Decimal("3")
                div_arcx   = total_arcx * yield_rate
                tx_time    = datetime.combine(entry["date"], datetime.min.time()) \
                             + timedelta(hours=0, minutes=1)
                tx_time    = timezone.make_aware(tx_time)

                Transaction.objects.get_or_create(
                    idempotency_key = uuid.uuid5(uuid.NAMESPACE_DNS, f"dividend-{arcx_user.id}-{day_i}"),
                    defaults={
                        "wallet":      wallet,
                        "tx_type":     Transaction.TxType.DIVIDEND,
                        "amount_arcx": div_arcx,
                        "amount_inr":  div_arcx * nav_inr,
                        "nav_at_tx":   nav_inr,
                        "status":      Transaction.Status.COMPLETED,
                        "created_at":  tx_time,
                    },
                )
                total_arcx += div_arcx

            # ── Update wallet final balance ────────────────────────────────
            with transaction.atomic():
                w = Wallet.objects.select_for_update().get(pk=wallet.pk)
                w.arcx_balance   = total_arcx
                w.cost_basis_inr = total_cost
                w.save(update_fields=["arcx_balance", "cost_basis_inr", "updated_at"])

            self.stdout.write(
                f"    ✓ {arcx_user.full_name:15s} → "
                f"{float(total_arcx):.4f} ARCX | "
                f"Cost ₹{float(total_cost):,.0f}"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Flush (clean wipe for re-seeding)
    # ─────────────────────────────────────────────────────────────────────────

    def _flush(self):
        self.stdout.write(self.style.WARNING("  [FLUSH] Removing previous simulation data..."))
        emails = [u["email"] for u in TEST_USERS]

        # Delete transactions first (FK constraints)
        arcx_users = User.objects.filter(email__in=emails)
        wallet_ids = Wallet.objects.filter(user__in=arcx_users).values_list("id", flat=True)
        Transaction.objects.filter(wallet_id__in=wallet_ids).delete()
        KYCRecord.objects.filter(user__in=arcx_users).delete()
        Wallet.objects.filter(user__in=arcx_users).delete()
        arcx_users.delete()
        DjangoUser.objects.filter(username__in=emails).delete()

        # Wipe NAV history (cascade-safe since VaultSnapshot → NAVHistory)
        NAVHistory.objects.all().delete()
        VaultSnapshot.objects.all().delete()

        self.stdout.write(self.style.WARNING("  [FLUSH] Done. Re-seeding...\n"))
