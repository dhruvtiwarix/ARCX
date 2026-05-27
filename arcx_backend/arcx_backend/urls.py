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
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # ── Django Admin ──────────────────────────────────────────────────────
    path("admin/", admin.site.urls),

    # ── ARCX API v1 ───────────────────────────────────────────────────────
    path("api/v1/", include("arcx_core.urls")),

    # ── Auth (JWT) ────────────────────────────────────────────────────────
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ── API Documentation (drf-spectacular) ───────────────────────────────
    # /api/schema/        → raw OpenAPI 3.0 YAML/JSON download
    # /api/docs/          → Swagger UI (interactive, try-it-out)
    # /api/redoc/         → ReDoc UI (read-only, beautiful reference)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]