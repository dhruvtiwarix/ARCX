# ARCX Phase 6 — The Holdings Ledger
## Complete Implementation Guide

---

## FILE 1: arcx_core/models.py — Add VaultAssetHolding

Add this class **after** the `VaultSnapshot` model, **before** `NAVHistory`:

```python
# ─────────────────────────────────────────────────────────────────────────────
# Vault Asset Holdings (Phase 6 — Quantity-Based Mark-to-Market)
# ─────────────────────────────────────────────────────────────────────────────

class VaultAssetHolding(ArcxBaseModel):
    """
    The source of truth for what ARCX physically holds in the global market.

    WHY THIS TABLE EXISTS:
      The old system tracked allocations as percentages (40/30/20/10).
      That model breaks in the real world:
        - Stock splits: SPY does 2-for-1 → price halves, but old system thinks vault lost 50%
        - Corporate actions: dividends, spinoffs
        - Broker reconciliation: you cannot tell a broker "buy 40% worth of SPY"
          You tell them "buy 14.5 shares of SPY at market price"

      This table stores the EXACT fractional shares the vault holds.
      Valuation is then: quantity * live_price (Mark-to-Market).

    ONE ROW PER ASSET:
      SPY → 14.502394850000000000 shares at avg $530.2500
      TLT →  9.812456780000000000 shares at avg $94.8000
      GLD → 12.345678900000000000 shares at avg $184.5000

    Cash (10% slice) is NOT stored here.
    It lives as cash_balance_usd in VaultSnapshot.
    Cash has no "shares" — it is just a USD balance.

    AVERAGE BUY PRICE:
      Calculated as weighted average every time we buy more.
      Formula: new_avg = (old_qty * old_avg + new_qty * new_price) / (old_qty + new_qty)
      Used for cost-basis reporting and P&L analytics. NOT used for NAV calculation.
      NAV only uses: quantity * live_price (current market value, not what we paid).
    """

    class AssetTicker(models.TextChoices):
        SPY = "SPY", "S&P 500 ETF (Stocks)"
        TLT = "TLT", "20+ Year Treasury ETF (Bonds)"
        GLD = "GLD", "Gold ETF"

    asset_ticker      = models.CharField(
        max_length=10,
        unique=True,                  # One row per asset — enforced at DB level
        choices=AssetTicker.choices,
        db_index=True,
    )
    total_quantity    = models.DecimalField(
        max_digits=28,
        decimal_places=18,            # 18 decimals = fractional share precision
        default=Decimal("0"),
        help_text="Total fractional shares held. e.g. 14.502394850000000000"
    )
    average_buy_price = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal("0"),
        help_text="Weighted average purchase price in USD. Used for cost-basis, not NAV."
    )

    class Meta:
        db_table = "vault_asset_holdings"
        verbose_name        = "Vault Asset Holding"
        verbose_name_plural = "Vault Asset Holdings"

    def update_on_buy(self, new_quantity: Decimal, execution_price: Decimal):
        """
        Updates quantity and recalculates weighted average buy price.

        Call this after every broker execution (buy order).
        This is the ONLY correct way to update holdings — never set fields directly.

        Args:
            new_quantity:    Fractional shares purchased (e.g., Decimal("0.0096"))
            execution_price: Price per share at execution (e.g., Decimal("500.00"))

        Formula:
            new_avg = (old_qty * old_avg + new_qty * exec_price) / (old_qty + new_qty)
        """
        if new_quantity <= 0:
            raise ValueError("new_quantity must be positive for a buy.")
        if execution_price <= 0:
            raise ValueError("execution_price must be positive.")

        old_qty   = self.total_quantity
        old_avg   = self.average_buy_price
        new_total = old_qty + new_quantity

        # Weighted average: prevents distortion from buying at different prices
        if new_total > 0:
            new_avg = ((old_qty * old_avg) + (new_quantity * execution_price)) / new_total
        else:
            new_avg = execution_price

        self.total_quantity    = new_total
        self.average_buy_price = new_avg.quantize(Decimal("0.0001"))

    def update_on_sell(self, sell_quantity: Decimal):
        """
        Reduces quantity on a sell/rebalance-out order.
        Average buy price does NOT change on sells (FIFO/avg-cost standard).

        Args:
            sell_quantity: Fractional shares sold (positive number)
        """
        if sell_quantity <= 0:
            raise ValueError("sell_quantity must be positive.")
        if sell_quantity > self.total_quantity:
            raise ValueError(
                f"Cannot sell {sell_quantity} shares of {self.asset_ticker}. "
                f"Only {self.total_quantity} held."
            )
        self.total_quantity -= sell_quantity

    def __str__(self):
        return (
            f"{self.asset_ticker}: {self.total_quantity} shares "
            f"@ avg ${self.average_buy_price}"
        )
```

