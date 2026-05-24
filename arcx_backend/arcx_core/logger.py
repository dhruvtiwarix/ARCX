"""
ARCX Structured Logger — Phase 4
------------------------------------
Goes in: arcx_backend/arcx_core/logger.py

WHY STRUCTURED LOGGING?
  A normal log line looks like this:
    [2025-06-01 10:30:01] INFO Deposit completed for user abc amount 5000

  A structured log line looks like this:
    {"ts":"2025-06-01T10:30:01Z","level":"INFO","event":"DEPOSIT_COMPLETED",
     "user_id":"abc","amount_inr":"5000.00","arcx_minted":"49.12","nav":"101.80",
     "tx_id":"xyz","duration_ms":143}

  Why does this matter?
  With plain text, answering "What was the total INR deposited on June 1st?"
  requires grep + regex + awk. Fragile and slow.

  With structured logs, you run one query in any log tool (Datadog, Loki,
  CloudWatch, even grep + jq):
    cat arcx.log | jq 'select(.event=="DEPOSIT_COMPLETED") | .amount_inr'

  Every MNC uses structured logging. If a candidate's project has it,
  evaluators immediately know they understand production systems.

EVENTS LOGGED:
  DEPOSIT_COMPLETED     -> wallet_service.deposit()
  DEPOSIT_FAILED        -> wallet_service.deposit() on exception
  WITHDRAW_COMPLETED    -> wallet_service.withdraw()
  WITHDRAW_FAILED       -> wallet_service.withdraw() on exception
  TRANSFER_COMPLETED    -> transfer_service.transfer()
  TRANSFER_FAILED       -> transfer_service.transfer() on exception
  ORACLE_FETCH          -> MultiSourceOracle.fetch_prices()
  ORACLE_FAILURE        -> oracle fetch failed
  REQUEST_IN            -> every API request (middleware)
  REQUEST_OUT           -> every API response with status + duration
  CIRCUIT_BREAKER_FIRED -> circuit breaker triggered
  NAV_PUBLISHED         -> daily NAV report saved

USAGE:
  from arcx_core.logger import arcx_logger

  arcx_logger.deposit_completed(
      user_id="abc",
      amount_inr=Decimal("5000"),
      arcx_minted=Decimal("49.12"),
      nav_inr=Decimal("101.80"),
      tx_id="xyz-123",
      duration_ms=143,
  )
"""

import json
import time
import logging
import functools
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any, Optional

# Use the standard Django logger -- settings.py configures where it goes
_log = logging.getLogger("arcx")


# -- Helpers ------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _safe_str(v: Any) -> Any:
    """Convert Decimal -> str so JSON does not crash."""
    if isinstance(v, Decimal):
        return str(v)
    return v


def _emit(level: str, event: str, **fields):
    """
    The single emission point for every structured log.
    Builds the JSON envelope and hands it to the standard logger.
    The standard logger then routes it to the handlers in settings.py.
    """
    payload = {
        "ts":    _now(),
        "level": level,
        "event": event,
        **{k: _safe_str(v) for k, v in fields.items()},
    }
    msg = json.dumps(payload, default=str)

    if level == "ERROR":
        _log.error(msg)
    elif level == "WARNING":
        _log.warning(msg)
    else:
        _log.info(msg)


# -- Transaction Events -------------------------------------------------------

