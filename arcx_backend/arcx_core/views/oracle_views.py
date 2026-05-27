"""
ARCX Oracle & NAV Views - Phase 3
------------------------------------
Endpoints:
  GET /api/v1/oracle/price   -> live NAV + asset prices (public, no auth)
  GET /api/v1/nav/history    -> historical NAV data for price chart
  GET /api/v1/nav/today      -> today's published NAV

oracle/price is intentionally public (no auth required).
Anyone can see the current price. This builds trust.
You can't run a "fair price" platform where the price is secret.
"""

import logging
from decimal import Decimal

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import serializers as drf_serializers
from drf_spectacular.utils import (
    extend_schema, OpenApiExample, OpenApiResponse,
    OpenApiParameter, inline_serializer
)
from drf_spectacular.types import OpenApiTypes

from domain.oracle import MultiSourceOracle, OracleFailureException
from domain.valuation import ValuationEngine
from arcx_core.models import VaultSnapshot, NAVHistory, VaultAssetHolding
from arcx_core.serializers import OraclePriceResponseSerializer, NAVHistorySerializer
from arcx_core.exceptions import OracleUnavailableError

logger = logging.getLogger("arcx.views.oracle")

# -- Inline response schemas ---------------------------------------------------
_TodayNAVSchema = inline_serializer(
    name="TodayNAVResponse",
    fields={
        "nav_date":             drf_serializers.DateField(help_text="Date of this NAV publication"),
        "nav_usd":              drf_serializers.DecimalField(max_digits=20, decimal_places=8),
        "nav_inr":              drf_serializers.DecimalField(max_digits=20, decimal_places=4),
        "dividend_accrued_inr": drf_serializers.DecimalField(max_digits=20, decimal_places=4),
        "report_hash":          drf_serializers.CharField(help_text="SHA-256 hash — verify the NAV was not tampered with"),
        "published_at":         drf_serializers.DateTimeField(),
    },
)

_NAVHistoryListSchema = inline_serializer(
    name="NAVHistoryListResponse",
    fields={
        "history": drf_serializers.ListField(child=drf_serializers.DictField(), help_text="List of NAV history records"),
    },
)

_ErrorSchema = inline_serializer(
    name="OracleErrorResponse",
    fields={
        "error": drf_serializers.CharField(),
        "code":  drf_serializers.CharField(),
    },
)


