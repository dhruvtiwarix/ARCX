"""
ARCX Dividend Accrual Engine — Phase 1B
-----------------------------------------
Real funds don't just hold assets — they collect yield from them.
This engine calculates how much yield each asset generates daily
and adds it to the vault value automatically.

Annual Yield Constants (approximate, based on historical averages):
  SPY  (Stocks) : ~1.30% dividend yield per year
  TLT  (Bonds)  : ~4.00% coupon yield per year
  GLD  (Gold)   : ~0.00% (gold pays no dividends)
  Cash          : ~5.00% (approximates money market / T-bill rate)

How It Works:
  1. At midnight every day, the Celery worker calls accrue_daily_yield()
  2. This calculates each asset's daily yield contribution
  3. The total daily yield is added to vault_value_usd
  4. NAV = (vault_value + accrued_yield) / supply → ticks up overnight
  5. User wakes up to slightly more wealth. The "dopamine hit."

This is called "Daily Accrual" — used by every money market fund.
"""

from dataclasses import dataclass
from arcx_backend.domain.oracle import MarketPrices

# ── Annual Yield Constants ────────────────────────────────────────────────────
ANNUAL_YIELDS = {
    "stocks": 0.0130,  # SPY dividend yield ~1.3%
    "bonds": 0.0400,  # TLT coupon yield   ~4.0%
    "gold": 0.0000,  # GLD no yield
    "cash": 0.0500,  # Cash/T-bill rate   ~5.0%
}

# ── Vault Allocation Weights ──────────────────────────────────────────────────
WEIGHTS = {
    "stocks": 0.40,
    "bonds": 0.30,
    "gold": 0.20,
    "cash": 0.10,
}

DAYS_IN_YEAR = 365


@dataclass
class DailyAccrualResult:
    """Breakdown of yield earned in a single day."""
    stock_yield_usd: float  # Dividend from equity slice
    bond_yield_usd: float  # Coupon from bond slice
    gold_yield_usd: float  # Always 0.0
    cash_yield_usd: float  # Interest from cash slice
    total_yield_usd: float  # Sum of all above
    total_yield_inr: float  # Converted to INR for display
    yield_per_arcx_inr: float  # How much each token grew tonight


class DividendAccrualEngine:
    """
    Calculates and applies daily yield to the vault.

    This runs once per day at midnight via a Celery scheduled task.
    In Phase 1 (MVP), it runs manually when you call accrue_daily_yield().
    In Phase 3 (Django), it will be a Celery beat task.
    """

    def accrue_daily_yield(
            self,
            vault_value_usd: float,
            arcx_supply: float,
            prices: MarketPrices,
    ) -> DailyAccrualResult:
        """
        Calculates the yield earned today across all 4 asset classes.

        Formula per asset:
          daily_yield = vault_value * weight * (annual_yield / 365)

        Args:
            vault_value_usd: Current total vault value in USD
            arcx_supply:     Total ARCX tokens in circulation
            prices:          Live market prices (for INR conversion)

        Returns:
            DailyAccrualResult with full breakdown
        """
        # ── Calculate each asset's daily yield ───────────────────────────
        stock_value = vault_value_usd * WEIGHTS["stocks"]
        bond_value = vault_value_usd * WEIGHTS["bonds"]
        gold_value = vault_value_usd * WEIGHTS["gold"]
        cash_value = vault_value_usd * WEIGHTS["cash"]

        stock_yield = stock_value * (ANNUAL_YIELDS["stocks"] / DAYS_IN_YEAR)
        bond_yield = bond_value * (ANNUAL_YIELDS["bonds"] / DAYS_IN_YEAR)
        gold_yield = gold_value * (ANNUAL_YIELDS["gold"] / DAYS_IN_YEAR)
        cash_yield = cash_value * (ANNUAL_YIELDS["cash"] / DAYS_IN_YEAR)

        total_yield_usd = stock_yield + bond_yield + gold_yield + cash_yield
        total_yield_inr = total_yield_usd * prices.usd_inr

        # ── How much did each ARCX token grow tonight? ────────────────────
        yield_per_arcx_inr = (total_yield_inr / arcx_supply) if arcx_supply > 0 else 0

        return DailyAccrualResult(
            stock_yield_usd=round(stock_yield, 6),
            bond_yield_usd=round(bond_yield, 6),
            gold_yield_usd=round(gold_yield, 6),
            cash_yield_usd=round(cash_yield, 6),
            total_yield_usd=round(total_yield_usd, 6),
            total_yield_inr=round(total_yield_inr, 4),
            yield_per_arcx_inr=round(yield_per_arcx_inr, 6),
        )

    def project_annual_yield(
            self,
            vault_value_usd: float,
            prices: MarketPrices,
    ) -> dict:
        """
        Projects what the vault will earn over a full year.
        Useful for showing users their expected annual return.
        Returns a dict with per-asset and total annual yield.
        """
        result = {}
        for asset, weight in WEIGHTS.items():
            asset_value = vault_value_usd * weight
            annual_yield_usd = asset_value * ANNUAL_YIELDS[asset]
            annual_yield_inr = annual_yield_usd * prices.usd_inr
            result[asset] = {
                "annual_yield_usd": round(annual_yield_usd, 2),
                "annual_yield_inr": round(annual_yield_inr, 2),
                "annual_yield_pct": ANNUAL_YIELDS[asset] * 100,
            }

        total_usd = sum(v["annual_yield_usd"] for v in result.values())
        total_inr = sum(v["annual_yield_inr"] for v in result.values())
        blended_yield_pct = sum(
            WEIGHTS[a] * ANNUAL_YIELDS[a] for a in WEIGHTS
        ) * 100

        result["total"] = {
            "annual_yield_usd": round(total_usd, 2),
            "annual_yield_inr": round(total_inr, 2),
            "blended_yield_pct": round(blended_yield_pct, 4),
        }
        return result
