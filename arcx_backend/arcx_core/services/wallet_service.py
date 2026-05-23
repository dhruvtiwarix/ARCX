"""
ARCX Wallet Service — Phase 3
--------------------------------
This is the bridge between:
  Phase 1 → domain/  (pure Python math, no framework)
  Phase 2 → models.py (PostgreSQL via Django ORM)
  Phase 3 → views/   (HTTP request handling)
 
The service layer is where business logic lives. Views are thin.
Views call services. Services talk to the DB and domain layer.
 
Why a separate service layer?
  If you put all logic in views, you can't:
    - Test it without HTTP requests
    - Reuse it from a Celery task
    - Reuse it from a management command
    - Reason about it clearly
 
  With a service layer:
    - Tests call service functions directly (no HTTP overhead)
    - Celery tasks call the same service functions
    - Views become 5 lines of "validate → call service → return response"
 
This is called the "Fat Services, Thin Views" pattern.
Standard in every serious Django codebase.
"""
 
import uuid
import logging
from decimal import Decimal
 
from django.db import transaction
 
from domain.oracle import MultiSourceOracle, OracleFailureException
from domain.valuation import ValuationEngine
from arcx_core.models import User, Wallet, Transaction, VaultSnapshot, NAVHistory
from arcx_core.exceptions import (
    InsufficientBalanceError,
    WalletFrozenError,
    KYCRequiredError,
    OracleUnavailableError,
)
 
