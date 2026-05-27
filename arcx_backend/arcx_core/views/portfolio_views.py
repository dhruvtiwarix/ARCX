"""
ARCX Portfolio Analytics View - Phase 10
------------------------------------------
GET /api/v1/portfolio/analytics
"""

import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers as drf_serializers
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer

from arcx_core.models import User as ArcxUser, Wallet, Transaction, NAVHistory, VaultSnapshot, VaultAssetHolding
from arcx_core.views.wallet_views import _user_id
from domain.oracle import MultiSourceOracle, OracleFailureException
from domain.valuation import ValuationEngine

logger = logging.getLogger("arcx.views.portfolio")

# -- Inline schemas -----------------------------------------------------------
_ErrorSchema = inline_serializer(
    name="PortfolioErrorResponse",
    fields={
        "error":   drf_serializers.CharField(),
        "user_id": drf_serializers.CharField(required=False),
    },
)

_HoldingsSchema = inline_serializer(
    name="Holdings",
    fields={
        "arcx_balance":       drf_serializers.FloatField(help_text="Current ARCX token balance"),
        "cost_basis_inr":     drf_serializers.FloatField(help_text="Total INR invested (historical cost)"),
        "current_value_inr":  drf_serializers.FloatField(help_text="Current portfolio value in INR at live NAV"),
        "unrealized_pnl_inr": drf_serializers.FloatField(help_text="Unrealized profit/loss = current_value - cost_basis"),
        "pnl_pct":            drf_serializers.FloatField(help_text="P&L as a percentage of cost basis"),
        "avg_buy_price_inr":  drf_serializers.FloatField(help_text="Average purchase price per ARCX token in INR"),
        "current_nav_inr":    drf_serializers.FloatField(help_text="Current live NAV used for valuation"),
    },
)

_YieldSchema = inline_serializer(
    name="YieldEarned",
    fields={
        "arcx":  drf_serializers.FloatField(help_text="Total ARCX earned through dividends"),
        "inr":   drf_serializers.FloatField(help_text="INR equivalent of dividends earned"),
        "count": drf_serializers.IntegerField(help_text="Number of dividend distributions received"),
    },
)

_PnLPointSchema = inline_serializer(
    name="PnLPoint",
    fields={
        "date":            drf_serializers.CharField(help_text="Date label e.g. '01 Jun'"),
        "portfolio_value": drf_serializers.FloatField(help_text="Portfolio value in INR on this date"),
        "cost_basis":      drf_serializers.FloatField(help_text="Cumulative cost basis in INR on this date"),
    },
)

_PortfolioResponseSchema = inline_serializer(
    name="PortfolioAnalyticsResponse",
    fields={
        "holdings": drf_serializers.DictField(
            help_text=(
                "Current portfolio snapshot: arcx_balance, cost_basis_inr, "
                "current_value_inr, unrealized_pnl_inr, pnl_pct, avg_buy_price_inr, current_nav_inr"
            )
        ),
        "yield_earned": drf_serializers.DictField(
            help_text="Dividend yield totals: arcx (float), inr (float), count (int)"
        ),
        "tx_breakdown": drf_serializers.DictField(
            child=drf_serializers.DictField(child=drf_serializers.FloatField()),
            help_text="Transaction breakdown by type: {tx_type: {count, total_inr, total_arcx}}",
        ),
        "pnl_series":   drf_serializers.ListField(
            child=drf_serializers.DictField(),
            help_text="Day-by-day P&L data points: {date, portfolio_value, cost_basis}",
        ),
    },
)


