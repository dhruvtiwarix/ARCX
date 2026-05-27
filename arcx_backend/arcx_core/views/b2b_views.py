import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, inline_serializer
from drf_spectacular.types import OpenApiTypes

from arcx_core.permissions import IsKYCApproved, IsWalletActive, IsCircuitBreakerClear
from arcx_core.models import WebhookEndpoint
from arcx_core.services.b2b_service import B2BService
from arcx_core.tasks.b2b_tasks import process_async_transfer_task

logger = logging.getLogger("arcx.views.b2b")

# --- Serializers ---

class SetPinRequestSerializer(drf_serializers.Serializer):
    current_pin = drf_serializers.CharField(max_length=6, min_length=6, required=False, help_text="Current 6-digit numeric PIN (required if updating)")
    pin = drf_serializers.CharField(max_length=6, min_length=6, help_text="New 6-digit numeric PIN")

class B2BTransferRequestSerializer(drf_serializers.Serializer):
    alias = drf_serializers.CharField(help_text="Recipient's Business Alias (e.g., vendorA@arcx)")
    amount_arcx = drf_serializers.DecimalField(max_digits=28, decimal_places=18)
    pin = drf_serializers.CharField(max_length=6, min_length=6, help_text="Your 6-digit transaction PIN")

class WebhookConfigRequestSerializer(drf_serializers.Serializer):
    url = drf_serializers.URLField(help_text="The HTTPS URL where you want to receive webhooks")
    secret_key = drf_serializers.CharField(max_length=128, help_text="Secret key for payload verification")

# --- Views ---

class SetTransactionPinView(APIView):
    """
    POST /api/v1/b2b/set-pin/
    Initializes or resets the user's 6-digit transaction PIN.
    """
    permission_classes = [IsAuthenticated, IsWalletActive]

    @extend_schema(
        tags=["B2B"],
        summary="Set or reset transaction PIN",
        request=SetPinRequestSerializer,
        responses={200: inline_serializer("SetPinSuccess", {"message": drf_serializers.CharField()})}
    )
    def post(self, request):
        serializer = SetPinRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        current_pin = serializer.validated_data.get("current_pin")
        new_pin = serializer.validated_data["pin"]
        
        # If a PIN is already set, validate the current PIN
        if request.user.wallet.transaction_pin:
            if not current_pin:
                return Response(
                    {"error": "current_pin is required when updating an existing PIN.", "code": "CURRENT_PIN_REQUIRED"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                B2BService.validate_transaction_pin(request.user, current_pin)
            except Exception as e:
                return Response(
                    {"error": "Incorrect current PIN.", "code": "INCORRECT_CURRENT_PIN"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        B2BService.set_transaction_pin(request.user, new_pin)
        
        return Response({"message": "Transaction PIN set successfully."}, status=status.HTTP_200_OK)


class B2BTransferView(APIView):
    """
    POST /api/v1/b2b/transfer/
    Asynchronous, PIN-protected B2B transfer endpoint.
    Returns 202 Accepted instantly.
    """
    permission_classes = [IsAuthenticated, IsKYCApproved, IsWalletActive, IsCircuitBreakerClear]

    @extend_schema(
        tags=["B2B"],
        summary="Async B2B Transfer (UPI Style)",
        request=B2BTransferRequestSerializer,
        parameters=[
            OpenApiParameter(name="Idempotency-Key", location=OpenApiParameter.HEADER, required=True, type=OpenApiTypes.UUID),
        ],
        responses={202: inline_serializer("B2BTransferAccepted", {"status": drf_serializers.CharField(), "message": drf_serializers.CharField()})}
    )
    def post(self, request):
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response({"error": "Idempotency-Key header is required."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = B2BTransferRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 1. Validate PIN
        B2BService.validate_transaction_pin(request.user, data["pin"])

        # 2. Resolve Alias to Email
        recipient_email = B2BService.resolve_alias_to_email(data["alias"])

        # 3. Dispatch to Celery (The "Switch")
        process_async_transfer_task.delay(
            sender_user_id=request.user.username,
            recipient_email=recipient_email,
            amount_arcx=str(data["amount_arcx"]),
            idempotency_key=idempotency_key
        )

        # 4. Return Instant 202 Accepted
        return Response({
            "status": "Accepted",
            "message": "Transfer request received and is being processed asynchronously."
        }, status=status.HTTP_202_ACCEPTED)


class WebhookConfigView(APIView):
    """
    POST /api/v1/b2b/webhooks/
    Registers a webhook URL for real-time B2B notifications.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["B2B"],
        summary="Configure Webhook Endpoint",
        request=WebhookConfigRequestSerializer,
        responses={200: inline_serializer("WebhookConfigSuccess", {"message": drf_serializers.CharField()})}
    )
    def post(self, request):
        serializer = WebhookConfigRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        endpoint, created = WebhookEndpoint.objects.update_or_create(
            user=request.user,
            defaults={
                "url": data["url"],
                "secret_key": data["secret_key"],
                "is_active": True
            }
        )
        
        msg = "Webhook endpoint created." if created else "Webhook endpoint updated."
        return Response({"message": msg}, status=status.HTTP_200_OK)
