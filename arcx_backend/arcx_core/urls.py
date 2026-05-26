"""
ARCX API URL Configuration — v1 (Phase 6 update)
--------------------------------------------------
Goes in: arcx_backend/arcx_core/urls.py
REPLACES the Phase 3 version.

Full endpoint map after Phase 6:

  PUBLIC:
    POST /api/v1/auth/register     → Create account (returns JWT immediately)
    GET  /api/v1/oracle/price      → Live NAV + asset prices
    GET  /api/v1/nav/history       → Historical NAV (price chart data)
    GET  /api/v1/nav/today         → Today's published NAV with audit hash

  AUTHENTICATED (any KYC status):
    GET  /api/v1/auth/me           → Full profile + wallet balance
    POST /api/v1/auth/logout       → Blacklist refresh token
    GET  /api/v1/kyc/status        → Current KYC tier + history
    GET  /api/v1/wallet/           → Balance + unrealized P&L
    GET  /api/v1/wallet/history    → Transaction history

  AUTHENTICATED + KYC APPROVED:
    POST /api/v1/kyc/submit        → Submit KYC document reference
    POST /api/v1/wallet/deposit    → INR → ARCX  [Idempotency-Key required]
    POST /api/v1/wallet/withdraw   → ARCX → INR  [Idempotency-Key required]
    POST /api/v1/transfer/         → P2P ARCX    [Idempotency-Key required]

  AUTH (root urls.py):
    POST /api/auth/token/          → Login: get access + refresh tokens
    POST /api/auth/token/refresh/  → Refresh expired access token
"""

from django.urls import path

from arcx_core.views.auth_views     import RegisterView, MeView, LogoutView
from arcx_core.views.kyc_views      import KYCSubmitView, KYCStatusView
from arcx_core.views.wallet_views   import (
    WalletBalanceView, DepositView, WithdrawView, TransactionHistoryView
)
from arcx_core.views.oracle_views   import LivePriceView, NAVHistoryView, TodayNAVView
from arcx_core.views.transfer_views import TransferView
from arcx_core.views.portfolio_views import PortfolioAnalyticsView
from arcx_core.views.admin_views import (
    AdminUserListView, AdminKYCView, AdminNAVComputerView
)

urlpatterns = [
    # ── Auth ─────────────────────────────────────────────────────────────
    path("auth/register",   RegisterView.as_view(), name="auth_register"),
    path("auth/me",         MeView.as_view(),       name="auth_me"),
    path("auth/logout",     LogoutView.as_view(),   name="auth_logout"),

    # ── KYC ──────────────────────────────────────────────────────────────
    path("kyc/submit",      KYCSubmitView.as_view(),  name="kyc_submit"),
    path("kyc/status",      KYCStatusView.as_view(),  name="kyc_status"),

    # ── Wallet ────────────────────────────────────────────────────────────
    path("wallet/",         WalletBalanceView.as_view(),      name="wallet_balance"),
    path("wallet/deposit",  DepositView.as_view(),            name="wallet_deposit"),
    path("wallet/withdraw", WithdrawView.as_view(),           name="wallet_withdraw"),
    path("wallet/history",  TransactionHistoryView.as_view(), name="wallet_history"),

    # ── Transfer ──────────────────────────────────────────────────────────
    path("transfer/",       TransferView.as_view(),           name="transfer"),

    # ── Oracle & NAV ──────────────────────────────────────────────────────
    path("oracle/price",    LivePriceView.as_view(),          name="oracle_price"),
    path("nav/history",     NAVHistoryView.as_view(),         name="nav_history"),
    path("nav/today",       TodayNAVView.as_view(),           name="nav_today"),

    # ── Portfolio ─────────────────────────────────────────────────────
    path("portfolio/analytics", PortfolioAnalyticsView.as_view(), name="portfolio_analytics"),

    # ── Admin ─────────────────────────────────────────────────────────────
    path("admin/users",       AdminUserListView.as_view(),      name="admin_users"),
    path("admin/kyc",         AdminKYCView.as_view(),           name="admin_kyc"),
    path("admin/nav/compute", AdminNAVComputerView.as_view(),   name="admin_nav_compute"),
]