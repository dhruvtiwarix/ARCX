"""
ARCX Phase 4 — Observability Tests
-------------------------------------
Goes in: arcx_backend/tests/test_observability.py

Tests that every critical operation produces the right structured log entry.

We test logging by capturing what the logger EMITS, not by reading files.
This makes tests fast (no disk I/O) and deterministic.

Run: python manage.py test tests.test_observability
"""

import json
import logging
from decimal import Decimal
from unittest.mock import patch, MagicMock
from datetime import datetime

from django.test import TestCase

from arcx_core.logger import arcx_logger, ArcxLogger, _emit


# ── Helper: Capture log output in tests ──────────────────────────────────────

class LogCapture(logging.Handler):
    """
    A logging handler that captures records into a list.
    Install it on the 'arcx' logger during tests, collect output,
    then remove it after.

    Usage:
      with LogCapture() as captured:
          arcx_logger.deposit_completed(...)
      assert any(e["event"] == "DEPOSIT_COMPLETED" for e in captured.records)
    """
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        try:
            self.records.append(json.loads(record.getMessage()))
        except json.JSONDecodeError:
            pass

    def __enter__(self):
        logging.getLogger("arcx").addHandler(self)
        return self

    def __exit__(self, *args):
        logging.getLogger("arcx").removeHandler(self)

    def find(self, event: str) -> list:
        """Return all captured records matching an event name."""
        return [r for r in self.records if r.get("event") == event]

    def first(self, event: str) -> dict:
        """Return first record matching event, or {}."""
        matches = self.find(event)
        return matches[0] if matches else {}


# ── Logger Unit Tests ─────────────────────────────────────────────────────────

