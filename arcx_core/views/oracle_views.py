"""
ARCX Oracle & NAV Views — Phase 3
------------------------------------
Endpoints:
  GET /api/v1/oracle/price   → live NAV + asset prices (public, no auth)
  GET /api/v1/nav/history    → historical NAV data for price chart
  GET /api/v1/nav/today      → today's published NAV
 
oracle/price is intentionally public (no auth required).
Anyone can see the current price. This builds trust.
You can't run a "fair price" platform where the price is secret.
"""
 
import logging
from decimal import Decimal
 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
 
from domain.oracle import MultiSourceOracle, OracleFailureException
from domain.valuation import ValuationEngine
from arcx_core.models import VaultSnapshot, NAVHistory
from arcx_core.serializers import OraclePriceResponseSerializer, NAVHistorySerializer
from arcx_core.exceptions import OracleUnavailableError
 
logger = logging.getLogger("arcx.views.oracle")
 
 
class LivePriceView(APIView):
    """
    GET /api/v1/oracle/price
 
    Public endpoint — no authentication required.
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
 
    def get(self, request):
        try:
            oracle = MultiSourceOracle()
            prices = oracle.fetch_prices()
        except OracleFailureException as e:
            logger.error("Oracle failure on price endpoint: %s", e)
            raise OracleUnavailableError(
                "Live price data is temporarily unavailable. Please retry."
            )
 
        # Calculate current NAV
        try:
            snapshot = VaultSnapshot.objects.latest("snapshot_date")
            engine   = ValuationEngine(
                arcx_supply     = float(snapshot.arcx_supply),
                vault_value_usd = float(snapshot.total_value_usd),
            )
        except VaultSnapshot.DoesNotExist:
            engine = ValuationEngine.from_genesis(prices)
 
        state = engine.calculate_nav(prices)
 
        data = {
            "spy_usd":      Decimal(str(round(prices.spy, 4))),
            "tlt_usd":      Decimal(str(round(prices.tlt, 4))),
            "gld_usd":      Decimal(str(round(prices.gld, 4))),
            "usd_inr":      Decimal(str(round(prices.usd_inr, 4))),
            "nav_usd":      Decimal(str(round(state.nav_usd, 8))),
            "nav_inr":      Decimal(str(round(state.nav_inr, 4))),
            "sources_used": prices.sources_used,
            "fetched_at":   prices.fetched_at,
        }
 
        serializer = OraclePriceResponseSerializer(data)
        return Response(serializer.data)
 
 
class NAVHistoryView(APIView):
    """
    GET /api/v1/nav/history?days=30
 
    Returns historical NAV data for the price chart.
    Public endpoint — anyone can audit ARCX's price history.
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
 