class ArcxLogger:
    """
    Typed logger for every ARCX event.
    Each method corresponds to one real system event.
    Using named methods (instead of raw _emit calls scattered everywhere)
    means: if you rename a field, you fix it in ONE place.
    """

    # -- Wallet ---------------------------------------------------------------

    def deposit_completed(
        self,
        user_id: str,
        amount_inr: Decimal,
        arcx_minted: Decimal,
        nav_inr: Decimal,
        tx_id: str,
        duration_ms: int,
    ):
        _emit("INFO", "DEPOSIT_COMPLETED",
              user_id=user_id,
              amount_inr=amount_inr,
              arcx_minted=arcx_minted,
              nav_inr=nav_inr,
              tx_id=tx_id,
              duration_ms=duration_ms)

    def deposit_failed(self, user_id: str, amount_inr: Decimal, error: str, error_code: str):
        _emit("ERROR", "DEPOSIT_FAILED",
              user_id=user_id,
              amount_inr=amount_inr,
              error=error,
              error_code=error_code)

    def withdraw_completed(
        self,
        user_id: str,
        amount_arcx: Decimal,
        inr_returned: Decimal,
        nav_inr: Decimal,
        tx_id: str,
        duration_ms: int,
    ):
        _emit("INFO", "WITHDRAW_COMPLETED",
              user_id=user_id,
              amount_arcx=amount_arcx,
              inr_returned=inr_returned,
              nav_inr=nav_inr,
              tx_id=tx_id,
              duration_ms=duration_ms)

    def withdraw_failed(self, user_id: str, amount_arcx: Decimal, error: str, error_code: str):
        _emit("ERROR", "WITHDRAW_FAILED",
              user_id=user_id,
              amount_arcx=amount_arcx,
              error=error,
              error_code=error_code)

    # -- Transfers ------------------------------------------------------------

    def transfer_completed(
        self,
        sender_id: str,
        recipient_email: str,
        amount_arcx: Decimal,
        tx_id: str,
        duration_ms: int,
    ):
        _emit("INFO", "TRANSFER_COMPLETED",
              sender_id=sender_id,
              recipient_email=recipient_email,
              amount_arcx=amount_arcx,
              tx_id=tx_id,
              duration_ms=duration_ms)

    def transfer_failed(
        self, sender_id: str, recipient_email: str, amount_arcx: Decimal, error: str
    ):
        _emit("ERROR", "TRANSFER_FAILED",
              sender_id=sender_id,
              recipient_email=recipient_email,
              amount_arcx=amount_arcx,
              error=error)

    # -- Oracle ---------------------------------------------------------------

    def oracle_fetch(
        self,
        sources_used: list,
        spy: float,
        tlt: float,
        gld: float,
        usd_inr: float,
        nav_inr: float,
        duration_ms: int,
    ):
        _emit("INFO", "ORACLE_FETCH",
              sources_used=sources_used,
              spy_usd=spy,
              tlt_usd=tlt,
              gld_usd=gld,
              usd_inr=usd_inr,
              nav_inr=nav_inr,
              duration_ms=duration_ms)

    def oracle_failure(self, error: str, sources_attempted: list):
        _emit("ERROR", "ORACLE_FAILURE",
              error=error,
              sources_attempted=sources_attempted)

    # -- Circuit Breaker ------------------------------------------------------

    def circuit_breaker_fired(self, tier: str, market_drop_pct: float, reason: str):
        _emit("WARNING", "CIRCUIT_BREAKER_FIRED",
              tier=tier,
              market_drop_pct=market_drop_pct,
              reason=reason)

    def circuit_breaker_resolved(self, tier: str, active_duration_minutes: float):
        _emit("INFO", "CIRCUIT_BREAKER_RESOLVED",
              tier=tier,
              active_duration_minutes=active_duration_minutes)

    # -- NAV ------------------------------------------------------------------

    def nav_published(self, nav_date: str, nav_inr: float, report_hash: str):
        _emit("INFO", "NAV_PUBLISHED",
              nav_date=nav_date,
              nav_inr=nav_inr,
              report_hash_prefix=report_hash[:16])

    # -- Request / Response ---------------------------------------------------

    def request_in(self, method: str, path: str, user_id: Optional[str], request_id: str):
        _emit("INFO", "REQUEST_IN",
              method=method,
              path=path,
              user_id=user_id or "anonymous",
              request_id=request_id)

    def request_out(
        self,
        method: str,
        path: str,
        status_code: int,
        user_id: Optional[str],
        request_id: str,
        duration_ms: int,
    ):
        level = "ERROR" if status_code >= 500 else "WARNING" if status_code >= 400 else "INFO"
        _emit(level, "REQUEST_OUT",
              method=method,
              path=path,
              status_code=status_code,
              user_id=user_id or "anonymous",
              request_id=request_id,
              duration_ms=duration_ms)


# -- Singleton ----------------------------------------------------------------
# One instance, imported everywhere. Thread-safe because Python's logging is.
arcx_logger = ArcxLogger()


# -- @log_operation decorator -------------------------------------------------

def log_operation(operation_name: str):
    """
    Decorator that wraps any service method and:
      1. Records start time
      2. Calls the function
      3. Logs success with duration_ms
      4. On exception: logs failure and re-raises

    USAGE:
      @log_operation("deposit")
      def deposit(self, user_id, amount_inr):
          ...

    Produces logs like:
      {"event":"OPERATION_START","operation":"deposit"}
      {"event":"OPERATION_END","operation":"deposit","duration_ms":143,"status":"ok"}
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            _emit("INFO", "OPERATION_START", operation=operation_name)
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.monotonic() - start) * 1000)
                _emit("INFO", "OPERATION_END",
                      operation=operation_name,
                      duration_ms=duration_ms,
                      status="ok")
                return result
            except Exception as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                _emit("ERROR", "OPERATION_END",
                      operation=operation_name,
                      duration_ms=duration_ms,
                      status="error",
                      error=str(exc),
                      error_type=type(exc).__name__)
                raise
        return wrapper
    return decorator