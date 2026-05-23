"""
ARCX NAV Report Generator — Phase 1B
---------------------------------------
Every real fund publishes a daily NAV report.
This is your legal protection, your transparency proof, and your audit trail.

What Gets Saved:
  - All price sources and their individual TWAP readings
  - Final median price per asset
  - Full vault breakdown (40/30/20/10 values)
  - Daily dividend accrual amount
  - Rebalance status (needed or not)
  - Final NAV in USD and INR
  - SHA256 hash of the entire report (tamper-proof)

Why SHA256 Hash:
  If someone claims "your NAV was wrong on May 20th," you can prove
  your report hasn't been altered since it was generated.
  hash(report_data) at generation time == hash(report_data) today → untampered.

In Phase 3 (Django), this report will be:
  1. Saved to PostgreSQL (nav_reports table)
  2. Published to an API endpoint (/api/v1/nav/daily/)
  3. Optionally stored on IPFS for full decentralization
"""

import json
import hashlib
import os
from dataclasses import asdict
from datetime import datetime
from arcx_backend.domain.oracle import MarketPrices
from arcx_backend.domain.valuation import VaultState
from arcx_backend.domain.dividend import DailyAccrualResult, DividendAccrualEngine
from arcx_backend.domain.rebalancer import RebalanceReport, DriftRebalancer

REPORTS_DIR = "reports"


class NAVReportGenerator:
    """
    Generates, signs, and saves the daily NAV report.
    This is the official record of ARCX's value on any given day.
    """

    def generate(
            self,
            prices: MarketPrices,
            vault_state: VaultState,
            accrual: DailyAccrualResult,
            rebalance: RebalanceReport,
    ) -> dict:
        """
        Builds the complete NAV report as a dictionary.
        Adds a SHA256 hash for tamper detection.
        Saves to reports/YYYY-MM-DD.json
        """

        # ── Build the report payload ──────────────────────────────────────
        report = {
            "arcx_nav_report": {
                "version": "1.0",
                "generated_at": prices.fetched_at.isoformat(),
                "date": prices.fetched_at.strftime("%Y-%m-%d"),
            },

            "oracle": {
                "sources_used": prices.sources_used,
                "prices": {
                    "SPY": {
                        "readings": prices.spy_readings,
                        "median_twap": prices.spy,
                    },
                    "TLT": {
                        "readings": prices.tlt_readings,
                        "median_twap": prices.tlt,
                    },
                    "GLD": {
                        "readings": prices.gld_readings,
                        "median_twap": prices.gld,
                    },
                    "USD_INR": prices.usd_inr,
                },
            },

            "vault": {
                "total_value_usd": vault_state.total_vault_value_usd,
                "arcx_supply": vault_state.arcx_supply,
                "allocation": {
                    "stocks_usd": vault_state.stock_value_usd,
                    "bonds_usd": vault_state.bond_value_usd,
                    "gold_usd": vault_state.gold_value_usd,
                    "cash_usd": vault_state.cash_value_usd,
                },
            },

            "dividend_accrual": {
                "stock_yield_usd": accrual.stock_yield_usd,
                "bond_yield_usd": accrual.bond_yield_usd,
                "gold_yield_usd": accrual.gold_yield_usd,
                "cash_yield_usd": accrual.cash_yield_usd,
                "total_yield_usd": accrual.total_yield_usd,
                "total_yield_inr": accrual.total_yield_inr,
                "yield_per_arcx_inr": accrual.yield_per_arcx_inr,
            },

            "rebalancing": {
                "rebalance_needed": rebalance.rebalance_needed,
                "total_drift": rebalance.total_drift,
                "trades_required": len(rebalance.trades),
                "trades": [
                    {
                        "asset": t.asset,
                        "action": t.action,
                        "amount_usd": t.amount_usd,
                        "reason": t.reason,
                    }
                    for t in rebalance.trades
                ],
            },

            "nav": {
                "nav_usd": vault_state.nav_usd,
                "nav_inr": vault_state.nav_inr,
            },
        }

        # ── SHA256 Signature ──────────────────────────────────────────────
        report_json = json.dumps(report, sort_keys=True)
        report_hash = hashlib.sha256(report_json.encode()).hexdigest()
        report["signature"] = {
            "algorithm": "SHA256",
            "hash": report_hash,
            "note": "Hash computed over entire report excluding this signature block.",
        }

        # ── Save to disk ──────────────────────────────────────────────────
        self._save(report, prices.fetched_at)
        return report

    def _save(self, report: dict, timestamp: datetime):
        """Saves the report to reports/YYYY-MM-DD_HH-MM-SS.json"""
        os.makedirs(REPORTS_DIR, exist_ok=True)
        filename = timestamp.strftime("%Y-%m-%d_%H-%M-%S") + ".json"
        filepath = os.path.join(REPORTS_DIR, filename)
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n  [Report] Saved: {filepath}")
        print(f"  [Report] Hash:  {report['signature']['hash'][:16]}...")
