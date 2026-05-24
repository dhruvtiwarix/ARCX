"""
ARCX Middleware — Phase 4 (Updated)
--------------------------------------
Goes in: arcx_backend/arcx_core/middleware.py
REPLACES the Phase 3 version of this file.

What's new in Phase 4:
  RequestLoggingMiddleware → logs every request in + response out
    {ts, event, method, path, status_code, user_id, request_id, duration_ms}

  The request_id is a UUID generated per request.
  It ties the REQUEST_IN log to the REQUEST_OUT log.
  When a user reports a bug ("my deposit failed at 10:30"), you search:
    jq 'select(.request_id=="abc-123")' logs/arcx.log
  And see the FULL request lifecycle: what came in, what went out, how long it took.

IdempotencyMiddleware from Phase 3 is preserved below, unchanged.
"""

import uuid
import time
import hashlib
import json
import logging

from django.core.cache import cache
from django.http import JsonResponse

from arcx_core.logger import arcx_logger

logger = logging.getLogger("arcx.middleware")

IDEMPOTENCY_REQUIRED_PATHS = {
    "/api/v1/wallet/deposit",
    "/api/v1/wallet/withdraw",
    "/api/v1/transfer/",
}
IDEMPOTENCY_TTL = 60 * 60 * 24


# ── Middleware 1: Request Logging ─────────────────────────────────────────────

class RequestLoggingMiddleware:
    """
    Logs every HTTP request and response as structured JSON.

    Attach to MIDDLEWARE in settings.py BEFORE IdempotencyMiddleware:
      MIDDLEWARE = [
          "arcx_core.middleware.RequestLoggingMiddleware",   # First
          "arcx_core.middleware.IdempotencyMiddleware",      # Second
          ...
      ]

    Why first? So we capture the full duration including idempotency checks.

    Adds X-Request-ID header to every response.
    Frontend can log this and include it in bug reports.
    You can then grep logs by request ID to find the exact transaction.

    Health check paths (like /health/) are skipped to avoid log spam.
    """

    SKIP_PATHS = {"/health/", "/favicon.ico", "/robots.txt"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip health checks and static files
        if request.path in self.SKIP_PATHS:
            return self.get_response(request)

        request_id = str(uuid.uuid4())
        request.request_id = request_id      # Attach to request for views to use
        start      = time.monotonic()

        # Resolve user from JWT if possible (don't fail if not authenticated)
        user_id = self._get_user_id(request)

        arcx_logger.request_in(
            method     = request.method,
            path       = request.path,
            user_id    = user_id,
            request_id = request_id,
        )

        response = self.get_response(request)

        duration_ms = int((time.monotonic() - start) * 1000)

        arcx_logger.request_out(
            method      = request.method,
            path        = request.path,
            status_code = response.status_code,
            user_id     = user_id,
            request_id  = request_id,
            duration_ms = duration_ms,
        )

        # Add request ID to response headers — useful for debugging
        response["X-Request-ID"] = request_id
        return response

    def _get_user_id(self, request) -> str | None:
        """
        Try to extract user ID from the JWT Authorization header.
        Returns None silently if not present or invalid — we don't
        want auth logic here, just the ID for logging.
        """
        try:
            from rest_framework_simplejwt.tokens import UntypedToken
            from rest_framework_simplejwt.exceptions import TokenError
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                token_str = auth.split(" ", 1)[1]
                token = UntypedToken(token_str)
                return str(token.payload.get("user_id") or token.payload.get("sub"))
        except Exception:
            pass
        return None


# ── Middleware 2: Idempotency (from Phase 3, unchanged) ───────────────────────

class IdempotencyMiddleware:
    """
    Idempotency engine — see Phase 3 documentation.
    Requires Idempotency-Key header on all financial POST endpoints.
    Caches responses to prevent duplicate transactions on retry.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self._should_check(request):
            return self.get_response(request)

        idempotency_key = request.headers.get("Idempotency-Key", "").strip()

        if not idempotency_key:
            return JsonResponse(
                {
                    "error": "Idempotency-Key header is required for this endpoint.",
                    "code":  "MISSING_IDEMPOTENCY_KEY",
                },
                status=400,
            )

        body_hash = self._hash_body(request)
        cache_key = f"idempotency:{idempotency_key}"
        cached    = cache.get(cache_key)

        if cached is not None:
            if cached.get("body_hash") != body_hash:
                logger.warning("Idempotency conflict: key=%s", idempotency_key[:8])
                return JsonResponse(
                    {
                        "error": (
                            "This Idempotency-Key was already used with a different request body. "
                            "Generate a new key for a new request."
                        ),
                        "code": "IDEMPOTENCY_CONFLICT",
                    },
                    status=409,
                )
            logger.info("Idempotency cache hit: key=%s", idempotency_key[:8])
            response = JsonResponse(cached["response_body"], status=cached["status_code"])
            response["X-Idempotency-Replayed"] = "true"
            return response

        response = self.get_response(request)

        if response.status_code < 500:
            try:
                response_body = json.loads(response.content)
                cache.set(
                    cache_key,
                    {
                        "body_hash":     body_hash,
                        "response_body": response_body,
                        "status_code":   response.status_code,
                    },
                    timeout=IDEMPOTENCY_TTL,
                )
            except (json.JSONDecodeError, AttributeError):
                pass

        return response

    def _should_check(self, request) -> bool:
        return (
            request.method == "POST"
            and request.path.rstrip("/") in {p.rstrip("/") for p in IDEMPOTENCY_REQUIRED_PATHS}
        )

    def _hash_body(self, request) -> str:
        return hashlib.sha256(request.body).hexdigest()