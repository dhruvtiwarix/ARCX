"""
ARCX Wallet Views — Phase 3
------------------------------
These are thin views. The pattern is always:
  1. Deserialize + validate input
  2. Call service
  3. Serialize + return output
 
No business logic here. The view's only job is HTTP.
 
Endpoints:
  GET  /api/v1/wallet/          → wallet balance + unrealized P&L
  POST /api/v1/wallet/deposit   → INR → ARCX
  POST /api/v1/wallet/withdraw  → ARCX → INR
  GET  /api/v1/wallet/history   → transaction history
"""
 
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
 
from arcx_core.permissions import IsKYCApproved, IsWalletActive, IsCircuitBreakerClear
from arcx_core.serializers import (
    DepositRequestSerializer,
    WithdrawRequestSerializer,
    WalletResponseSerializer,
    TransactionResponseSerializer,
)
from arcx_core.services.wallet_service import WalletService
 
logger = logging.getLogger("arcx.views.wallet")
 
 
def _user_id(request) -> str:
    """Extract ARCX user UUID from JWT subject claim."""
    return request.user.username   # JWT sub = ARCX user UUID
 
 
class WalletBalanceView(APIView):
    """
    GET /api/v1/wallet/
 
    Returns the user's current balance and unrealized P&L.
    No KYC requirement — even pending users can see their balance.
    """
    permission_classes = [IsAuthenticated]
 
    def get(self, request):
        service = WalletService()
        wallet  = service.get_wallet(_user_id(request))
 
        # Fetch current NAV to compute unrealized P&L
        # If oracle is down, we still return the balance (P&L shows null)
        current_nav = None
        try:
            prices      = service._fetch_prices()
            current_nav = service._get_nav_inr(prices)
        except Exception:
            logger.warning("Could not fetch NAV for P&L calculation. Returning balance only.")
 
        serializer = WalletResponseSerializer(
            wallet,
            context={"current_nav_inr": current_nav},
        )
        return Response(serializer.data)
 
 
class DepositView(APIView):
    """
    POST /api/v1/wallet/deposit
    Headers: Idempotency-Key: <uuid>
 
    Body:
      { "amount_inr": "5000.00" }
 
    Response:
      {
        "transaction_id": "...",
        "arcx_credited":  "49.123456...",
        "nav_at_tx":      "101.80",
        "new_balance":    "49.123456..."
      }
    """
    permission_classes = [IsAuthenticated, IsKYCApproved, IsCircuitBreakerClear]
 
    def post(self, request):
        serializer = DepositRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
 
        service = WalletService()
        tx      = service.deposit(
            user_id    = _user_id(request),
            amount_inr = serializer.validated_data["amount_inr"],
        )
 
        wallet = service.get_wallet(_user_id(request))
 
        return Response(
            {
                "transaction_id": str(tx.id),
                "arcx_credited":  str(tx.amount_arcx),
                "nav_at_tx":      str(tx.nav_at_tx),
                "new_balance":    str(wallet.arcx_balance),
            },
            status=status.HTTP_201_CREATED,
        )
 
 
class WithdrawView(APIView):
    """
    POST /api/v1/wallet/withdraw
    Headers: Idempotency-Key: <uuid>
 
    Body:
      { "amount_arcx": "10.5" }
 
    Response:
      {
        "transaction_id": "...",
        "inr_returned":   "1068.90",
        "nav_at_tx":      "101.80",
        "new_balance":    "38.623456..."
      }
    """
    permission_classes = [IsAuthenticated, IsKYCApproved, IsWalletActive, IsCircuitBreakerClear]
 
    def post(self, request):
        serializer = WithdrawRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
 
        service = WalletService()
        tx      = service.withdraw(
            user_id     = _user_id(request),
            amount_arcx = serializer.validated_data["amount_arcx"],
        )
 
        wallet = service.get_wallet(_user_id(request))
 
        return Response(
            {
                "transaction_id": str(tx.id),
                "inr_returned":   str(tx.amount_inr),
                "nav_at_tx":      str(tx.nav_at_tx),
                "new_balance":    str(wallet.arcx_balance),
            },
            status=status.HTTP_201_CREATED,
        )
 
 
class TransactionHistoryView(APIView):
    """
    GET /api/v1/wallet/history?limit=20
 
    Returns the last N transactions for the authenticated user.
    """
    permission_classes = [IsAuthenticated]
 
    def get(self, request):
        limit = min(int(request.query_params.get("limit", 20)), 100)
 
        service = WalletService()
        txns    = service.get_transaction_history(_user_id(request), limit=limit)
 
        serializer = TransactionResponseSerializer(txns, many=True)
        return Response({"transactions": serializer.data, "count": len(serializer.data)})
 