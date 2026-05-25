"""
ARCX Wallet Service — Phase 4 (Updated with Observability)
------------------------------------------------------------

What's new in Phase 4:
  - arcx_logger calls on every operation (success + failure)
  - duration_ms tracked per operation using time.monotonic()
  - @log_operation decorator on public methods
  - Oracle fetch duration logged separately

Every log entry can be correlated by user_id and tx_id.
If a user says "my deposit at 10:30 didn't work", you run:
  cat logs/arcx.log | python manage.py read_logs --event DEPOSIT_FAILED
"""

import uuid
import time
import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from domain.oracle import MultiSourceOracle, OracleFailureException
from domain.valuation import ValuationEngine
from arcx_core.models import User, Wallet, Transaction, VaultSnapshot
from arcx_core.exceptions import (
    InsufficientBalanceError,
    WalletFrozenError,
    KYCRequiredError,
    OracleUnavailableError,
)
from arcx_core.logger import arcx_logger, log_operation

logger = logging.getLogger("arcx.wallet_service")

KYC_DAILY_LIMITS_INR = {
    "tier_1": Decimal("10000.00"),
    "tier_2": Decimal("100000.00"),
    "tier_3": Decimal("9999999.99"),
}


class WalletService:

    def __init__(self):
        self._oracle = MultiSourceOracle()

    def get_wallet(self, user_id: str) -> Wallet:
        return Wallet.objects.select_related("user").get(
            user_id=user_id,
            deleted_at__isnull=True,
        )

    @log_operation("deposit")
    def deposit(self, user_id: str, amount_inr: Decimal) -> Transaction:
        """
        Convert INR to ARCX and credit wallet.
        Logs DEPOSIT_COMPLETED or DEPOSIT_FAILED with full context.
        """
        op_start = time.monotonic()

        # Oracle fetch — timed separately so we know if slowness is oracle vs DB
        try:
            oracle_start = time.monotonic()
            prices       = self._oracle.fetch_prices()
            oracle_ms    = int((time.monotonic() - oracle_start) * 1000)
            nav_inr      = self._get_nav_inr(prices)

            arcx_logger.oracle_fetch(
                sources_used = prices.sources_used,
                spy          = prices.spy,
                tlt          = prices.tlt,
                gld          = prices.gld,
                usd_inr      = prices.usd_inr,
                nav_inr      = float(nav_inr),
                duration_ms  = oracle_ms,
            )
        except OracleFailureException as e:
            arcx_logger.oracle_failure(
                error              = str(e),
                sources_attempted  = ["Yahoo Finance", "Alpha Vantage", "Twelve Data"],
            )
            raise OracleUnavailableError(
                "Price data is temporarily unavailable. Please retry in a moment."
            )

        arcx_to_mint = (amount_inr / nav_inr).quantize(Decimal("0.000000000000000001"))

        try:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(
                    user_id=user_id,
                    deleted_at__isnull=True,
                )

                if wallet.is_frozen:
                    raise WalletFrozenError("Wallet is frozen. Contact support.")

                self._check_daily_limit(wallet, amount_inr, "deposit")

                wallet.arcx_balance   += arcx_to_mint
                wallet.cost_basis_inr += amount_inr
                wallet.save(update_fields=["arcx_balance", "cost_basis_inr", "updated_at"])

                tx = Transaction.objects.create(
                    wallet          = wallet,
                    idempotency_key = uuid.uuid4(),
                    tx_type         = Transaction.TxType.DEPOSIT,
                    amount_arcx     = arcx_to_mint,
                    amount_inr      = amount_inr,
                    nav_at_tx       = nav_inr,
                    status          = Transaction.Status.COMPLETED,
                )

            duration_ms = int((time.monotonic() - op_start) * 1000)
            arcx_logger.deposit_completed(
                user_id     = user_id,
                amount_inr  = amount_inr,
                arcx_minted = arcx_to_mint,
                nav_inr     = nav_inr,
                tx_id       = str(tx.id),
                duration_ms = duration_ms,
            )
            return tx

        except (WalletFrozenError, KYCRequiredError, OracleUnavailableError) as exc:
            arcx_logger.deposit_failed(
                user_id    = user_id,
                amount_inr = amount_inr,
                error      = str(exc),
                error_code = getattr(exc, "code", "UNKNOWN"),
            )
            raise

    @log_operation("withdraw")
    def withdraw(self, user_id: str, amount_arcx: Decimal) -> Transaction:
        """
        Convert ARCX to INR and debit wallet.
        Logs WITHDRAW_COMPLETED or WITHDRAW_FAILED.
        """
        op_start = time.monotonic()

        try:
            prices  = self._oracle.fetch_prices()
            nav_inr = self._get_nav_inr(prices)
        except OracleFailureException as e:
            arcx_logger.oracle_failure(str(e), [])
            raise OracleUnavailableError("Price data unavailable.")

        inr_to_return = (amount_arcx * nav_inr).quantize(Decimal("0.0001"))

        try:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(
                    user_id=user_id,
                    deleted_at__isnull=True,
                )

                if wallet.is_frozen:
                    raise WalletFrozenError("Wallet is frozen. Contact support.")

                if wallet.arcx_balance < amount_arcx:
                    raise InsufficientBalanceError(
                        f"Insufficient balance. You have {wallet.arcx_balance} ARCX, "
                        f"tried to withdraw {amount_arcx} ARCX."
                    )

                if wallet.arcx_balance > 0:
                    ratio                = amount_arcx / wallet.arcx_balance
                    cost_basis_reduction = wallet.cost_basis_inr * ratio
                else:
                    cost_basis_reduction = Decimal("0")

                wallet.arcx_balance   -= amount_arcx
                wallet.cost_basis_inr -= cost_basis_reduction
                wallet.save(update_fields=["arcx_balance", "cost_basis_inr", "updated_at"])

                tx = Transaction.objects.create(
                    wallet          = wallet,
                    idempotency_key = uuid.uuid4(),
                    tx_type         = Transaction.TxType.WITHDRAW,
                    amount_arcx     = amount_arcx,
                    amount_inr      = inr_to_return,
                    nav_at_tx       = nav_inr,
                    status          = Transaction.Status.COMPLETED,
                )

            duration_ms = int((time.monotonic() - op_start) * 1000)
            arcx_logger.withdraw_completed(
                user_id      = user_id,
                amount_arcx  = amount_arcx,
                inr_returned = inr_to_return,
                nav_inr      = nav_inr,
                tx_id        = str(tx.id),
                duration_ms  = duration_ms,
            )
            return tx

        except (WalletFrozenError, InsufficientBalanceError, KYCRequiredError) as exc:
            arcx_logger.withdraw_failed(
                user_id     = user_id,
                amount_arcx = amount_arcx,
                error       = str(exc),
                error_code  = getattr(exc, "code", "UNKNOWN"),
            )
            raise

    def get_transaction_history(self, user_id: str, limit: int = 20) -> list:
        return (
            Transaction.objects
            .filter(wallet__user_id=user_id)
            .select_related("wallet")
            .order_by("-created_at")[:limit]
        )

    def _get_nav_inr(self, prices) -> Decimal:
        try:
            snapshot = VaultSnapshot.objects.latest("snapshot_date")
            engine   = ValuationEngine(
                arcx_supply     = float(snapshot.arcx_supply),
                vault_value_usd = float(snapshot.total_value_usd),
            )
        except VaultSnapshot.DoesNotExist:
            logger.warning("No vault snapshot found. Bootstrapping from genesis config.")
            engine = ValuationEngine.from_genesis(prices)

        state = engine.calculate_nav(prices)
        return Decimal(str(round(state.nav_inr, 4)))

    def _fetch_prices(self):
        """Fetch current prices from the Oracle."""
        return self._oracle.fetch_prices()

    def _check_daily_limit(self, wallet: Wallet, amount_inr: Decimal, direction: str):
        from django.utils import timezone
        from datetime import timedelta

        if wallet.user.kyc_status != User.KycStatus.APPROVED:
            raise KYCRequiredError("KYC approval required to transact.")

        approved_kyc = wallet.user.kyc_records.filter(
            status="approved",
            deleted_at__isnull=True,
        ).order_by("-tier").first()

        tier_key    = approved_kyc.tier if approved_kyc else "tier_1"
        daily_limit = KYC_DAILY_LIMITS_INR.get(tier_key, KYC_DAILY_LIMITS_INR["tier_1"])

        cutoff  = timezone.now() - timedelta(hours=24)
        tx_type = Transaction.TxType.DEPOSIT if direction == "deposit" else Transaction.TxType.WITHDRAW

        today_total = (
            Transaction.objects
            .filter(
                wallet=wallet,
                tx_type=tx_type,
                status=Transaction.Status.COMPLETED,
                created_at__gte=cutoff,
            )
            .aggregate(total=Sum("amount_inr"))
        )["total"] or Decimal("0")

        if today_total + amount_inr > daily_limit:
            remaining = daily_limit - today_total
            raise KYCRequiredError(
                f"Daily {direction} limit for your KYC tier is Rs.{daily_limit:,.2f}. "
                f"You have Rs.{remaining:,.2f} remaining today."
            )