---

## FILE 2: arcx_core/migrations/0003_vault_asset_holdings.py — New Migration

```python
# arcx_core/migrations/0003_vault_asset_holdings.py

import decimal
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('arcx_core', '0002_add_fee_inr_settlement_date_to_transaction'),
    ]

    operations = [
        migrations.CreateModel(
            name='VaultAssetHolding',
            fields=[
                ('id',                models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at',        models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at',        models.DateTimeField(auto_now=True)),
                ('deleted_at',        models.DateTimeField(blank=True, db_index=True, null=True)),
                ('asset_ticker',      models.CharField(
                    choices=[('SPY', 'S&P 500 ETF (Stocks)'), ('TLT', '20+ Year Treasury ETF (Bonds)'), ('GLD', 'Gold ETF')],
                    db_index=True, max_length=10, unique=True
                )),
                ('total_quantity',    models.DecimalField(
                    decimal_places=18, default=decimal.Decimal('0'),
                    help_text='Total fractional shares held.',
                    max_digits=28
                )),
                ('average_buy_price', models.DecimalField(
                    decimal_places=4, default=decimal.Decimal('0'),
                    help_text='Weighted average purchase price in USD.',
                    max_digits=20
                )),
            ],
            options={
                'verbose_name':        'Vault Asset Holding',
                'verbose_name_plural': 'Vault Asset Holdings',
                'db_table':            'vault_asset_holdings',
            },
        ),
    ]
```

---

## FILE 3: domain/valuation.py — Complete Rewrite

Replace the entire file:

```python
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
from typing import List, Optional
from domain.oracle import MarketPrices


# ── Genesis Constants ─────────────────────────────────────────────────────────
# Day 0: 1 ARCX = ₹100 = $1.20 (at ₹83.5/$)
# Founder deposit: ₹1,00,000 = ~$1,197.60 buys 1,000 genesis ARCX tokens.
# On Day 0, no shares are purchased yet — vault is pure cash.
# The first Rebalancer run converts cash into the 40/30/20/10 allocation.

GENESIS_ARCX_SUPPLY     = Decimal("1000")
GENESIS_VAULT_CASH_USD  = Decimal("1197.60")   # ₹1,00,000 at ₹83.5/$
GENESIS_NAV_INR         = Decimal("100.00")    # 1 ARCX = ₹100 on Day 0


@dataclass
class AssetPosition:
    """
    Represents one asset's contribution to vault value.
    Created fresh each time NAV is calculated (not persisted).
    """
    ticker:          str
    quantity:        Decimal    # Fractional shares owned
    live_price_usd:  Decimal    # Current market price (from Oracle)
    market_value_usd: Decimal   # quantity × live_price (calculated)
    average_buy_price: Decimal  # What we paid per share (for cost-basis analytics)
    unrealized_pnl_usd: Decimal # market_value - (quantity × avg_buy_price)


@dataclass
class VaultState:
    """
    Complete snapshot of vault value at a point in time.
    Replaces the old VaultState — now includes per-asset positions.
    """
    # Per-asset breakdown
    positions:            List[AssetPosition]

    # Totals
    total_equity_usd:     Decimal   # Sum of all position market values
    cash_balance_usd:     Decimal   # The 10% cash slice (USD)
    total_vault_value_usd: Decimal  # equity + cash

    # Supply
    arcx_supply:          Decimal

    # NAV
    nav_usd:              Decimal   # total_vault / arcx_supply
    nav_inr:              Decimal   # nav_usd × usd_inr_rate

    # Backward-compatible fields for existing views/serializers
    # These are computed from positions, not stored separately
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


class ValuationEngine:
    """
    Phase 6 NAV Engine — Mark-to-Market on actual share quantities.

    This class has ZERO knowledge of Django, PostgreSQL, or any framework.
    It receives holdings data and prices, and returns vault state.
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
                ticker            = ticker,
                quantity          = qty,
                live_price_usd    = live_price,
                market_value_usd  = market_value,
                average_buy_price = avg_buy,
                unrealized_pnl_usd = unrealized_pnl,
            ))

            total_equity_usd += market_value

        total_vault_value_usd = total_equity_usd + self.cash_balance_usd

        # Genesis guard: if no supply yet, return genesis peg
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
        """Returns genesis-peg NAV when supply is zero (Day 0 bootstrap)."""
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
```

