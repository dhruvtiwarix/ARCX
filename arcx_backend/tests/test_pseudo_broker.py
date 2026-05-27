"""
ARCX Phase 7 — Pseudo Broker Service Tests
--------------------------------------------
Verifies that the mock broker correctly translates RebalanceTrades
into physical ledger updates (VaultAssetHolding) and cash deductions (VaultSnapshot).
"""

from decimal import Decimal
from django.test import TestCase

from domain.rebalancer import RebalanceTrade
from arcx_core.models import VaultSnapshot, VaultAssetHolding
from arcx_core.services.pseudo_broker import PseudoBrokerService


class TestPseudoBrokerService(TestCase):
    def setUp(self):
        # Create a genesis snapshot with $10,000 cash
        self.snapshot = VaultSnapshot.objects.create(
            snapshot_date="2026-01-01",
            total_value_usd=Decimal("10000.00"),
            stock_value_usd=Decimal("0"),
            bond_value_usd=Decimal("0"),
            gold_value_usd=Decimal("0"),
            cash_value_usd=Decimal("10000.00"),
            arcx_supply=Decimal("100.0"),
            spy_twap=Decimal("500.00"),
            tlt_twap=Decimal("100.00"),
            gld_twap=Decimal("200.00"),
            usd_inr_rate=Decimal("83.00"),
        )

        # Create zero-quantity holdings (like init_holdings)
        self.spy = VaultAssetHolding.objects.create(asset_ticker="SPY", total_quantity=0, average_buy_price=0)
        self.tlt = VaultAssetHolding.objects.create(asset_ticker="TLT", total_quantity=0, average_buy_price=0)
        self.gld = VaultAssetHolding.objects.create(asset_ticker="GLD", total_quantity=0, average_buy_price=0)
        
        self.broker = PseudoBrokerService()

    def test_execute_buy_trades_deducts_cash_and_credits_shares(self):
        """Buying shares must deduct exact cash and increase exact quantity."""
        # Instruction: Buy 2 shares of SPY at $500 = $1,000
        # Instruction: Buy 5 shares of TLT at $100 = $500
        trades = [
            RebalanceTrade(action="BUY", ticker="SPY", share_quantity=2.0, execution_price=500.0, dollar_amount=1000.0, reason="test"),
            RebalanceTrade(action="BUY", ticker="TLT", share_quantity=5.0, execution_price=100.0, dollar_amount=500.0, reason="test"),
        ]

        self.broker.execute_trades(trades, self.snapshot)

        # Refresh from DB
        self.snapshot.refresh_from_db()
        self.spy.refresh_from_db()
        self.tlt.refresh_from_db()

        # Cash should be down by $1,500
        self.assertEqual(self.snapshot.cash_value_usd, Decimal("8500.00"))
        
        # Shares should be credited
        self.assertEqual(self.spy.total_quantity, Decimal("2.0"))
        self.assertEqual(self.spy.average_buy_price, Decimal("500.0000"))
        
        self.assertEqual(self.tlt.total_quantity, Decimal("5.0"))
        self.assertEqual(self.tlt.average_buy_price, Decimal("100.0000"))

    def test_execute_sell_trades_adds_cash_and_deducts_shares(self):
        """Selling shares must add cash and reduce quantity."""
        # Setup initial state: own 10 GLD
        self.gld.total_quantity = Decimal("10.0")
        self.gld.average_buy_price = Decimal("200.00")
        self.gld.save()

        # Instruction: Sell 3 shares of GLD at $210 = $630 cash back
        trades = [
            RebalanceTrade(action="SELL", ticker="GLD", share_quantity=3.0, execution_price=210.0, dollar_amount=630.0, reason="test"),
        ]

        self.broker.execute_trades(trades, self.snapshot)

        self.snapshot.refresh_from_db()
        self.gld.refresh_from_db()

        # Cash should go up by $630
        self.assertEqual(self.snapshot.cash_value_usd, Decimal("10630.00"))
        
        # Shares should be deducted (10 - 3 = 7)
        self.assertEqual(self.gld.total_quantity, Decimal("7.0"))
        
        # Average buy price does NOT change on sell!
        self.assertEqual(self.gld.average_buy_price, Decimal("200.0000"))

    def test_insufficient_cash_rolls_back_entire_transaction(self):
        """If we try to buy more than cash available, the whole batch fails."""
        # Instruction: Buy $12,000 of SPY (we only have $10,000)
        trades = [
            RebalanceTrade(action="BUY", ticker="GLD", share_quantity=1.0, execution_price=200.0, dollar_amount=200.0, reason="test"), # This would succeed
            RebalanceTrade(action="BUY", ticker="SPY", share_quantity=24.0, execution_price=500.0, dollar_amount=12000.0, reason="test"), # This fails
        ]

        with self.assertRaises(ValueError) as context:
            self.broker.execute_trades(trades, self.snapshot)

        self.assertIn("Insufficient cash", str(context.exception))

        self.snapshot.refresh_from_db()
        self.gld.refresh_from_db()
        self.spy.refresh_from_db()

        # Due to atomic transaction, the $200 GLD buy should have been rolled back
        self.assertEqual(self.snapshot.cash_value_usd, Decimal("10000.00"))
        self.assertEqual(self.gld.total_quantity, Decimal("0"))
        self.assertEqual(self.spy.total_quantity, Decimal("0"))
