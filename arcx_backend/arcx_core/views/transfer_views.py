"""
ARCX Transfer View — Phase 3
------------------------------
Endpoint:
  POST /api/v1/transfer/
  Headers: Idempotency-Key: <uuid>
 
Body:
  {
    "to_user_email": "friend@example.com",
    "amount_arcx":   "10.5",
    "note":          "Splitting dinner"      ← optional
  }
 
Response:
  {
    "transaction_id":     "...",
    "amount_sent":        "10.5",
    "recipient_email":    "friend@example.com",
    "new_balance":        "89.5",
    "fee":                "0.00"
  }
 
The fee is always 0.00. This is a feature, not an oversight.
SWIFT charges $25-50 and takes 3-5 days.
ARCX charges ₹0 and takes <100ms.
This is the headline feature. Make it visible in the response.
"""
 
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
 
from arcx_core.permissions import IsKYCApproved, IsWalletActive, IsCircuitBreakerClear
from arcx_core.serializers import TransferRequestSerializer
from arcx_core.services.transfer_service import TransferService
from arcx_core.services.wallet_service import WalletService
 
logger = logging.getLogger("arcx.views.transfer")
 
 
def _user_id(request) -> str:
    return request.user.username
 
 
class TransferView(APIView):
    """
    POST /api/v1/transfer/
 
    Zero-fee, real-time ARCX transfer between any two ARCX users.
    Both wallets update atomically in one DB transaction.
    """
    permission_classes = [IsAuthenticated, IsKYCApproved, IsWalletActive, IsCircuitBreakerClear]
 
    def post(self, request):
        serializer = TransferRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
 
        data = serializer.validated_data
 
        transfer_service = TransferService()
        tx = transfer_service.transfer(
            sender_user_id  = _user_id(request),
            recipient_email = data["to_user_email"],
            amount_arcx     = data["amount_arcx"],
        )
 
        wallet_service = WalletService()
        wallet         = wallet_service.get_wallet(_user_id(request))
 
        return Response(
            {
                "transaction_id":  str(tx.id),
                "amount_sent":     str(data["amount_arcx"]),
                "recipient_email": data["to_user_email"],
                "new_balance":     str(wallet.arcx_balance),
                "fee":             "0.00",
                "note":            data.get("note", ""),
            },
            status=status.HTTP_201_CREATED,
        )
 