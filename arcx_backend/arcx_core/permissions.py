"""
ARCX Permission Classes — Phase 3
------------------------------------
Django REST Framework permission classes are the clean way to enforce
access rules without cluttering view code.

Instead of this (messy):
    def post(self, request):
        if request.user.kyc_status != 'approved':
            return Response({"error": "KYC required"}, 403)
        if request.user.wallet.is_frozen:
            return Response({"error": "Wallet frozen"}, 403)
        # ... actual logic ...

You do this (clean):
    class DepositView(APIView):
        permission_classes = [IsAuthenticated, IsKYCApproved, IsWalletActive]

        def post(self, request):
            # If we got here, all checks passed
            # ... actual logic ...

Each permission class has ONE job. Compose them.
"""

from rest_framework.permissions import BasePermission
from arcx_core.models import User


class IsKYCApproved(BasePermission):
    """
    Allows access only to users with kyc_status = 'approved'.
    Required for: deposit, withdraw, transfer.

    Users with 'pending' status can read prices and NAV history,
    but cannot move money.
    """
    message = "KYC verification required. Please complete identity verification."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            arcx_user = User.objects.get(
                id=request.user.username,  # JWT subject = ARCX user UUID
                deleted_at__isnull=True,
            )
            return arcx_user.kyc_status == User.KycStatus.APPROVED
        except User.DoesNotExist:
            return False


class IsWalletActive(BasePermission):
    """
    Allows access only if the user's wallet is not frozen.
    Frozen wallets: compliance hold. User can view but not transact.
    """
    message = "Your wallet has been temporarily suspended. Contact support."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            arcx_user = User.objects.select_related("wallet").get(
                id=request.user.username,
                deleted_at__isnull=True,
            )
            return not arcx_user.wallet.is_frozen
        except (User.DoesNotExist, Exception):
            return False


class IsCircuitBreakerClear(BasePermission):
    """
    Blocks transaction endpoints when an active circuit breaker is running.

    Tier 1 → withdrawals still allowed (only new deposits blocked)
    Tier 2 → all new deposits blocked
    Tier 3 → complete halt, all transactions blocked

    This permission class checks for Tier 3.
    Tier-specific logic lives in the service layer.
    """
    message = "Transactions are temporarily paused due to market conditions. Please try later."

    def has_permission(self, request, view):
        from arcx_core.models import CircuitBreakerLog
        active_tier3 = CircuitBreakerLog.objects.filter(
            tier=CircuitBreakerLog.Tier.TIER_3,
            event_type=CircuitBreakerLog.EventType.TRIGGERED,
            resolved_at__isnull=True,
        ).exists()
        return not active_tier3