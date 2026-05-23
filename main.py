"""
ARCX — Phase 1B Entry Point
------------------------------
Full pipeline: Oracle → Valuation → Dividend → Rebalancer → NAV Report

Run: python main.py
"""

from colorama import init, Fore, Style
from domain.oracle import MultiSourceOracle
from domain.valuation import ValuationEngine
from domain.dividend import DividendAccrualEngine
from domain.rebalancer import DriftRebalancer
from domain.nav_report import NAVReportGenerator

init(autoreset=True)


def print_header():
    print(Fore.CYAN + "=" * 55)
    print(Fore.CYAN + "   ARCX Valuation Engine — Phase 1B")
    print(Fore.CYAN + "   Multi-Source Oracle  |  TWAP  |  Dividend Accrual")
    print(Fore.CYAN + "=" * 55)


def print_nav(state, accrual, rebalance):
    print(Fore.YELLOW + "\n── VAULT STATE ──────────────────────────────────────")
    print(f"  Total Vault    : ${state.total_vault_value_usd:,.3f} USD")
    print(f"  ARCX Supply    : {state.arcx_supply:,.0f} tokens")
    print(f"  Stocks (40%)   : ${state.stock_value_usd:,.3f}")
    print(f"  Bonds  (30%)   : ${state.bond_value_usd:,.3f}")
    print(f"  Gold   (20%)   : ${state.gold_value_usd:,.3f}")
    print(f"  Cash   (10%)   : ${state.cash_value_usd:,.3f}")

    print(Fore.YELLOW + "\n── TONIGHT'S DIVIDEND ACCRUAL ───────────────────────")
    print(f"  Stock Yield    : ${accrual.stock_yield_usd:.6f}")
    print(f"  Bond Yield     : ${accrual.bond_yield_usd:.6f}")
    print(f"  Cash Yield     : ${accrual.cash_yield_usd:.6f}")
    print(f"  Total Yield    : Rs.{accrual.total_yield_inr:.4f}")
    print(Fore.GREEN + f"  Per ARCX Token : +Rs.{accrual.yield_per_arcx_inr:.6f} tonight")

    print(Fore.YELLOW + "\n── REBALANCING STATUS ───────────────────────────────")
    if rebalance.rebalance_needed:
        print(Fore.RED + f"  WARNING: Rebalance needed. Total drift: {rebalance.total_drift*100:.3f}%")
        for trade in rebalance.trades:
            print(f"  {trade.action} {trade.asset.upper()}: ${trade.amount_usd:,.3f}")
    else:
        print(Fore.GREEN + f"  OK: All assets within tolerance. Drift: {rebalance.total_drift*100:.3f}%")

    print(Fore.YELLOW + "\n── FINAL NAV ────────────────────────────────────────")
    print(f"  1 ARCX = ${state.nav_usd:.4f} USD")
    print(Fore.GREEN + Style.BRIGHT + f"  1 ARCX = Rs.{state.nav_inr:.3f} INR")
    print(Fore.CYAN + "=" * 55)


def main():
    print_header()

    # 1. Fetch prices (multi-source TWAP + median)
    oracle = MultiSourceOracle()
    prices = oracle.fetch_prices()

    # 2. Bootstrap valuation engine
    print(Fore.CYAN + "\n  [Engine] Bootstrapping from Genesis...")
    engine = ValuationEngine.from_genesis(prices)
    state  = engine.calculate_nav(prices)

    # 3. Calculate today's dividend accrual
    accrual_engine = DividendAccrualEngine()
    accrual = accrual_engine.accrue_daily_yield(
        vault_value_usd = engine.vault_value_usd,
        arcx_supply     = engine.arcx_supply,
        prices          = prices,
    )

    # 4. Check for drift and generate rebalance trades
    rebalancer = DriftRebalancer()
    rebalance  = rebalancer.analyze(
        vault_value_usd = state.total_vault_value_usd,
        stock_value_usd = state.stock_value_usd,
        bond_value_usd  = state.bond_value_usd,
        gold_value_usd  = state.gold_value_usd,
        cash_value_usd  = state.cash_value_usd,
    )

    # 5. Print results
    print_nav(state, accrual, rebalance)

    # 6. Generate and save NAV report with SHA256 hash
    reporter = NAVReportGenerator()
    reporter.generate(prices, state, accrual, rebalance)


if __name__ == "__main__":
    main()
 