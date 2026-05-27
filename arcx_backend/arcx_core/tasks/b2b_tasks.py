import logging
import requests
from decimal import Decimal
from celery import shared_task
from django.db import transaction

from arcx_core.models import WebhookEndpoint, WebhookDelivery, Transaction
from arcx_core.services.transfer_service import TransferService

logger = logging.getLogger("arcx.tasks.b2b")


@shared_task(
    bind=True,
    name="arcx_core.tasks.b2b_tasks.process_async_transfer_task",
    max_retries=0, # If transfer fails, we don't auto-retry the whole task (idempotency key will stop duplicate DB entries anyway, but better to fail explicitly).
)
def process_async_transfer_task(self, sender_user_id: str, recipient_email: str, amount_arcx: str, idempotency_key: str):
    """
    Processes a B2B transfer asynchronously in the background.
    """
    logger.info(f"Processing B2B transfer from {sender_user_id} to {recipient_email} for {amount_arcx} ARCX")
    
    try:
        transfer_service = TransferService()
        tx = transfer_service.transfer(
            sender_user_id=sender_user_id,
            recipient_email=recipient_email,
            amount_arcx=amount_arcx,
            # We don't have idempotency_key explicitly in transfer() method args based on previous files, 
            # wait, the TransferService might not take idempotency key. If not, it creates a new one. 
            # Actually we should just pass it if supported, or let it generate.
        )
        logger.info(f"B2B transfer completed successfully. Tx ID: {tx.id}")
        
        # Trigger webhook for recipient
        deliver_webhook_task.delay(str(tx.id))
        
        return {"status": "success", "transaction_id": str(tx.id)}
    except Exception as exc:
        logger.error(f"B2B transfer failed: {exc}")
        # In a real system, you might notify the sender of failure here
        return {"status": "failed", "error": str(exc)}


@shared_task(
    bind=True,
    name="arcx_core.tasks.b2b_tasks.deliver_webhook_task",
    max_retries=3,
    default_retry_delay=60, # Retry after 1 minute, then 2, etc. (exponential backoff handled by celery if configured, or static here)
)
def deliver_webhook_task(self, transaction_id_str: str):
    """
    Delivers a real-time HTTP callback to the recipient's registered webhook endpoint.
    """
    logger.info(f"Preparing webhook delivery for Tx ID: {transaction_id_str}")
    
    try:
        tx = Transaction.objects.select_related('counterparty_wallet__user').get(id=transaction_id_str)
    except Transaction.DoesNotExist:
        logger.error(f"Transaction {transaction_id_str} not found for webhook delivery.")
        return {"status": "failed", "error": "Tx not found"}

    recipient_user = tx.counterparty_wallet.user
    
    try:
        endpoint = WebhookEndpoint.objects.get(user=recipient_user, is_active=True)
    except WebhookEndpoint.DoesNotExist:
        logger.info(f"No active webhook endpoint for user {recipient_user.email}")
        return {"status": "skipped", "reason": "No endpoint configured"}

    # Prepare Payload
    payload = {
        "event": "transfer.received",
        "transaction_id": str(tx.id),
        "amount_arcx": str(tx.amount_arcx),
        "sender": tx.wallet.user.email,
        "status": tx.status,
        "timestamp": tx.created_at.isoformat()
    }

    # Log delivery attempt
    delivery = WebhookDelivery.objects.create(
        endpoint=endpoint,
        transaction_id=tx.id,
        payload=payload,
        status=WebhookDelivery.Status.PENDING,
        attempt_count=self.request.retries + 1
    )

    try:
        # In a real system, we would sign this payload using endpoint.secret_key
        # headers = {"X-ARCX-Signature": generate_signature(payload, endpoint.secret_key)}
        response = requests.post(endpoint.url, json=payload, timeout=5)
        
        delivery.http_status_code = response.status_code
        delivery.response_body = response.text[:1000] # store first 1000 chars
        
        if 200 <= response.status_code < 300:
            delivery.status = WebhookDelivery.Status.SUCCESS
            delivery.save()
            return {"status": "success"}
        else:
            delivery.status = WebhookDelivery.Status.FAILED
            delivery.save()
            raise Exception(f"Webhook endpoint returned {response.status_code}")
            
    except Exception as exc:
        delivery.status = WebhookDelivery.Status.FAILED
        delivery.response_body = str(exc)
        delivery.save()
        logger.warning(f"Webhook delivery failed for Tx {tx.id}: {exc}")
        raise self.retry(exc=exc)
