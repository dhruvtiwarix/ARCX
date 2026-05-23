"""
ARCX Idempotency Middleware — Phase 3
----------------------------------------
Problem: Networks are unreliable. A user taps "Deposit ₹5,000."
The request reaches the server, the transaction is created, but
the response never makes it back. The client retries.
Without idempotency, the user is charged twice.

Solution: Every mutating request (POST) carries an Idempotency-Key header.
The server stores (key → response). On retry, it returns the cached response
without re-executing the transaction.

This is standard in Stripe, Razorpay, and every serious payment API.

How to use (client side):
  POST /api/v1/wallet/deposit
  Headers:
    Authorization: Bearer <token>
    Idempotency-Key: <uuid4 generated client-side, same on retry>

Rules:
  - Same key + same body → return original response (idempotent)
  - Same key + different body → 409 CONFLICT (you made a mistake)
  - No key on POST → 400 BAD REQUEST (enforced on financial endpoints)
  - GET/DELETE are naturally idempotent → middleware ignores them

Storage: Django cache (Redis in production, LocMemCache in dev).
TTL: 24 hours (after which the key expires and can be reused).

NOTE: For Phase 3/MVP, we cache the full response body.
In Phase 4, we'll store idempotency records in PostgreSQL for
cross-process consistency (when you have multiple API workers).
"""

import hashlib
import json
import logging

from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger("arcx.idempotency")

# Only enforce on financial mutation endpoints
IDEMPOTENCY_REQUIRED_PATHS = {
    "/api/v1/wallet/deposit",
    "/api/v1/wallet/withdraw",
    "/api/v1/transfer/",
}

IDEMPOTENCY_TTL = 60 * 60 * 24  # 24 hours in seconds


class IdempotencyMiddleware:
    """
    Intercepts POST requests on financial endpoints.

    On first request:
      - Store (idempotency_key → response) in cache
      - Return response normally

    On retry with same key + same body:
      - Return cached response immediately
      - Transaction is NOT re-executed

    On retry with same key + different body:
      - Return 409 CONFLICT
      - Something is wrong on the client side
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self._should_check(request):
            return self.get_response(request)

        idempotency_key = request.headers.get("Idempotency-Key", "").strip()

        # Financial POST endpoints MUST include this header
        if not idempotency_key:
            return JsonResponse(
                {
                    "error": "Idempotency-Key header is required for this endpoint.",
                    "code":  "MISSING_IDEMPOTENCY_KEY",
                },
                status=400,
            )

        # Build a fingerprint of this exact request
        body_hash = self._hash_body(request)
        cache_key = f"idempotency:{idempotency_key}"

        cached = cache.get(cache_key)

        if cached is not None:
            stored_body_hash = cached.get("body_hash")

            # Same key, different body → conflict
            if stored_body_hash != body_hash:
                logger.warning(
                    "Idempotency conflict: key=%s", idempotency_key[:8]
                )
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

            # Same key, same body → return cached response
            logger.info("Idempotency cache hit: key=%s", idempotency_key[:8])
            response = JsonResponse(cached["response_body"], status=cached["status_code"])
            response["X-Idempotency-Replayed"] = "true"
            return response

        # First time seeing this key → process normally
        response = self.get_response(request)

        # Cache only successful and business-error responses (not 5xx)
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
                pass  # Don't cache unparseable responses

        return response

    def _should_check(self, request) -> bool:
        return (
            request.method == "POST"
            and request.path.rstrip("/") in {p.rstrip("/") for p in IDEMPOTENCY_REQUIRED_PATHS}
        )

    def _hash_body(self, request) -> str:
        """SHA256 of the raw request body. Used to detect body changes on retry."""
        return hashlib.sha256(request.body).hexdigest()