---

## FILE 4: domain/rebalancer.py — Upgrade to Quantity-Based Trades

Replace the `RebalanceTrade` dataclass and `DriftRebalancer.analyze()`:

```python
"""
ARCX Drift Rebalancer — Phase 6 (Quantity-Based Trades)
---------------------------------------------------------
WHAT CHANGED FROM PHASE 5:
  Old: Trade instruction was "BUY $4.80 of SPY"
       → Cannot execute at broker. Brokers need share counts.

  New: Trade instruction is "BUY 0.0096 shares of SPY at $500.00"
       → Directly executable at Alpaca / IBKR / Zerodha.

The Rebalancer still uses the 40/30/20/10 target weights to decide
WHAT to buy/sell. But the output is now share quantities, not dollar amounts.

EXECUTION MATH:
  shares_to_buy = dollar_amount_needed / current_live_price
  e.g. Need $4.80 more of SPY. SPY is at $480.
       shares_to_buy = 4.80 / 480 = 0.01 shares

This is fractional share trading — exactly how Alpaca and IBKR work.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional
from domain.oracle import MarketPrices

# ── Target Allocation ─────────────────────────────────────────────────────────
TARGET_WEIGHTS = {
    "SPY": Decimal("0.40"),   # 40% → US Stocks
    "TLT": Decimal("0.30"),   # 30% → Bonds
    "GLD": Decimal("0.20"),   # 20% → Gold
    # Cash (10%) is implicitly the remainder — not traded via broker
}
CASH_WEIGHT     = Decimal("0.10")
DRIFT_TOLERANCE = Decimal("0.03")   # ±3% triggers rebalance


@dataclass
class AssetWeight:
    """Current vs target allocation for one asset."""
    ticker:          str
    target_weight:   Decimal
    actual_weight:   Decimal
    drift:           Decimal          # actual - target (positive = overweight)
    needs_rebalance: bool


@dataclass
class RebalanceTrade:
    """
    A broker-executable trade instruction.

    Phase 6 change: now contains share_quantity, not just dollar_amount.
    The broker API receives: action, ticker, share_quantity.
    """
    ticker:          str
    action:          str              # "BUY" or "SELL"
    share_quantity:  Decimal          # FRACTIONAL shares to buy/sell
    dollar_amount:   Decimal          # USD value of the trade (for logging)
    execution_price: Decimal          # Live price used to calculate shares
    reason:          str


@dataclass
class RebalanceReport:
    """Complete rebalancing analysis."""
    weights:           List[AssetWeight]
    trades:            List[RebalanceTrade]
    rebalance_needed:  bool
    total_drift:       Decimal
    vault_value_usd:   Decimal


class DriftRebalancer:
    """
    Monitors vault allocation and generates broker-executable trade instructions.

    INPUT:  Current holdings (shares + value) + live prices
    OUTPUT: List of RebalanceTrade objects with exact share quantities

    This class does NOT execute trades.
    Phase 7 (Alpaca integration) will read these trades and submit them.
    """

    def analyze(
        self,
        vault_value_usd:  float,
        holdings:         dict,    # {"SPY": {"value": 4000, "qty": 7.5}, ...}
        cash_balance_usd: float,
        live_prices:      dict,    # {"SPY": 530.00, "TLT": 95.00, "GLD": 185.00}
    ) -> RebalanceReport:
        """
        Analyzes current holdings vs target weights and generates trades.

        Args:
            vault_value_usd:  Total vault value in USD (equity + cash)
            holdings:         Current holdings dict with value and quantity per ticker
            cash_balance_usd: Current cash balance (not traded via broker)
            live_prices:      Current live prices from Oracle

        Returns:
            RebalanceReport with broker-executable RebalanceTrade objects
        """
        vault_usd = Decimal(str(vault_value_usd))

        # ── Step 1: Calculate actual weights ─────────────────────────────
        weights = []
        for ticker, target in TARGET_WEIGHTS.items():
            holding    = holdings.get(ticker, {"value": 0, "qty": 0})
            actual_val = Decimal(str(holding.get("value", 0)))
            actual_wt  = (actual_val / vault_usd) if vault_usd > 0 else Decimal("0")
            drift      = actual_wt - target

            weights.append(AssetWeight(
                ticker          = ticker,
                target_weight   = target,
                actual_weight   = actual_wt.quantize(Decimal("0.0001")),
                drift           = drift.quantize(Decimal("0.0001")),
                needs_rebalance = abs(drift) > DRIFT_TOLERANCE,
            ))

        # ── Step 2: Generate quantity-based trade instructions ────────────
        trades: List[RebalanceTrade] = []
        rebalance_needed = any(w.needs_rebalance for w in weights)

        if rebalance_needed:
            for w in weights:
                if abs(w.drift) <= DRIFT_TOLERANCE:
                    continue

                target_value  = vault_usd * w.target_weight
                actual_value  = Decimal(str(holdings.get(w.ticker, {}).get("value", 0)))
                delta_usd     = target_value - actual_value   # + = need to buy, - = need to sell

                live_price    = Decimal(str(live_prices.get(w.ticker, 1)))
                if live_price <= 0:
                    continue

                # THE KEY PHASE 6 CALCULATION:
                # Dollar amount needed → fractional shares to trade
                share_quantity = (abs(delta_usd) / live_price).quantize(
                    Decimal("0.000000000000000001")
                )

                action = "BUY" if delta_usd > 0 else "SELL"

                trades.append(RebalanceTrade(
                    ticker          = w.ticker,
                    action          = action,
                    share_quantity  = share_quantity,
                    dollar_amount   = abs(delta_usd).quantize(Decimal("0.01")),
                    execution_price = live_price,
                    reason          = (
                        f"{w.ticker} drifted {float(w.drift) * 100:+.1f}% from target "
                        f"({float(w.actual_weight) * 100:.1f}% actual vs "
                        f"{float(w.target_weight) * 100:.1f}% target). "
                        f"{action} {float(share_quantity):.8f} shares @ ${float(live_price):.2f}"
                    ),
                ))

        total_drift = sum(abs(w.drift) for w in weights)

        return RebalanceReport(
            weights          = weights,
            trades           = trades,
            rebalance_needed = rebalance_needed,
            total_drift      = total_drift.quantize(Decimal("0.0001")),
            vault_value_usd  = vault_usd,
        )
```