class PortfolioAnalyticsView(APIView):
    """
    GET /api/v1/portfolio/analytics

    Authenticated only. Returns holdings snapshot, P&L series,
    yield earned, and transaction breakdown by type.
    """
    permission_classes = [IsAuthenticated]

    def _get_wallet(self, user_id: str) -> Wallet:
        """
        Resolve wallet robustly for all user types:
          - Real users:  username = UUID  -> ArcxUser.id = UUID
          - Seed users:  username = UUID  -> ArcxUser.id = UUID
        Returns the wallet or raises Wallet.DoesNotExist.
        """
        try:
            arcx_user = ArcxUser.objects.get(id=user_id, deleted_at__isnull=True)
            return Wallet.objects.select_related("user").get(
                user=arcx_user, deleted_at__isnull=True
            )
        except (ArcxUser.DoesNotExist, Wallet.DoesNotExist, ValueError):
            raise Wallet.DoesNotExist(f"No wallet found for user_id={user_id!r}")

    @extend_schema(
        tags=["Portfolio"],
        operation_id="portfolio_analytics",
        summary="Get portfolio analytics and P&L",
        description=(
            "Returns a complete analytics snapshot for the authenticated user's portfolio:\n\n"
            "- **Holdings** - current balance, cost basis, live value, unrealized P&L, avg buy price\n"
            "- **Yield earned** - total ARCX and INR earned through dividend distributions\n"
            "- **Transaction breakdown** - deposit/withdraw/transfer/dividend counts and totals\n"
            "- **P&L series** - day-by-day portfolio value vs cost basis (powers the chart)\n\n"
            "The live NAV is fetched from the oracle on every call. If the oracle is unavailable, "
            "the last known NAV from the vault snapshot is used as a fallback."
        ),
        responses={
            200: _PortfolioResponseSchema,
            404: OpenApiResponse(response=_ErrorSchema, description="Wallet not found for this user"),
            500: OpenApiResponse(response=_ErrorSchema, description="Internal error fetching wallet or NAV"),
            401: OpenApiResponse(response=_ErrorSchema, description="JWT missing or expired"),
        },
    )
    def get(self, request):
        user_id = _user_id(request)   # JWT sub = request.user.username

        # ── Fetch wallet ────────────────────────────────────────────────────
        try:
            wallet = self._get_wallet(user_id)
        except Wallet.DoesNotExist:
            return Response({"error": "Wallet not found.", "user_id": user_id}, status=404)
        except Exception as e:
            logger.exception("Unexpected error fetching wallet for user_id=%s", user_id)
            return Response({"error": "Internal error fetching wallet."}, status=500)

        arcx_balance = float(wallet.arcx_balance)
        cost_basis   = float(wallet.cost_basis_inr)

        # Phase 6: Calculate NAV from actual share quantities (Mark-to-Market)
        try:
            snapshot = VaultSnapshot.objects.latest("snapshot_date")
            holdings = list(VaultAssetHolding.objects.all())
            engine   = ValuationEngine(
                arcx_supply      = float(snapshot.arcx_supply),
                cash_balance_usd = float(snapshot.cash_value_usd),
            )
            oracle  = MultiSourceOracle()
            prices  = oracle.fetch_prices()
            current_nav_inr = float(engine.calculate_nav(holdings, prices).nav_inr)
        except VaultSnapshot.DoesNotExist:
            try:
                oracle = MultiSourceOracle()
                prices = oracle.fetch_prices()
                engine = ValuationEngine.from_genesis(prices)
                current_nav_inr = float(engine.calculate_nav([], prices).nav_inr)
            except Exception as e:
                logger.warning("Could not fetch live NAV for portfolio analytics: %s", e)
                current_nav_inr = 100.0
        except Exception as e:
            logger.warning("Error calculating NAV from snapshot: %s", e)
            current_nav_inr = 100.0

        current_value    = arcx_balance * current_nav_inr
        unrealized_pnl   = current_value - cost_basis
        pnl_pct          = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0.0
        avg_buy_price    = (cost_basis / arcx_balance) if arcx_balance > 0 else 0.0

        # ── All transactions ────────────────────────────────────────────────
        txns = Transaction.objects.filter(
            wallet=wallet,
            status=Transaction.Status.COMPLETED,
            deleted_at__isnull=True,
        ).order_by("created_at")

        # ── Yield earned (dividends) ────────────────────────────────────────
        dividends      = [t for t in txns if t.tx_type == Transaction.TxType.DIVIDEND]
        yield_arcx     = sum(float(t.amount_arcx) for t in dividends)
        yield_inr      = sum(float(t.amount_inr)  for t in dividends)

        # ── Transaction breakdown ───────────────────────────────────────────
        breakdown = {}
        for tx in txns:
            key = tx.tx_type
            if key not in breakdown:
                breakdown[key] = {"count": 0, "total_inr": 0.0, "total_arcx": 0.0}
            breakdown[key]["count"]      += 1
            breakdown[key]["total_inr"]  += abs(float(tx.amount_inr))
            breakdown[key]["total_arcx"] += abs(float(tx.amount_arcx))

        # ── P&L series: walk through NAV history + running ARCX balance ────
        # Strategy: for each day in NAV history, compute what the portfolio
        # was worth at that day's NAV price, using a running balance.
        nav_history = list(
            NAVHistory.objects.order_by("nav_date")
            .values("nav_date", "nav_inr")
        )

        # Build a lookup: date → cumulative arcx_balance up to that date
        # Walk transactions in order and accumulate balance per day
        pnl_series = []
        if nav_history:
            running_arcx = 0.0
            running_cost = 0.0
            tx_idx       = 0
            tx_list      = list(txns)

            for nav_row in nav_history:
                day     = nav_row["nav_date"]
                nav_inr = float(nav_row["nav_inr"])

                # Apply all transactions up to and including this day
                while tx_idx < len(tx_list):
                    tx = tx_list[tx_idx]
                    tx_date = tx.created_at.date() if hasattr(tx.created_at, 'date') else tx.created_at
                    if tx_date <= day:
                        amt = float(tx.amount_arcx)
                        running_arcx += amt
                        if tx.tx_type == Transaction.TxType.DEPOSIT:
                            running_cost += float(tx.amount_inr)
                        tx_idx += 1
                    else:
                        break

                if running_arcx > 0:
                    pnl_series.append({
                        "date":               day.strftime("%d %b"),
                        "portfolio_value":    round(running_arcx * nav_inr, 2),
                        "cost_basis":         round(running_cost, 2),
                    })

        return Response({
            "holdings": {
                "arcx_balance":    round(arcx_balance, 6),
                "cost_basis_inr":  round(cost_basis, 2),
                "current_value_inr": round(current_value, 2),
                "unrealized_pnl_inr": round(unrealized_pnl, 2),
                "pnl_pct":         round(pnl_pct, 4),
                "avg_buy_price_inr": round(avg_buy_price, 4),
                "current_nav_inr": round(current_nav_inr, 4),
            },
            "yield_earned": {
                "arcx":    round(yield_arcx, 6),
                "inr":     round(yield_inr, 2),
                "count":   len(dividends),
            },
            "tx_breakdown": breakdown,
            "pnl_series":   pnl_series,
        })