class LivePriceView(APIView):
    """
    GET /api/v1/oracle/price

    Public endpoint -- no authentication required.
    Returns live TWAP prices for all assets + current ARCX NAV.

    This is the "heartbeat" endpoint. The frontend polls this every 30s
    to keep the price display current.

    Response:
      {
        "spy_usd":      "530.25",
        "tlt_usd":      "95.10",
        "gld_usd":      "185.40",
        "usd_inr":      "83.50",
        "nav_usd":      "1.1952",
        "nav_inr":      "99.80",
        "sources_used": ["Yahoo Finance"],
        "fetched_at":   "2025-06-01T10:30:00Z"
      }
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Oracle"],
        operation_id="oracle_live_price",
        summary="Get live NAV and asset prices",
        description=(
            "**Public endpoint** — no authentication required.\n\n"
            "Returns real-time TWAP prices for all vault assets (SPY, TLT, GLD) "
            "and the current ARCX NAV in both USD and INR. "
            "The frontend polls this every 30 seconds.\n\n"
            "NAV is calculated from the latest vault snapshot using the formula:\n"
            "`NAV = total_vault_value_USD / total_arcx_supply`"
        ),
        responses={
            200: OraclePriceResponseSerializer,
            503: OpenApiResponse(
                response=_ErrorSchema,
                description="All price sources are temporarily unavailable",
                examples=[
                    OpenApiExample(
                        "Oracle down",
                        value={"error": "Live price data is temporarily unavailable. Please retry.", "code": "ORACLE_UNAVAILABLE"},
                    )
                ],
            ),
        },
        examples=[
            OpenApiExample(
                "Live price response",
                response_only=True,
                status_codes=["200"],
                value={
                    "spy_usd":      "530.2500",
                    "tlt_usd":      "95.1000",
                    "gld_usd":      "185.4000",
                    "usd_inr":      "83.5000",
                    "nav_usd":      "1.19520000",
                    "nav_inr":      "99.8000",
                    "sources_used": ["Yahoo Finance"],
                    "fetched_at":   "2025-06-01T10:30:00Z",
                },
            ),
        ],
        auth=[],   # Public — no JWT required
    )
    def get(self, request):
        try:
            oracle = MultiSourceOracle()
            prices = oracle.fetch_prices()
        except OracleFailureException as e:
            logger.error("Oracle failure on price endpoint: %s", e)
            raise OracleUnavailableError(
                "Live price data is temporarily unavailable. Please retry."
            )

        # Phase 6: Calculate current NAV from actual share quantities (Mark-to-Market)
        # No longer uses percentage weights — queries real holdings from DB.
        from datetime import datetime
        market_open = datetime.utcnow().weekday() < 5 # Simple mock: Open Mon-Fri

        try:
            snapshot = VaultSnapshot.objects.latest("snapshot_date")
            holdings = VaultAssetHolding.objects.all()
            engine   = ValuationEngine(
                arcx_supply      = float(snapshot.arcx_supply),
                cash_balance_usd = float(snapshot.cash_value_usd),
            )
            arcx_supply = float(snapshot.arcx_supply)
            
            # Fetch previous snapshot to calculate 1D asset changes
            prev_snap = VaultSnapshot.objects.filter(snapshot_date__lt=snapshot.snapshot_date).order_by("-snapshot_date").first()
            if prev_snap:
                spy_change = (float(prices.spy) / float(prev_snap.spy_twap) - 1.0) * 100
                tlt_change = (float(prices.tlt) / float(prev_snap.tlt_twap) - 1.0) * 100
                gld_change = (float(prices.gld) / float(prev_snap.gld_twap) - 1.0) * 100
            else:
                spy_change, tlt_change, gld_change = 0.0, 0.0, 0.0

        except VaultSnapshot.DoesNotExist:
            engine   = ValuationEngine.from_genesis(prices)
            holdings = []   # Day 0: vault is pure cash, no shares yet
            arcx_supply = 1000.0
            spy_change, tlt_change, gld_change = 0.0, 0.0, 0.0

        state = engine.calculate_nav(holdings, prices)

        data = {
            "spy_usd":      Decimal(str(round(prices.spy, 4))),
            "tlt_usd":      Decimal(str(round(prices.tlt, 4))),
            "gld_usd":      Decimal(str(round(prices.gld, 4))),
            "usd_inr":      Decimal(str(round(prices.usd_inr, 4))),
            "nav_usd":      Decimal(str(round(state.nav_usd, 8))),
            "nav_inr":      Decimal(str(round(state.nav_inr, 4))),
            "spy_change":   Decimal(str(round(spy_change, 4))),
            "tlt_change":   Decimal(str(round(tlt_change, 4))),
            "gld_change":   Decimal(str(round(gld_change, 4))),
            "arcx_supply":  Decimal(str(round(arcx_supply, 4))),
            "market_open":  market_open,
            "sources_used": prices.sources_used,
            "fetched_at":   prices.fetched_at,
        }

        serializer = OraclePriceResponseSerializer(data)
        return Response(serializer.data)


class NAVHistoryView(APIView):
    """
    GET /api/v1/nav/history?days=30

    Returns historical NAV data for the price chart.
    Public endpoint -- anyone can audit ARCX's price history.
    Default: last 30 days. Max: 365 days.

    Response:
      {
        "history": [
          {"nav_date": "2025-06-01", "nav_usd": "1.1952", "nav_inr": "99.80", ...},
          ...
        ]
      }
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Oracle"],
        operation_id="nav_history",
        summary="Get historical NAV data",
        description=(
            "**Public endpoint** — no authentication required.\n\n"
            "Returns daily NAV history used to power the price chart. "
            "Default is the last 30 days; maximum is 365 days.\n\n"
            "This data is publicly auditable — anyone can verify ARCX's price history."
        ),
        parameters=[
            OpenApiParameter(
                name="days",
                location=OpenApiParameter.QUERY,
                type=OpenApiTypes.INT,
                required=False,
                default=30,
                description="Number of days of history to return. Default 30, max 365.",
            ),
        ],
        responses={
            200: _NAVHistoryListSchema,
        },
        auth=[],
    )
    def get(self, request):
        days = min(int(request.query_params.get("days", 30)), 365)

        history = (
            NAVHistory.objects
            .order_by("-nav_date")[:days]
            .values("nav_date", "nav_usd", "nav_inr", "dividend_accrued_inr")
        )

        serializer = NAVHistorySerializer(history, many=True)
        return Response({"history": serializer.data})


class TodayNAVView(APIView):
    """
    GET /api/v1/nav/today

    Returns today's published NAV with the SHA256 audit hash.
    The hash lets anyone independently verify this NAV wasn't tampered with.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Oracle"],
        operation_id="nav_today",
        summary="Get today's published NAV",
        description=(
            "**Public endpoint** — no authentication required.\n\n"
            "Returns today's officially published NAV along with a SHA-256 `report_hash`. "
            "The hash is computed from the raw vault data — anyone can independently verify "
            "this NAV was not tampered with after publication."
        ),
        responses={
            200: _TodayNAVSchema,
            404: OpenApiResponse(
                response=_ErrorSchema,
                description="No NAV has been published yet",
                examples=[
                    OpenApiExample("No data", value={"error": "No NAV published yet.", "code": "NO_NAV_DATA"}),
                ],
            ),
        },
        examples=[
            OpenApiExample(
                "Today's NAV",
                response_only=True,
                status_codes=["200"],
                value={
                    "nav_date":             "2025-06-01",
                    "nav_usd":              "1.19520000",
                    "nav_inr":              "99.8000",
                    "dividend_accrued_inr": "0.0250",
                    "report_hash":          "a7b3c9d1e5f2...",
                    "published_at":         "2025-06-01T18:30:00Z",
                },
            ),
        ],
        auth=[],
    )
    def get(self, request):
        try:
            today_nav = NAVHistory.objects.latest("nav_date")
        except NAVHistory.DoesNotExist:
            return Response(
                {"error": "No NAV published yet.", "code": "NO_NAV_DATA"},
                status=404,
            )

        return Response({
            "nav_date":             str(today_nav.nav_date),
            "nav_usd":              str(today_nav.nav_usd),
            "nav_inr":              str(today_nav.nav_inr),
            "dividend_accrued_inr": str(today_nav.dividend_accrued_inr),
            "report_hash":          today_nav.report_hash,
            "published_at":         today_nav.created_at,
        })