---

## FILE 5: arcx_core/services/wallet_service.py — Deposit Updates Holdings

Add this method to `WalletService`. After a deposit, the vault has more cash.
The Rebalancer task (runs at EOD) will convert that cash into shares.
For the deposit itself, we only update the cash balance:

```python
# In WalletService.deposit() — after wallet.save(), ADD THIS:

# Phase 6: Track cash influx in VaultSnapshot
# The rebalancer will convert this cash to shares at market close (15:30 IST)
# For now we update the cash_value_usd in the latest snapshot
try:
    from arcx_core.models import VaultSnapshot
    from decimal import Decimal as D
    amount_usd = (amount_inr / nav_inr).quantize(D("0.0001"))
    latest_snapshot = VaultSnapshot.objects.latest("snapshot_date")
    latest_snapshot.cash_value_usd  += amount_usd
    latest_snapshot.total_value_usd += amount_usd
    latest_snapshot.save(update_fields=["cash_value_usd", "total_value_usd", "updated_at"])
except VaultSnapshot.DoesNotExist:
    pass   # Genesis — first snapshot will pick it up
```

---

## FILE 6: arcx_core/views/oracle_views.py — Use New Engine

Update `LivePriceView.get()` to pass holdings to the engine:

```python
# In LivePriceView.get(), replace the engine block:

from arcx_core.models import VaultSnapshot, VaultAssetHolding

try:
    snapshot = VaultSnapshot.objects.latest("snapshot_date")
    holdings = VaultAssetHolding.objects.all()
    engine   = ValuationEngine(
        arcx_supply      = float(snapshot.arcx_supply),
        cash_balance_usd = float(snapshot.cash_value_usd),
    )
    state = engine.calculate_nav(holdings, prices)
except VaultSnapshot.DoesNotExist:
    engine = ValuationEngine.from_genesis(prices)
    state  = engine.calculate_nav([], prices)   # empty holdings on Day 0
```