logger = logging.getLogger("arcx.wallet")
 
 
# ─────────────────────────────────────────────────────────────────────────────
# KYC Daily Limits
# These enforce deposit/withdraw caps based on KYC tier.
# India's PMLA regulations require tiered limits.
# ─────────────────────────────────────────────────────────────────────────────
KYC_DAILY_LIMITS_INR = {
    "tier_1": Decimal("10000.00"),    # ₹10,000 / day — Basic KYC
    "tier_2": Decimal("100000.00"),   # ₹1,00,000 / day — Full KYC
    "tier_3": Decimal("9999999.99"),  # ₹99,99,999 / day — Accredited
}
 
 
class WalletService:
    """
    Handles all wallet mutations.
    Every method that changes money uses transaction.atomic() + select_for_update().
    """
 
    def __init__(self):
        self._oracle = MultiSourceOracle()
 
    # ── Public API ────────────────────────────────────────────────────────
 
    def get_wallet(self, user_id: str) -> Wallet:
        """Fetch a user's wallet. Read-only, no lock needed."""
        return Wallet.objects.select_related("user").get(
            user_id=user_id,
            deleted_at__isnull=True,
        )
 
    def deposit(self, user_id: str, amount_inr: Decimal) -> Transaction:
        """
        Convert INR → ARCX and credit user's wallet.
 
        Steps:
          1. Fetch live NAV from Oracle
          2. Calculate how many ARCX tokens ₹amount_inr buys
          3. Lock wallet row (select_for_update)
          4. Check KYC daily limit
          5. Credit balance + record transaction
          6. Return the transaction record
 
        Args:
            user_id:    ARCX User UUID
            amount_inr: Amount in INR to deposit (e.g., Decimal("5000.00"))
 
        Returns:
            Transaction record (status=completed)
        """
        # Step 1: Fetch live prices — do this BEFORE acquiring DB lock
        # (Oracle call takes ~1-2s; holding a DB lock during this is bad)
        prices = self._fetch_prices()
 
        # Step 2: Calculate how many ARCX tokens this INR buys
        nav_inr      = self._get_nav_inr(prices)
        arcx_to_mint = (amount_inr / nav_inr).quantize(Decimal("0.000000000000000001"))
 
        with transaction.atomic():
            # Step 3: Row-level lock on this wallet
            wallet = Wallet.objects.select_for_update().get(
                user_id=user_id,
                deleted_at__isnull=True,
            )
 
            if wallet.is_frozen:
                raise WalletFrozenError("Wallet is frozen. Contact support.")
 
            # Step 4: Enforce KYC daily limit
            self._check_daily_limit(wallet, amount_inr, "deposit")
 
            # Step 5: Update balance
            wallet.arcx_balance   += arcx_to_mint
            wallet.cost_basis_inr += amount_inr
            wallet.save(update_fields=["arcx_balance", "cost_basis_inr", "updated_at"])
 
            # Step 6: Record transaction
            tx = Transaction.objects.create(
                wallet          = wallet,
                idempotency_key = uuid.uuid4(),
                tx_type         = Transaction.TxType.DEPOSIT,
                amount_arcx     = arcx_to_mint,
                amount_inr      = amount_inr,
                nav_at_tx       = nav_inr,
                status          = Transaction.Status.COMPLETED,
            )
 
        logger.info(
            "DEPOSIT completed: user=%s amount_inr=%s arcx_minted=%s nav=%s tx=%s",
            user_id, amount_inr, arcx_to_mint, nav_inr, tx.id,
        )
        return tx
 
    def withdraw(self, user_id: str, amount_arcx: Decimal) -> Transaction:
        """
        Convert ARCX → INR and debit user's wallet.
 
        Steps:
          1. Fetch live NAV
          2. Calculate INR value of the ARCX being sold
          3. Lock wallet
          4. Check balance is sufficient
          5. Debit balance + record transaction
 
        Args:
            user_id:     ARCX User UUID
            amount_arcx: ARCX tokens to sell (e.g., Decimal("10.5"))
 
        Returns:
            Transaction record (status=completed)
        """
        prices  = self._fetch_prices()
        nav_inr = self._get_nav_inr(prices)
        inr_to_return = (amount_arcx * nav_inr).quantize(Decimal("0.0001"))
 
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
 
            # Proportionally reduce cost basis
            if wallet.arcx_balance > 0:
                ratio = amount_arcx / wallet.arcx_balance
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
 
        logger.info(
            "WITHDRAW completed: user=%s arcx_burned=%s inr_returned=%s nav=%s tx=%s",
            user_id, amount_arcx, inr_to_return, nav_inr, tx.id,
        )
        return tx
 
    def get_transaction_history(self, user_id: str, limit: int = 20) -> list:
        """Fetch last N transactions for a user's wallet."""
        return (
            Transaction.objects
            .filter(wallet__user_id=user_id)
            .select_related("wallet")
            .order_by("-created_at")[:limit]
        )
 
    # ── Private helpers ───────────────────────────────────────────────────
 
    def _fetch_prices(self):
        """Wrap oracle call with ARCX exception."""
        try:
            return self._oracle.fetch_prices()
        except OracleFailureException as e:
            logger.error("Oracle failure during wallet operation: %s", e)
            raise OracleUnavailableError(
                "Price data is temporarily unavailable. Please retry in a moment."
            )
 
    def _get_nav_inr(self, prices) -> Decimal:
        """
        Calculate current NAV from live prices.
        Uses the latest vault snapshot as the vault state source.
        Falls back to genesis configuration if no snapshot exists yet.
        """
        try:
            snapshot = VaultSnapshot.objects.latest("snapshot_date")
            engine = ValuationEngine(
                arcx_supply     = float(snapshot.arcx_supply),
                vault_value_usd = float(snapshot.total_value_usd),
            )
        except VaultSnapshot.DoesNotExist:
            # Day 0: no snapshots yet, bootstrap from genesis
            logger.warning("No vault snapshot found. Bootstrapping from genesis config.")
            engine = ValuationEngine.from_genesis(prices)
 
        state = engine.calculate_nav(prices)
        return Decimal(str(round(state.nav_inr, 4)))
 
    def _check_daily_limit(self, wallet: Wallet, amount_inr: Decimal, direction: str):
        """
        Enforce KYC tier daily transaction limits.
        Looks back at the last 24h of completed deposits/withdrawals.
        """
        from django.utils import timezone
        from datetime import timedelta
 
        kyc_status = wallet.user.kyc_status
        if kyc_status != User.KycStatus.APPROVED:
            raise KYCRequiredError("KYC approval required to transact.")
 
        # Find the user's highest approved KYC tier
        approved_kyc = wallet.user.kyc_records.filter(
            status="approved",
            deleted_at__isnull=True,
        ).order_by("-tier").first()
 
        tier_key = approved_kyc.tier if approved_kyc else "tier_1"
        daily_limit = KYC_DAILY_LIMITS_INR.get(tier_key, KYC_DAILY_LIMITS_INR["tier_1"])
 
        # Sum today's transactions of this type
        cutoff = timezone.now() - timedelta(hours=24)
        tx_type = Transaction.TxType.DEPOSIT if direction == "deposit" else Transaction.TxType.WITHDRAW
 
        today_total = (
            Transaction.objects
            .filter(
                wallet=wallet,
                tx_type=tx_type,
                status=Transaction.Status.COMPLETED,
                created_at__gte=cutoff,
            )
            .aggregate(total=models_Sum("amount_inr"))
        )["total"] or Decimal("0")
 
        if today_total + amount_inr > daily_limit:
            remaining = daily_limit - today_total
            raise KYCRequiredError(
                f"Daily {direction} limit for your KYC tier is ₹{daily_limit:,.2f}. "
                f"You have ₹{remaining:,.2f} remaining today. "
                f"Upgrade your KYC tier for a higher limit."
            )
 
 
# ── Import fix for Sum aggregate ─────────────────────────────────────────────
from django.db.models import Sum as models_Sum
 