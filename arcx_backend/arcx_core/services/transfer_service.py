"""
ARCX Transfer Service — Phase 4 (Updated with Observability)
--------------------------------------------------------------

What's new: arcx_logger on success + failure, duration_ms tracking.
"""

import uuid
import time
import logging
from decimal import Decimal

from django.db import transaction

from arcx_core.models import User, Wallet, Transaction
from arcx_core.exceptions import InsufficientBalanceError, WalletFrozenError
from arcx_core.logger import arcx_logger, log_operation

logger = logging.getLogger("arcx.transfer_service")


class TransferService:

    @log_operation("transfer")
    def transfer(
        self,
        sender_user_id: str,
        recipient_email: str,
        amount_arcx: Decimal,
    ) -> Transaction:
        """
        Atomic P2P ARCX transfer. Logs TRANSFER_COMPLETED or TRANSFER_FAILED.
        """
        op_start = time.monotonic()

        recipient = User.objects.select_related("wallet").get(
            email=recipient_email,
            deleted_at__isnull=True,
            is_active=True,
        )

        if str(recipient.id) == str(sender_user_id):
            raise ValueError("Cannot transfer ARCX to yourself.")

        sender_wallet_id    = str(Wallet.objects.get(user_id=sender_user_id).id)
        recipient_wallet_id = str(recipient.wallet.id)

        # Lock in deterministic UUID order to prevent deadlocks
        first_id, second_id = sorted([sender_wallet_id, recipient_wallet_id])

        try:
            with transaction.atomic():
                wallets = {
                    str(w.id): w
                    for w in Wallet.objects.select_for_update().filter(
                        id__in=[first_id, second_id],
                        deleted_at__isnull=True,
                    )
                }

                sender_wallet    = wallets[sender_wallet_id]
                recipient_wallet = wallets[recipient_wallet_id]

                if sender_wallet.is_frozen:
                    raise WalletFrozenError("Your wallet is frozen. Contact support.")

                if recipient_wallet.is_frozen:
                    raise WalletFrozenError("Recipient wallet is frozen. Transfer not possible.")

                if sender_wallet.arcx_balance < amount_arcx:
                    raise InsufficientBalanceError(
                        f"Insufficient balance. You have {sender_wallet.arcx_balance} ARCX, "
                        f"tried to send {amount_arcx} ARCX."
                    )

                sender_wallet.arcx_balance    -= amount_arcx
                recipient_wallet.arcx_balance += amount_arcx

                sender_wallet.save(update_fields=["arcx_balance", "updated_at"])
                recipient_wallet.save(update_fields=["arcx_balance", "updated_at"])

                outgoing_tx = Transaction.objects.create(
                    wallet                = sender_wallet,
                    idempotency_key       = uuid.uuid4(),
                    tx_type               = Transaction.TxType.TRANSFER,
                    amount_arcx           = -amount_arcx,
                    amount_inr            = Decimal("0"),
                    nav_at_tx             = Decimal("0"),
                    status                = Transaction.Status.COMPLETED,
                    counterparty_wallet   = recipient_wallet,
                )

                Transaction.objects.create(
                    wallet                = recipient_wallet,
                    idempotency_key       = uuid.uuid4(),
                    tx_type               = Transaction.TxType.TRANSFER,
                    amount_arcx           = amount_arcx,
                    amount_inr            = Decimal("0"),
                    nav_at_tx             = Decimal("0"),
                    status                = Transaction.Status.COMPLETED,
                    counterparty_wallet   = sender_wallet,
                )

            duration_ms = int((time.monotonic() - op_start) * 1000)
            arcx_logger.transfer_completed(
                sender_id       = sender_user_id,
                recipient_email = recipient_email,
                amount_arcx     = amount_arcx,
                tx_id           = str(outgoing_tx.id),
                duration_ms     = duration_ms,
            )
            return outgoing_tx

        except (WalletFrozenError, InsufficientBalanceError) as exc:
            arcx_logger.transfer_failed(
                sender_id       = sender_user_id,
                recipient_email = recipient_email,
                amount_arcx     = amount_arcx,
                error           = str(exc),
            )
            raise