class TestArcxLoggerOutput(TestCase):
    """Tests that arcx_logger emits correctly structured JSON for each event."""

    def test_deposit_completed_fields(self):
        with LogCapture() as cap:
            arcx_logger.deposit_completed(
                user_id     = "user-abc",
                amount_inr  = Decimal("5000.00"),
                arcx_minted = Decimal("49.12"),
                nav_inr     = Decimal("101.80"),
                tx_id       = "tx-xyz",
                duration_ms = 143,
            )
        record = cap.first("DEPOSIT_COMPLETED")

        self.assertEqual(record["event"],       "DEPOSIT_COMPLETED")
        self.assertEqual(record["level"],       "INFO")
        self.assertEqual(record["user_id"],     "user-abc")
        self.assertEqual(record["amount_inr"],  "5000.00")
        self.assertEqual(record["arcx_minted"], "49.12")
        self.assertEqual(record["tx_id"],       "tx-xyz")
        self.assertEqual(record["duration_ms"], 143)
        self.assertIn("ts", record)

    def test_deposit_failed_fields(self):
        with LogCapture() as cap:
            arcx_logger.deposit_failed(
                user_id    = "user-abc",
                amount_inr = Decimal("5000.00"),
                error      = "Wallet is frozen",
                error_code = "WALLET_FROZEN",
            )
        record = cap.first("DEPOSIT_FAILED")

        self.assertEqual(record["level"],      "ERROR")
        self.assertEqual(record["event"],      "DEPOSIT_FAILED")
        self.assertEqual(record["error_code"], "WALLET_FROZEN")

    def test_withdraw_completed_fields(self):
        with LogCapture() as cap:
            arcx_logger.withdraw_completed(
                user_id      = "user-abc",
                amount_arcx  = Decimal("10.0"),
                inr_returned = Decimal("1018.00"),
                nav_inr      = Decimal("101.80"),
                tx_id        = "tx-xyz",
                duration_ms  = 98,
            )
        record = cap.first("WITHDRAW_COMPLETED")
        self.assertEqual(record["event"],       "WITHDRAW_COMPLETED")
        self.assertEqual(record["inr_returned"], "1018.00")

    def test_transfer_completed_fields(self):
        with LogCapture() as cap:
            arcx_logger.transfer_completed(
                sender_id       = "user-abc",
                recipient_email = "friend@arcx.in",
                amount_arcx     = Decimal("5.0"),
                tx_id           = "tx-xyz",
                duration_ms     = 45,
            )
        record = cap.first("TRANSFER_COMPLETED")
        self.assertEqual(record["event"],           "TRANSFER_COMPLETED")
        self.assertEqual(record["recipient_email"], "friend@arcx.in")
        self.assertEqual(record["duration_ms"],     45)

    def test_oracle_fetch_fields(self):
        with LogCapture() as cap:
            arcx_logger.oracle_fetch(
                sources_used = ["Yahoo Finance"],
                spy          = 530.0,
                tlt          = 95.0,
                gld          = 185.0,
                usd_inr      = 83.5,
                nav_inr      = 101.80,
                duration_ms  = 1240,
            )
        record = cap.first("ORACLE_FETCH")
        self.assertEqual(record["event"],        "ORACLE_FETCH")
        self.assertEqual(record["sources_used"], ["Yahoo Finance"])
        self.assertEqual(record["duration_ms"],  1240)

    def test_oracle_failure_is_error_level(self):
        with LogCapture() as cap:
            arcx_logger.oracle_failure(
                error              = "All sources down",
                sources_attempted  = ["Yahoo Finance", "Alpha Vantage"],
            )
        record = cap.first("ORACLE_FAILURE")
        self.assertEqual(record["level"], "ERROR")

    def test_circuit_breaker_is_warning_level(self):
        with LogCapture() as cap:
            arcx_logger.circuit_breaker_fired(
                tier             = "tier_2",
                market_drop_pct  = 11.5,
                reason           = "SPY dropped 11.5% in 1 hour",
            )
        record = cap.first("CIRCUIT_BREAKER_FIRED")
        self.assertEqual(record["level"], "WARNING")
        self.assertEqual(record["tier"],  "tier_2")

    def test_request_out_5xx_is_error_level(self):
        with LogCapture() as cap:
            arcx_logger.request_out(
                method      = "POST",
                path        = "/api/v1/wallet/deposit",
                status_code = 500,
                user_id     = "user-abc",
                request_id  = "req-123",
                duration_ms = 200,
            )
        record = cap.first("REQUEST_OUT")
        self.assertEqual(record["level"],       "ERROR")
        self.assertEqual(record["status_code"], 500)

    def test_request_out_200_is_info_level(self):
        with LogCapture() as cap:
            arcx_logger.request_out(
                method      = "GET",
                path        = "/api/v1/oracle/price",
                status_code = 200,
                user_id     = None,
                request_id  = "req-456",
                duration_ms = 55,
            )
        record = cap.first("REQUEST_OUT")
        self.assertEqual(record["level"],   "INFO")
        self.assertEqual(record["user_id"], "anonymous")

    def test_decimal_values_serialized_as_strings(self):
        """
        Decimal in JSON must be string, not float.
        float(Decimal("5000.00")) loses precision at large values.
        """
        with LogCapture() as cap:
            arcx_logger.deposit_completed(
                user_id     = "u",
                amount_inr  = Decimal("99999999.99"),
                arcx_minted = Decimal("1000000.123456789"),
                nav_inr     = Decimal("99.9999"),
                tx_id       = "t",
                duration_ms = 1,
            )
        record = cap.first("DEPOSIT_COMPLETED")
        # Must be string — JSON float would mangle this value
        self.assertIsInstance(record["amount_inr"],  str)
        self.assertIsInstance(record["arcx_minted"], str)

    def test_log_operation_decorator_emits_start_and_end(self):
        """The @log_operation decorator must emit OPERATION_START and OPERATION_END."""
        from arcx_core.logger import log_operation

        @log_operation("test_op")
        def dummy():
            return "ok"

        with LogCapture() as cap:
            dummy()

        self.assertEqual(len(cap.find("OPERATION_START")), 1)
        self.assertEqual(len(cap.find("OPERATION_END")),   1)
        end_record = cap.first("OPERATION_END")
        self.assertEqual(end_record["status"], "ok")
        self.assertIn("duration_ms", end_record)

    def test_log_operation_decorator_logs_error_on_exception(self):
        from arcx_core.logger import log_operation

        @log_operation("failing_op")
        def boom():
            raise ValueError("Something broke")

        with LogCapture() as cap:
            with self.assertRaises(ValueError):
                boom()

        end_record = cap.first("OPERATION_END")
        self.assertEqual(end_record["status"],     "error")
        self.assertEqual(end_record["error_type"], "ValueError")
        self.assertIn("Something broke", end_record["error"])