import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "arcx_backend.settings")
django.setup()

from datetime import date
from decimal import Decimal
from django.db.models import Sum
from arcx_core.models import Wallet, VaultSnapshot, VaultAssetHolding, NAVHistory

def repair():
    # 1. Delete bad data
    NAVHistory.objects.filter(nav_date__gte=date(2026, 5, 26)).delete()
    VaultSnapshot.objects.filter(snapshot_date__gte=date(2026, 5, 26)).delete()
    VaultAssetHolding.objects.all().delete()
    print("Deleted bad snapshots and holdings.")

    # 2. Get true wallet supply
    total_arcx = Wallet.objects.aggregate(Sum('arcx_balance'))['arcx_balance__sum']
    if not total_arcx:
        total_arcx = Decimal("1000")
    print(f"True ARCX Supply: {total_arcx}")

    # 3. Find the last good snapshot (May 22)
    latest = VaultSnapshot.objects.order_by('-snapshot_date').first()
    if latest:
        # We know NAV is total / supply.
        # So new total = NAV * true_supply
        nav_usd = latest.total_value_usd / latest.arcx_supply
        new_total = nav_usd * total_arcx
        
        latest.arcx_supply = total_arcx
        latest.cash_value_usd = new_total
        latest.total_value_usd = new_total
        latest.save()
        print(f"Updated snapshot {latest.snapshot_date} with true supply. New Total USD: {new_total}")

if __name__ == "__main__":
    repair()
