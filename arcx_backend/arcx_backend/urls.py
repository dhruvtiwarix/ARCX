"""
URL configuration for arcx_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
"""
ARCX API URL Configuration — v1
----------------------------------
All routes live under /api/v1/ (mounted in arcx_backend/urls.py).

Full endpoint map:
  PUBLIC (no auth):
    GET  /api/v1/oracle/price      → Live NAV + asset prices
    GET  /api/v1/nav/history       → Historical NAV (price chart data)
    GET  /api/v1/nav/today         → Today's published NAV with audit hash

  AUTHENTICATED:
    GET  /api/v1/wallet/           → Balance + unrealized P&L
    GET  /api/v1/wallet/history    → Transaction history

  AUTHENTICATED + KYC APPROVED:
    POST /api/v1/wallet/deposit    → INR → ARCX  [Idempotency-Key required]
    POST /api/v1/wallet/withdraw   → ARCX → INR  [Idempotency-Key required]
    POST /api/v1/transfer/         → P2P ARCX    [Idempotency-Key required]

  AUTH:
    POST /api/auth/token/          → Get JWT tokens
    POST /api/auth/token/refresh/  → Refresh JWT (in root urls.py)
"""

from django.contrib import admin
from django.urls import path
from arcx_core.views.wallet_views  import WalletBalanceView, DepositView, WithdrawView, TransactionHistoryView
from arcx_core.views.oracle_views  import LivePriceView, NAVHistoryView, TodayNAVView
from arcx_core.views.transfer_views import TransferView

urlpatterns = [
    # ── Django Admin ──────────────────────────────────────────────────────
    path("admin/", admin.site.urls),

    # ── Wallet ────────────────────────────────────────────────────────────
    path("api/v1/wallet/",          WalletBalanceView.as_view(),      name="wallet_balance"),
    path("api/v1/wallet/deposit",   DepositView.as_view(),            name="wallet_deposit"),
    path("api/v1/wallet/withdraw",  WithdrawView.as_view(),           name="wallet_withdraw"),
    path("api/v1/wallet/history",   TransactionHistoryView.as_view(), name="wallet_history"),

    # ── Transfer ──────────────────────────────────────────────────────────
    path("api/v1/transfer/",        TransferView.as_view(),           name="transfer"),

    # ── Oracle & NAV ──────────────────────────────────────────────────────
    path("api/v1/oracle/price",     LivePriceView.as_view(),          name="oracle_price"),
    path("api/v1/nav/history",      NAVHistoryView.as_view(),         name="nav_history"),
    path("api/v1/nav/today",        TodayNAVView.as_view(),           name="nav_today"),
]