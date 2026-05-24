"""
ARCX Log Reader — Management Command
----------------------------------------

Usage:
  python manage.py read_logs
  python manage.py read_logs --event DEPOSIT_COMPLETED
  python manage.py read_logs --event DEPOSIT_FAILED
  python manage.py read_logs --event ORACLE_FAILURE
  python manage.py read_logs --user abc-123
  python manage.py read_logs --level ERROR
  python manage.py read_logs --event DEPOSIT_COMPLETED --tail 50
  python manage.py read_logs --summary

This is what separates an "I added print statements" project from an
"I built an observable system" project. Same data, completely different
impression on an evaluator.

Think of this as your personal CLI version of Datadog, built in 80 lines.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime

from django.core.management.base import BaseCommand
from django.conf import settings


COLORS = {
    "INFO":    "\033[32m",   # Green
    "WARNING": "\033[33m",   # Yellow
    "ERROR":   "\033[31m",   # Red
    "RESET":   "\033[0m",
    "BOLD":    "\033[1m",
    "CYAN":    "\033[36m",
    "DIM":     "\033[2m",
}


class Command(BaseCommand):
    help = "Read and filter ARCX structured logs. Use --summary for a stats overview."

    def add_arguments(self, parser):
        parser.add_argument(
            "--event",
            type=str,
            default=None,
            help="Filter by event type (e.g. DEPOSIT_COMPLETED, ORACLE_FAILURE)",
        )
        parser.add_argument(
            "--level",
            type=str,
            default=None,
            choices=["INFO", "WARNING", "ERROR"],
            help="Filter by log level",
        )
        parser.add_argument(
            "--user",
            type=str,
            default=None,
            help="Filter by user_id or sender_id",
        )
        parser.add_argument(
            "--tail",
            type=int,
            default=30,
            help="Number of most recent entries to show (default: 30)",
        )
        parser.add_argument(
            "--summary",
            action="store_true",
            help="Show summary statistics instead of individual log lines",
        )
        parser.add_argument(
            "--errors-only",
            action="store_true",
            help="Show only ERROR level entries (shortcut for --level ERROR)",
        )

    def handle(self, *args, **options):
        log_path = os.path.join(settings.BASE_DIR, "logs", "arcx.log")

        if not os.path.exists(log_path):
            self.stderr.write(
                f"\n  No log file found at {log_path}\n"
                f"  Start the server and make some requests first.\n\n"
            )
            sys.exit(1)

        entries = self._load_entries(log_path)

        if not entries:
            self.stdout.write("\n  Log file is empty.\n")
            return

        # Apply filters
        if options["errors_only"]:
            options["level"] = "ERROR"

        filtered = self._filter(entries, options)

        if options["summary"]:
            self._print_summary(filtered)
        else:
            self._print_entries(filtered[-options["tail"]:])

    def _load_entries(self, log_path: str) -> list:
        entries = []
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass   # Skip non-JSON lines (e.g. console output redirected here)
        return entries

    def _filter(self, entries: list, options: dict) -> list:
        result = entries

        if options.get("event"):
            result = [e for e in result if e.get("event") == options["event"].upper()]

        if options.get("level"):
            result = [e for e in result if e.get("level") == options["level"].upper()]

        if options.get("user"):
            uid = options["user"]
            result = [
                e for e in result
                if e.get("user_id") == uid
                or e.get("sender_id") == uid
            ]

        return result

    def _print_entries(self, entries: list):
        if not entries:
            self.stdout.write("\n  No log entries match your filters.\n")
            return

        self.stdout.write(
            f"\n{COLORS['BOLD']}  ARCX Log Viewer — {len(entries)} entries{COLORS['RESET']}\n"
            + "  " + "─" * 60 + "\n"
        )

        for entry in entries:
            level   = entry.get("level", "INFO")
            color   = COLORS.get(level, "")
            reset   = COLORS["RESET"]
            dim     = COLORS["DIM"]
            event   = entry.get("event", "UNKNOWN")

            # Format timestamp to just time (date is usually today)
            ts_raw  = entry.get("ts", "")
            try:
                ts = datetime.fromisoformat(ts_raw).strftime("%H:%M:%S.%f")[:-3]
            except ValueError:
                ts = ts_raw

            # Build the key fields line
            skip = {"ts", "level", "event"}
            fields = {k: v for k, v in entry.items() if k not in skip}
            fields_str = "  ".join(f"{k}={v}" for k, v in fields.items())

            self.stdout.write(
                f"  {dim}{ts}{reset}  "
                f"{color}{level:7}{reset}  "
                f"{COLORS['BOLD']}{event:30}{reset}  "
                f"{dim}{fields_str}{reset}\n"
            )

        self.stdout.write("\n")

    def _print_summary(self, entries: list):
        if not entries:
            self.stdout.write("\n  No entries to summarize.\n")
            return

        event_counts  = defaultdict(int)
        level_counts  = defaultdict(int)
        total_inr_in  = 0.0
        total_inr_out = 0.0
        failed_count  = 0
        durations     = []

        for e in entries:
            event = e.get("event", "UNKNOWN")
            level = e.get("level", "INFO")
            event_counts[event] += 1
            level_counts[level] += 1

            if event == "DEPOSIT_COMPLETED":
                try:
                    total_inr_in += float(e.get("amount_inr", 0))
                except (TypeError, ValueError):
                    pass

            if event == "WITHDRAW_COMPLETED":
                try:
                    total_inr_out += float(e.get("inr_returned", 0))
                except (TypeError, ValueError):
                    pass

            if level == "ERROR":
                failed_count += 1

            if "duration_ms" in e:
                try:
                    durations.append(int(e["duration_ms"]))
                except (TypeError, ValueError):
                    pass

        avg_ms = round(sum(durations) / len(durations)) if durations else 0
        max_ms = max(durations) if durations else 0

        b = COLORS["BOLD"]
        r = COLORS["RESET"]
        c = COLORS["CYAN"]
        g = COLORS["INFO"] if "INFO" in COLORS else "\033[32m"
        red = COLORS["ERROR"]

        self.stdout.write(f"\n{b}  ARCX Log Summary{r}\n  {'─'*50}\n")
        self.stdout.write(f"\n{b}  Volume{r}\n")
        self.stdout.write(f"    Total log entries  : {len(entries)}\n")
        self.stdout.write(f"    Errors             : {red}{failed_count}{r}\n")
        self.stdout.write(f"\n{b}  Money Flow{r}\n")
        self.stdout.write(f"    Total deposited    : Rs.{total_inr_in:,.2f}\n")
        self.stdout.write(f"    Total withdrawn    : Rs.{total_inr_out:,.2f}\n")
        self.stdout.write(f"\n{b}  Performance{r}\n")
        self.stdout.write(f"    Avg operation time : {avg_ms}ms\n")
        self.stdout.write(f"    Slowest operation  : {max_ms}ms\n")
        self.stdout.write(f"\n{b}  Events Breakdown{r}\n")
        for event, count in sorted(event_counts.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 30)
            self.stdout.write(f"    {event:35} {c}{count:4}{r}  {bar}\n")

        self.stdout.write("\n")