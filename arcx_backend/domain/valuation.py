"""
ARCX Valuation Engine — Phase 6 (Quantity-Based Mark-to-Market)
----------------------------------------------------------------
THE ARCHITECTURAL SHIFT:
  Phase 1-5: NAV was calculated from percentage weights (40/30/20/10).
             Formula: vault_value * 0.40 = "stocks slice"
             Problem: System never knew HOW MANY shares it actually owned.

  Phase 6+:  NAV is calculated from actual share quantities × live prices.
             Formula: spy_qty * spy_price + tlt_qty * tlt_price + gld_qty * gld_price + cash
             This is how every real fund in the world calculates NAV.

WHY THE OLD WAY BROKE:
  1. Stock splits: SPY does 2-for-1. Price: $500 → $250. Shares: 10 → 20.
     Old engine: "SPY dropped 50%! ARCX NAV crashed!" (WRONG)
     New engine: "10 shares at $500 = 20 shares at $250 = $5,000" (CORRECT)

  2. Broker integration: You cannot tell Alpaca "buy 40% worth of SPY".
     You must say "buy 10.5 fractional shares of SPY at market price".

  3. Reconciliation: At audit time, the question is always
     "how many shares do you own?" not "what % of your portfolio is stocks?"

THE 40/30/20/10 RULE IS NOT DEAD — it just moved.
  It now lives ONLY in the Rebalancer, which uses it to decide WHAT TO BUY.
  Once shares are purchased, their value is tracked by quantity, not percentage.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

from domain.oracle import MarketPrices


# ── Genesis Constants ─────────────────────────────────────────────────────────
# Day 0: 1 ARCX = ₹100 = $1.20 (at ₹83.5/$)
# Founder deposit: ₹1,00,000 = ~$1,197.60 buys 1,000 genesis ARCX tokens.
# On Day 0, no shares are purchased yet — vault is pure cash.
# The first Rebalancer run converts cash into the 40/30/20/10 allocation.

GENESIS_ARCX_SUPPLY    = Decimal("1000")
GENESIS_VAULT_CASH_USD = Decimal("1197.60")   # ₹1,00,000 at ₹83.5/$
GENESIS_NAV_INR        = Decimal("100.00")    # 1 ARCX = ₹100 on Day 0


@dataclass
class AssetPosition:
    """
    Represents one asset's contribution to vault value.
    Created fresh each time NAV is calculated — not persisted in DB.

    This is a pure computation output, not a storage object.
    """
    ticker:             str
    quantity:           Decimal    # Fractional shares owned
    live_price_usd:     Decimal    # Current market price (from Oracle)
    market_value_usd:   Decimal    # quantity × live_price (calculated)
    average_buy_price:  Decimal    # What we paid per share (for cost-basis analytics)
    unrealized_pnl_usd: Decimal    # market_value - (quantity × avg_buy_price)


@dataclass
class VaultState:
    """
    Complete snapshot of vault value at a single point in time.

    Phase 6 change: now includes per-asset positions list instead of
    simple stock/bond/gold float values. The old float fields are
    preserved as computed properties for backward compatibility with
    existing views and serializers.
    """
    # Per-asset position breakdown (list of AssetPosition)
    positions:             List[AssetPosition]

    # Totals
    total_equity_usd:      Decimal   # Sum of all position market values (SPY + TLT + GLD)
    cash_balance_usd:      Decimal   # The 10% cash slice (USD)
    total_vault_value_usd: Decimal   # total_equity + cash

    # Supply
    arcx_supply:           Decimal

    # NAV
    nav_usd:               Decimal   # total_vault / arcx_supply
    nav_inr:               Decimal   # nav_usd × usd_inr_rate

    # ── Backward-Compat Properties ───────────────────────────────────────────
    # Existing views/serializers reference these by name.
    # They are now computed from positions, not stored separately.
    # This avoids a breaking change across the codebase.

    @property
    def stock_value_usd(self) -> Decimal:
        pos = next((p for p in self.positions if p.ticker == "SPY"), None)
        return pos.market_value_usd if pos else Decimal("0")

    @property
    def bond_value_usd(self) -> Decimal:
        pos = next((p for p in self.positions if p.ticker == "TLT"), None)
        return pos.market_value_usd if pos else Decimal("0")

    @property
    def gold_value_usd(self) -> Decimal:
        pos = next((p for p in self.positions if p.ticker == "GLD"), None)
        return pos.market_value_usd if pos else Decimal("0")

    @property
    def cash_value_usd(self) -> Decimal:
        """Alias so old code calling state.cash_value_usd still works."""
        return self.cash_balance_usd


class ValuationEngine:
    """
    Phase 6 NAV Engine — Mark-to-Market on actual share quantities.

    This class has ZERO knowledge of Django, PostgreSQL, or any framework.
    It receives holdings data and prices, returns vault state.
    Pure math. Fully testable without a database.

    USAGE (from Django views/tasks):
        from arcx_core.models import VaultAssetHolding, VaultSnapshot
        from domain.valuation import ValuationEngine

        holdings = VaultAssetHolding.objects.all()
        snapshot = VaultSnapshot.objects.latest("snapshot_date")
        prices   = oracle.fetch_prices()

        engine = ValuationEngine(
            arcx_supply      = float(snapshot.arcx_supply),
            cash_balance_usd = float(snapshot.cash_value_usd),
        )
        state = engine.calculate_nav(holdings, prices)
    """

    def __init__(self, arcx_supply: float, cash_balance_usd: float):
        """
        Args:
            arcx_supply:      Total ARCX tokens currently in circulation.
            cash_balance_usd: The cash portion of the vault in USD (the 10% slice).
        """
        if arcx_supply < 0:
            raise ValueError("arcx_supply cannot be negative.")
        if cash_balance_usd < 0:
            raise ValueError("cash_balance_usd cannot be negative.")

        self.arcx_supply      = Decimal(str(arcx_supply))
        self.cash_balance_usd = Decimal(str(cash_balance_usd))

    def calculate_nav(self, holdings, prices: MarketPrices) -> VaultState:
        """
        Core Mark-to-Market NAV calculation.

        Args:
            holdings: Iterable of VaultAssetHolding model instances
                      (or any object with .asset_ticker, .total_quantity, .average_buy_price)
            prices:   MarketPrices from MultiSourceOracle

        Returns:
            VaultState with full position breakdown and NAV

        The math:
            For each holding: market_value = quantity × live_price
            total_equity = Σ(all market values)
            total_vault  = total_equity + cash_balance
            nav_usd      = total_vault / arcx_supply
            nav_inr      = nav_usd × usd_inr
        """
        live_prices = {
            "SPY": Decimal(str(prices.spy)),
            "TLT": Decimal(str(prices.tlt)),
            "GLD": Decimal(str(prices.gld)),
        }

        positions: List[AssetPosition] = []
        total_equity_usd = Decimal("0")

        for holding in holdings:
            ticker     = holding.asset_ticker
            qty        = Decimal(str(holding.total_quantity))
            avg_buy    = Decimal(str(holding.average_buy_price))
            live_price = live_prices.get(ticker, Decimal("0"))

            market_value    = (qty * live_price).quantize(Decimal("0.0001"))
            cost_of_holding = (qty * avg_buy).quantize(Decimal("0.0001"))
            unrealized_pnl  = market_value - cost_of_holding

            positions.append(AssetPosition(
                ticker             = ticker,
                quantity           = qty,
                live_price_usd     = live_price,
                market_value_usd   = market_value,
                average_buy_price  = avg_buy,
                unrealized_pnl_usd = unrealized_pnl,
            ))

            total_equity_usd += market_value

        total_vault_value_usd = total_equity_usd + self.cash_balance_usd

        # Genesis guard: if no supply yet, return genesis peg (₹100)
        if self.arcx_supply <= 0:
            return self._genesis_state(positions, total_vault_value_usd, prices)

        nav_usd = (total_vault_value_usd / self.arcx_supply).quantize(Decimal("0.00000001"))
        nav_inr = (nav_usd * Decimal(str(prices.usd_inr))).quantize(Decimal("0.0001"))

        return VaultState(
            positions             = positions,
            total_equity_usd      = total_equity_usd,
            cash_balance_usd      = self.cash_balance_usd,
            total_vault_value_usd = total_vault_value_usd,
            arcx_supply           = self.arcx_supply,
            nav_usd               = nav_usd,
            nav_inr               = nav_inr,
        )

    def _genesis_state(self, positions, total_vault_usd, prices) -> VaultState:
        """
        Returns genesis-peg NAV when supply is zero (Day 0 bootstrap).
        Pegged to ₹100 per ARCX.
        """
        nav_usd = GENESIS_NAV_INR / Decimal(str(prices.usd_inr))
        return VaultState(
            positions             = positions,
            total_equity_usd      = Decimal("0"),
            cash_balance_usd      = self.cash_balance_usd,
            total_vault_value_usd = total_vault_usd,
            arcx_supply           = Decimal("0"),
            nav_usd               = nav_usd.quantize(Decimal("0.00000001")),
            nav_inr               = GENESIS_NAV_INR,
        )

    @classmethod
    def from_genesis(cls, prices: MarketPrices) -> "ValuationEngine":
        """
        Bootstrap for Day 0.
        Converts founder's ₹1,00,000 deposit to USD and creates genesis engine.
        On Day 0, the vault is pure cash — no shares purchased yet.
        The Rebalancer task will convert cash to shares on first run.
        """
        founder_deposit_usd = (
            Decimal("100000") / Decimal(str(prices.usd_inr))
        ).quantize(Decimal("0.0001"))

        return cls(
            arcx_supply      = float(GENESIS_ARCX_SUPPLY),
            cash_balance_usd = float(founder_deposit_usd),
        )