---

## FILE 7: arcx_core/tasks/eod_tasks.py — take_vault_snapshot() Update

Update the snapshot task to save per-asset holdings to VaultSnapshot:

```python
# In take_vault_snapshot(), replace the engine/state block:

from arcx_core.models import VaultAssetHolding

holdings = list(VaultAssetHolding.objects.all())

try:
    prev = VaultSnapshot.objects.exclude(snapshot_date=today).latest("snapshot_date")
    engine = ValuationEngine(
        arcx_supply      = float(prev.arcx_supply),
        cash_balance_usd = float(prev.cash_value_usd),
    )
except VaultSnapshot.DoesNotExist:
    engine = ValuationEngine.from_genesis(prices)

state = engine.calculate_nav(holdings, prices)

# Now state.stock_value_usd / bond_value_usd / gold_value_usd
# are computed from actual holdings, not weights — no other changes needed
```

---

## FILE 8: Management Command — Initialize Holdings on First Run

Create `arcx_core/management/commands/init_holdings.py`:

```python
"""
ARCX Phase 6 — init_holdings Management Command
-------------------------------------------------
Run ONCE after migrating to initialize the VaultAssetHolding table.

On Day 0 (genesis), the vault is pure cash — no shares yet.
This command creates the 3 holding rows with zero quantity.
The first Rebalancer run will then buy shares with the cash.

Usage:
    python manage.py init_holdings          # Creates zero-quantity rows
    python manage.py init_holdings --reset  # Wipes and recreates
"""

from decimal import Decimal
from django.core.management.base import BaseCommand
from arcx_core.models import VaultAssetHolding


INITIAL_HOLDINGS = [
    {"ticker": "SPY", "description": "S&P 500 ETF — 40% Stocks allocation"},
    {"ticker": "TLT", "description": "20+ Year Treasury ETF — 30% Bonds"},
    {"ticker": "GLD", "description": "Gold ETF — 20% Gold allocation"},
]


class Command(BaseCommand):
    help = "Initialize VaultAssetHolding rows (Phase 6)"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Delete all holdings and recreate.")

    def handle(self, *args, **options):
        if options["reset"]:
            VaultAssetHolding.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Holdings cleared."))

        for h in INITIAL_HOLDINGS:
            obj, created = VaultAssetHolding.objects.get_or_create(
                asset_ticker=h["ticker"],
                defaults={
                    "total_quantity":    Decimal("0"),
                    "average_buy_price": Decimal("0"),
                },
            )
            status = "Created" if created else "Already exists"
            self.stdout.write(
                self.style.SUCCESS(f"  {status}: {h['ticker']} — {h['description']}")
            )

        self.stdout.write(self.style.SUCCESS("\n  Holdings initialized. Run rebalancer to allocate cash → shares."))
```

---

## FILE 9: tests/test_phase6.py — Unit Tests

