"""
ARCX Custom Exception Handler
--------------------------------
Problem: DRF's default exception handler returns different shapes
for different errors:

  Validation error:   {"field": ["This field is required."]}
  Permission error:   {"detail": "Authentication credentials were not provided."}
  Custom error:       whatever you raise

This is terrible for frontend developers. They have to write
3 different error-handling code paths.

Solution: Normalize ALL errors to one shape:
  {
    "error":   "Human-readable message",
    "code":    "MACHINE_READABLE_CODE",
    "details": {...}  ← optional field-level validation errors
  }

Every error in ARCX uses this shape. Period.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger("arcx.exceptions")


# ── ARCX-specific exception classes ──────────────────────────────────────────

class InsufficientBalanceError(Exception):
    """User is trying to withdraw/transfer more ARCX than they hold."""
    code = "INSUFFICIENT_BALANCE"


class WalletFrozenError(Exception):
    """Wallet is frozen by compliance. No transactions allowed."""
    code = "WALLET_FROZEN"


class KYCRequiredError(Exception):
    """Action requires a higher KYC tier than the user currently has."""
    code = "KYC_REQUIRED"


class CircuitBreakerActiveError(Exception):
    """A circuit breaker is active. Action is temporarily halted."""
    code = "CIRCUIT_BREAKER_ACTIVE"


class IdempotencyConflictError(Exception):
    """The idempotency key was already used for a DIFFERENT request body."""
    code = "IDEMPOTENCY_CONFLICT"


class OracleUnavailableError(Exception):
    """The price oracle could not fetch a valid price. Safe to retry."""
    code = "ORACLE_UNAVAILABLE"


# ── Error code → HTTP status mapping ─────────────────────────────────────────
ERROR_STATUS_MAP = {
    "INSUFFICIENT_BALANCE":   status.HTTP_422_UNPROCESSABLE_ENTITY,
    "WALLET_FROZEN":          status.HTTP_403_FORBIDDEN,
    "KYC_REQUIRED":           status.HTTP_403_FORBIDDEN,
    "CIRCUIT_BREAKER_ACTIVE": status.HTTP_503_SERVICE_UNAVAILABLE,
    "IDEMPOTENCY_CONFLICT":   status.HTTP_409_CONFLICT,
    "ORACLE_UNAVAILABLE":     status.HTTP_503_SERVICE_UNAVAILABLE,
}

ARCX_EXCEPTIONS = (
    InsufficientBalanceError,
    WalletFrozenError,
    KYCRequiredError,
    CircuitBreakerActiveError,
    IdempotencyConflictError,
    OracleUnavailableError,
)


# ── The handler ───────────────────────────────────────────────────────────────

def arcx_exception_handler(exc, context):
    """
    Called by DRF whenever a view raises an exception.

    Flow:
      1. If it's one of our ARCX exceptions → normalize and return
      2. If it's a DRF exception → normalize its shape
      3. Anything else → 500 with safe message (no internal details leaked)
    """
    # ── ARCX business logic exceptions ───────────────────────────────────
    if isinstance(exc, ARCX_EXCEPTIONS):
        code        = exc.code
        http_status = ERROR_STATUS_MAP.get(code, status.HTTP_400_BAD_REQUEST)
        logger.warning("ARCX exception: code=%s message=%s", code, str(exc))
        return Response(
            {"error": str(exc) or code, "code": code},
            status=http_status,
        )

    # ── DRF exceptions (auth, validation, etc.) ───────────────────────────
    response = exception_handler(exc, context)
    if response is not None:
        original_data = response.data

        # DRF validation errors have field-level detail
        if isinstance(original_data, dict) and "detail" not in original_data:
            # Field-level validation error
            return Response(
                {
                    "error":   "Validation failed. Check the details field.",
                    "code":    "VALIDATION_ERROR",
                    "details": original_data,
                },
                status=response.status_code,
            )

        # Auth / permission errors — "detail" key
        detail = original_data.get("detail", str(original_data))
        code_map = {
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            429: "RATE_LIMITED",
        }
        return Response(
            {
                "error": str(detail),
                "code":  code_map.get(response.status_code, "API_ERROR"),
            },
            status=response.status_code,
        )

    # ── Unhandled server error ────────────────────────────────────────────
    logger.exception("Unhandled exception in view: %s", context.get("view"))
    return Response(
        {"error": "An internal error occurred. Please try again.", "code": "INTERNAL_ERROR"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )