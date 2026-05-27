"""
ARCX Phase 6 — init_holdings Management Command
-------------------------------------------------
Run ONCE after migrating to initialize the VaultAssetHolding table.

On Day 0 (genesis), the vault is pure cash — no shares yet.
This command creates the 3 holding rows (SPY, TLT, GLD) with zero quantity.
The first Rebalancer run at 15:45 IST will then generate BUY instructions
to convert the cash into shares.

Usage:
    python manage.py init_holdings          # Creates zero-quantity rows (safe to re-run)
    python manage.py init_holdings --reset  # Wipes all holdings and recreates from zero

When to run:
    1. After running Phase 6 migrations for the first time
    2. After `python manage.py migrate` on a fresh deployment
    DO NOT run --reset in production unless you are intentionally clearing all positions.
"""

from decimal import Decimal
from django.core.management.base import BaseCommand
from arcx_core.models import VaultAssetHolding


INITIAL_HOLDINGS = [
    {
        "ticker":      "SPY",
        "description": "S&P 500 ETF — 40% US Stocks allocation",
    },
    {
        "ticker":      "TLT",
        "description": "20+ Year Treasury ETF — 30% Bonds allocation",
    },
    {
        "ticker":      "GLD",
        "description": "Gold ETF — 20% Gold allocation",
    },
]


class Command(BaseCommand):
    help = "Initialize VaultAssetHolding rows for Phase 6 (Quantity-Based Mark-to-Market)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "DELETE all existing holdings and recreate from zero. "
                "WARNING: Only use this in development, never in production!"
            ),
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n[*] ARCX Phase 6 — init_holdings\n"
        ))

        if options["reset"]:
            count = VaultAssetHolding.objects.count()
            VaultAssetHolding.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f"  [!] --reset: Deleted {count} existing holding rows.\n"
            ))

        created_any = False
        for h in INITIAL_HOLDINGS:
            obj, created = VaultAssetHolding.objects.get_or_create(
                asset_ticker = h["ticker"],
                defaults     = {
                    "total_quantity":    Decimal("0"),
                    "average_buy_price": Decimal("0"),
                },
            )

            if created:
                created_any = True
                self.stdout.write(self.style.SUCCESS(
                    f"  [+] Created: {h['ticker']} — {h['description']}"
                ))
            else:
                self.stdout.write(
                    f"  [=] Already exists: {h['ticker']} "
                    f"({obj.total_quantity} shares @ avg ${obj.average_buy_price})"
                )

        self.stdout.write("")

        if created_any:
            self.stdout.write(self.style.SUCCESS(
                "  Holdings initialized with zero quantities.\n"
                "  Next step: Run the Rebalancer to convert vault cash -> fractional shares.\n"
                "  Command: python manage.py run_scheduler  (or trigger Celery EOD task)\n"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "  All holdings already existed. Nothing was changed.\n"
                "  Use --reset to force recreate from zero.\n"
            ))

        # Print current state
        self.stdout.write(self.style.MIGRATE_HEADING("  Current Holdings State:"))
        all_holdings = VaultAssetHolding.objects.all().order_by("asset_ticker")
        if not all_holdings.exists():
            self.stdout.write("    (none)")
        else:
            for h in all_holdings:
                self.stdout.write(
                    f"    {h.asset_ticker}: {h.total_quantity} shares "
                    f"@ avg ${h.average_buy_price}"
                )
        self.stdout.write("")