```python
"""
ARCX Phase 6 — Holdings Engine Tests
--------------------------------------
Tests for the quantity-based Mark-to-Market valuation engine.
All tests use mock data — no DB, no Oracle, no network.

Run: python manage.py test tests.test_phase6
"""

from decimal import Decimal
from datetime import datetime
from unittest.mock import MagicMock
from django.test import TestCase

from domain.oracle import MarketPrices
from domain.valuation import ValuationEngine, GENESIS_NAV_INR
from domain.rebalancer import DriftRebalancer, DRIFT_TOLERANCE


def mock_prices(spy=530.0, tlt=95.0, gld=185.0, usd_inr=83.5):
    m = MagicMock()
    m.spy = spy; m.tlt = tlt; m.gld = gld; m.usd_inr = usd_inr
    m.fetched_at = datetime.now()
    m.sources_used = ["Mock"]
    return m


def mock_holding(ticker, qty, avg_price):
    h = MagicMock()
    h.asset_ticker     = ticker
    h.total_quantity   = Decimal(str(qty))
    h.average_buy_price = Decimal(str(avg_price))
    return h


class TestProductionValuationEngine(TestCase):

    def setUp(self):
        self.prices = mock_prices()

    def test_mark_to_market_basic(self):
        """10 SPY shares at $530 = $5,300 + cash."""
        holdings = [mock_holding("SPY", 10.0, 500.0)]
        engine   = ValuationEngine(arcx_supply=1000.0, cash_balance_usd=1000.0)
        state    = engine.calculate_nav(holdings, self.prices)

        self.assertAlmostEqual(float(state.stock_value_usd), 5300.0, places=2)
        self.assertAlmostEqual(float(state.cash_balance_usd), 1000.0, places=2)
        self.assertAlmostEqual(float(state.total_vault_value_usd), 6300.0, places=2)

    def test_nav_formula_correct(self):
        """NAV = total_vault / arcx_supply."""
        holdings = [
            mock_holding("SPY", 10.0, 500.0),   # 10 × $530 = $5,300
            mock_holding("TLT",  5.0,  90.0),   #  5 × $95  = $475
        ]
        engine = ValuationEngine(arcx_supply=100.0, cash_balance_usd=200.0)
        state  = engine.calculate_nav(holdings, self.prices)

        # $5,300 + $475 + $200 = $5,975 / 100 = $59.75
        self.assertAlmostEqual(float(state.nav_usd), 59.75, places=2)

    def test_stock_split_resilience(self):
        """
        2-for-1 split: price halves, quantity doubles → value unchanged.
        Old % engine FAILS this. New quantity engine PASSES.
        """
        # Before split: 10 shares at $500 = $5,000
        holdings_before = [mock_holding("SPY", 10.0, 500.0)]
        engine = ValuationEngine(arcx_supply=1000.0, cash_balance_usd=0.0)
        state_before = engine.calculate_nav(
            holdings_before, mock_prices(spy=500.0)
        )

        # After split: 20 shares at $250 = $5,000 (same value!)
        holdings_after = [mock_holding("SPY", 20.0, 250.0)]
        state_after = engine.calculate_nav(
            holdings_after, mock_prices(spy=250.0)
        )

        # Value MUST be unchanged — this is the key correctness test
        self.assertAlmostEqual(
            float(state_before.total_vault_value_usd),
            float(state_after.total_vault_value_usd),
            places=2,
            msg="Stock split changed vault value — BUG in valuation engine!",
        )

    def test_empty_holdings_uses_cash_only(self):
        """Day 0: no shares purchased yet. Vault = pure cash."""
        engine = ValuationEngine(arcx_supply=1000.0, cash_balance_usd=1197.60)
        state  = engine.calculate_nav([], self.prices)

        self.assertAlmostEqual(float(state.total_vault_value_usd), 1197.60, places=2)
        self.assertEqual(len(state.positions), 0)

    def test_genesis_returns_peg(self):
        """Zero supply returns genesis NAV peg (₹100)."""
        engine = ValuationEngine(arcx_supply=0.0, cash_balance_usd=0.0)
        state  = engine.calculate_nav([], self.prices)
        self.assertEqual(state.nav_inr, GENESIS_NAV_INR)

    def test_unrealized_pnl_calculated(self):
        """Position P&L: bought at $500, now at $530 → +$300 on 10 shares."""
        holdings = [mock_holding("SPY", 10.0, 500.0)]
        engine   = ValuationEngine(arcx_supply=1000.0, cash_balance_usd=0.0)
        state    = engine.calculate_nav(holdings, mock_prices(spy=530.0))

        spy_pos = next(p for p in state.positions if p.ticker == "SPY")
        self.assertAlmostEqual(float(spy_pos.unrealized_pnl_usd), 300.0, places=2)

    def test_backward_compat_properties(self):
        """stock_value_usd, bond_value_usd, gold_value_usd still work."""
        holdings = [
            mock_holding("SPY", 8.0, 500.0),    # 8 × $530 = $4,240
            mock_holding("TLT", 3.0, 90.0),     # 3 × $95  = $285
            mock_holding("GLD", 1.0, 180.0),    # 1 × $185 = $185
        ]
        engine = ValuationEngine(arcx_supply=1000.0, cash_balance_usd=0.0)
        state  = engine.calculate_nav(holdings, self.prices)

        self.assertAlmostEqual(float(state.stock_value_usd), 4240.0, places=1)
        self.assertAlmostEqual(float(state.bond_value_usd),   285.0, places=1)
        self.assertAlmostEqual(float(state.gold_value_usd),   185.0, places=1)


class TestQuantityBasedRebalancer(TestCase):

    def setUp(self):
        self.rebalancer = DriftRebalancer()
        self.live_prices = {"SPY": 530.0, "TLT": 95.0, "GLD": 185.0}

    def test_perfect_balance_no_trades(self):
        """Exactly 40/30/20/10 allocation = no rebalance needed."""
        holdings = {
            "SPY": {"value": 4000, "qty": 7.547},
            "TLT": {"value": 3000, "qty": 31.578},
            "GLD": {"value": 2000, "qty": 10.810},
        }
        report = self.rebalancer.analyze(
            vault_value_usd=10000.0, holdings=holdings,
            cash_balance_usd=1000.0, live_prices=self.live_prices
        )
        self.assertFalse(report.rebalance_needed)

    def test_trade_output_has_share_quantity(self):
        """Trades must specify share_quantity, not just dollar_amount."""
        holdings = {
            "SPY": {"value": 2000, "qty": 3.77},   # Underweight (20% vs 40% target)
            "TLT": {"value": 3000, "qty": 31.578},
            "GLD": {"value": 4000, "qty": 21.621}, # Overweight (40% vs 20% target)
        }
        report = self.rebalancer.analyze(
            vault_value_usd=10000.0, holdings=holdings,
            cash_balance_usd=1000.0, live_prices=self.live_prices
        )
        self.assertTrue(report.rebalance_needed)
        for trade in report.trades:
            self.assertGreater(trade.share_quantity, 0)
            self.assertIn(trade.action, ["BUY", "SELL"])

    def test_buy_quantity_math(self):
        """BUY quantity = dollar_amount / live_price."""
        holdings = {
            "SPY": {"value": 2000, "qty": 3.77},   # Needs $2,000 more (40% of $10k - $2k)
            "TLT": {"value": 3000, "qty": 31.578},
            "GLD": {"value": 2000, "qty": 10.810},
        }
        report = self.rebalancer.analyze(
            vault_value_usd=10000.0, holdings=holdings,
            cash_balance_usd=3000.0, live_prices=self.live_prices
        )
        spy_trade = next((t for t in report.trades if t.ticker == "SPY"), None)
        self.assertIsNotNone(spy_trade)
        # shares = dollar_amount / price
        expected_shares = float(spy_trade.dollar_amount) / 530.0
        self.assertAlmostEqual(float(spy_trade.share_quantity), expected_shares, places=6)
```

