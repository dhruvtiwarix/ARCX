"""
ARCX Valuation Engine
----------------------
The mathematical heart of ARCX.

Formula:
  NAV = (Total Value of all Assets in Vault) / (Total ARCX Tokens in Circulation)

Vault Allocation:
  40% → Global Stocks (SPY)
  30% → Bonds (TLT)
  20% → Gold (GLD)
  10% → Cash (USD)

All values are stored and calculated in USD internally.
Final output is converted to INR using live USD/INR rate.
"""

from dataclasses import dataclass
from domain.oracle import MarketPrices


# ── Vault Allocation Constants ──────────────────────────────────────────────
STOCK_WEIGHT = 0.40
BOND_WEIGHT  = 0.30
GOLD_WEIGHT  = 0.20
CASH_WEIGHT  = 0.10


@dataclass
class VaultState:
    """
    Represents the current state of the ARCX vault.
    All monetary values in USD unless suffixed with _inr.
    """
    total_vault_value_usd: float   # Total USD value of all assets
    stock_value_usd: float         # 40% slice
    bond_value_usd: float          # 30% slice
    gold_value_usd: float          # 20% slice
    cash_value_usd: float          # 10% slice
    arcx_supply: float             # Total ARCX tokens in circulation
    nav_usd: float                 # 1 ARCX = X USD
    nav_inr: float                 # 1 ARCX = X INR


@dataclass
class GenesisVault:
    """
    Day 0 configuration.
    The founder deposits an initial amount to bootstrap the protocol.
    This prevents the "divide by zero" crash on first launch.

    Genesis Peg: 1 ARCX = ₹100 on Day 0.
    """
    founder_deposit_inr: float = 100_000.0   # ₹1,00,000 founder deposit
    genesis_peg_inr: float = 100.0           # 1 ARCX = ₹100 on Day 0

    @property
    def initial_arcx_supply(self) -> float:
        """Tokens issued = founder deposit / genesis peg."""
        return self.founder_deposit_inr / self.genesis_peg_inr


class ValuationEngine:
    """
    Core NAV calculation engine.

    This class has ZERO knowledge of Django, PostgreSQL, or any framework.
    It takes prices in, returns vault state out. Pure math.
    This is intentional — it follows Clean Architecture principles.
    """

    def __init__(self, arcx_supply: float, vault_value_usd: float):
        """
        Args:
            arcx_supply:      Total ARCX tokens currently in circulation.
            vault_value_usd:  Total USD value of all assets in the vault.
        """
        if arcx_supply <= 0:
            raise ValueError("ARCX supply must be greater than zero.")
        if vault_value_usd <= 0:
            raise ValueError("Vault value must be greater than zero.")

        self.arcx_supply = arcx_supply
        self.vault_value_usd = vault_value_usd

    def calculate_nav(self, prices: MarketPrices) -> VaultState:
        """
        Calculates the current NAV (Net Asset Value) of 1 ARCX token.

        The vault_value_usd is broken down into 4 slices based on
        the 40/30/20/10 allocation weights. Then NAV is simply:

            NAV (USD) = Total Vault Value / ARCX Supply
            NAV (INR) = NAV (USD) * USD/INR rate
        """

        # ── Step 1: Break vault into 4 asset slices ──────────────────────
        stock_value = self.vault_value_usd * STOCK_WEIGHT
        bond_value  = self.vault_value_usd * BOND_WEIGHT
        gold_value  = self.vault_value_usd * GOLD_WEIGHT
        cash_value  = self.vault_value_usd * CASH_WEIGHT

        # ── Step 2: Calculate NAV in USD ──────────────────────────────────
        nav_usd = self.vault_value_usd / self.arcx_supply

        # ── Step 3: Convert NAV to INR using live Oracle rate ─────────────
        nav_inr = nav_usd * prices.usd_inr

        return VaultState(
            total_vault_value_usd = self.vault_value_usd,
            stock_value_usd       = stock_value,
            bond_value_usd        = bond_value,
            gold_value_usd        = gold_value,
            cash_value_usd        = cash_value,
            arcx_supply           = self.arcx_supply,
            nav_usd               = nav_usd,
            nav_inr               = nav_inr,
        )

    @classmethod
    def from_genesis(cls, prices: MarketPrices) -> "ValuationEngine":
        """
        Factory method for Day 0.
        Bootstraps the engine from the genesis configuration.
        Converts the founder's INR deposit to USD using live rate.
        """
        genesis = GenesisVault()

        # Convert founder INR deposit → USD
        founder_deposit_usd = genesis.founder_deposit_inr / prices.usd_inr

        return cls(
            arcx_supply     = genesis.initial_arcx_supply,
            vault_value_usd = founder_deposit_usd,
        )
