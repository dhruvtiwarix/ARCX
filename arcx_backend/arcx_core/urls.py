"""
ARCX Root URL Configuration
------------------------------
All ARCX endpoints live under /api/v1/.
Versioning in the URL means we can ship /api/v2/ later without
breaking any client that still calls /api/v1/.

JWT endpoints:
  POST /api/auth/token/          → get access + refresh tokens
  POST /api/auth/token/refresh/  → swap refresh → new access token
"""

from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Auth — JWT token exchange
    path("api/auth/token/",         TokenObtainPairView.as_view(),  name="token_obtain"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(),     name="token_refresh"),

    # ARCX v1 API
    path("api/v1/", include("arcx_core.urls")),
]