---

## Deployment Checklist

```bash
# 1. Apply the new migration
python manage.py makemigrations arcx_core
python manage.py migrate

# 2. Initialize the holdings table (Day 0: zero quantities)
python manage.py init_holdings

# 3. Run tests to verify nothing broke
python manage.py test tests.test_phase6
python manage.py test tests.test_phase5   # Regression check

# 4. Backfill: seed real historical holdings from the existing NAV history
#    (Optional — covered in Phase 7 broker integration)

# 5. Verify in Django shell
python manage.py shell
>>> from arcx_core.models import VaultAssetHolding
>>> VaultAssetHolding.objects.all()
# Should show: SPY, TLT, GLD with total_quantity=0
```

---

## What Phase 7 Unlocks (After Phase 6)

With holdings tracked as real share quantities:

| Feature | Why Phase 6 is Required |
|---|---|
| Alpaca paper trading | Broker needs share count, not dollar % |
| Stock split handling | Quantity stays correct when price halves |
| Per-user cost basis | Real FIFO/avg-cost P&L (not just % change) |
| Audit trail | "We owned 14.5 SPY shares on May 27" |
| Tax reporting | Capital gains require purchase price + quantity |
| Corporate actions | Dividends, rights issues tracked per share |

The `40/30/20/10` rule lives only in the Rebalancer now.
Everything else is quantity × live_price.
