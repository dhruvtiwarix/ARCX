"""
ARCX Transfer Service — Phase 3
----------------------------------
Peer-to-peer ARCX transfers. This is the "UPI of ARCX."
 
Key properties:
  - Zero fees (no SWIFT, no cut, no delay)
  - Real-time (same database, same transaction.atomic() block)
  - Atomic (both wallets update or neither does — no partial state)
 
The "real-time" claim in the ARCX pitch deck is technically true:
  A P2P transfer IS just two database row updates inside one DB transaction.
  No external settlement, no overnight batch, no correspondent banking.
  It commits in ~5ms.
 
Atomicity example:
  Sender has 100 ARCX. Receiver has 50 ARCX. Sending 20 ARCX.
 
  START TRANSACTION
    Lock sender   wallet → balance: 100
    Lock receiver wallet → balance: 50
    sender.balance   = 100 - 20 = 80  ← only in memory
    receiver.balance =  50 + 20 = 70  ← only in memory
    COMMIT → both writes hit disk simultaneously
  END TRANSACTION
 
  If anything fails between START and COMMIT:
    ROLLBACK → sender still 100, receiver still 50
    No money vanished, no money duplicated.
 
Two-wallet lock ordering (prevents deadlocks):
  If User A sends to B and User B sends to A simultaneously:
    Thread 1 locks A then tries to lock B
    Thread 2 locks B then tries to lock A
    → Deadlock! Both threads wait forever.
 
  Solution: Always lock wallets in UUID order.
    Thread 1: min(A,B) first, then max(A,B)
    Thread 2: min(A,B) first, then max(A,B)
    → Same order → no deadlock. One waits, one proceeds.
"""
 
import uuid
import logging
from decimal import Decimal
 
from django.db import transaction
 
from arcx_core.models import User, Wallet, Transaction
from arcx_core.exceptions import InsufficientBalanceError, WalletFrozenError
 
logger = logging.getLogger("arcx.transfer")
 
 
class TransferService:
 
    def transfer(
        self,
        sender_user_id: str,
        recipient_email: str,
        amount_arcx: Decimal,
    ) -> Transaction:
        """
        Transfer ARCX from sender to recipient.
 
        Args:
            sender_user_id:  UUID of the sending user
            recipient_email: Email of the recipient (looked up server-side)
            amount_arcx:     How many ARCX tokens to send
 
        Returns:
            The outgoing transaction record from the sender's perspective
        """
        # Resolve recipient
        recipient = User.objects.select_related("wallet").get(
            email=recipient_email,
            deleted_at__isnull=True,
            is_active=True,
        )
 
        if str(recipient.id) == str(sender_user_id):
            raise ValueError("Cannot transfer ARCX to yourself.")
 
        sender_wallet_id    = str(Wallet.objects.get(user_id=sender_user_id).id)
        recipient_wallet_id = str(recipient.wallet.id)
 
        # Determine lock order (smaller UUID first — prevents deadlocks)
        first_id, second_id = sorted([sender_wallet_id, recipient_wallet_id])
 
        with transaction.atomic():
            # Lock in deterministic order
            wallets = {
                str(w.id): w
                for w in Wallet.objects.select_for_update().filter(
                    id__in=[first_id, second_id],
                    deleted_at__isnull=True,
                )
            }
 
            sender_wallet    = wallets[sender_wallet_id]
            recipient_wallet = wallets[recipient_wallet_id]
 
            # Validation
            if sender_wallet.is_frozen:
                raise WalletFrozenError("Your wallet is frozen. Contact support.")
 
            if recipient_wallet.is_frozen:
                raise WalletFrozenError("Recipient wallet is frozen. Transfer not possible.")
 
            if sender_wallet.arcx_balance < amount_arcx:
                raise InsufficientBalanceError(
                    f"Insufficient balance. You have {sender_wallet.arcx_balance} ARCX, "
                    f"tried to send {amount_arcx} ARCX."
                )
 
            # Execute transfer
            sender_wallet.arcx_balance    -= amount_arcx
            recipient_wallet.arcx_balance += amount_arcx
 
            sender_wallet.save(update_fields=["arcx_balance", "updated_at"])
            recipient_wallet.save(update_fields=["arcx_balance", "updated_at"])
 
            # Record both legs of the transaction
            # Leg 1: Sender's outgoing record
            outgoing_tx = Transaction.objects.create(
                wallet                  = sender_wallet,
                idempotency_key         = uuid.uuid4(),
                tx_type                 = Transaction.TxType.TRANSFER,
                amount_arcx             = -amount_arcx,   # Negative = outgoing
                amount_inr              = Decimal("0"),   # No INR exchange in P2P
                nav_at_tx               = Decimal("0"),   # No NAV needed for P2P
                status                  = Transaction.Status.COMPLETED,
                counterparty_wallet     = recipient_wallet,
            )
 
            # Leg 2: Recipient's incoming record
            Transaction.objects.create(
                wallet                  = recipient_wallet,
                idempotency_key         = uuid.uuid4(),
                tx_type                 = Transaction.TxType.TRANSFER,
                amount_arcx             = amount_arcx,    # Positive = incoming
                amount_inr              = Decimal("0"),
                nav_at_tx               = Decimal("0"),
                status                  = Transaction.Status.COMPLETED,
                counterparty_wallet     = sender_wallet,
            )
 
        logger.info(
            "TRANSFER completed: sender=%s → recipient=%s amount_arcx=%s tx=%s",
            sender_user_id, recipient_email, amount_arcx, outgoing_tx.id,
        )
        return outgoing_tx
 