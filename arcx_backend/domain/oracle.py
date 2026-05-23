"""
ARCX Multi-Source Oracle — Phase 1B
--------------------------------------
Upgrades from single-source to 3-source oracle with TWAP.

Architecture:
  Source 1: Yahoo Finance   (free, no key — always available)
  Source 2: Alpha Vantage   (free tier, 25 req/day — needs .env key)
  Source 3: Twelve Data     (free tier, 800 req/day — needs .env key)

Price Logic:
  - Each source fetches last 5 days of closing prices
  - TWAP (Time Weighted Average Price) calculated per source
  - Final price = median of all available sources
  - If a source fails or returns bad data, it is silently dropped
  - System works with just Yahoo Finance if keys are missing

Why TWAP over Spot Price:
  A single spot price can be manipulated by one large trade.
  TWAP averages prices over time, making manipulation expensive.
  This is standard in all institutional and DeFi protocols.

Why Median over Mean:
  Mean is skewed by outliers. If one source returns 999 instead of 530,
  mean breaks. Median ignores it automatically.
"""

import os
import statistics
import requests
import yfinance as yf
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from colorama import Fore

load_dotenv()

ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")
TWELVE_DATA_KEY   = os.getenv("TWELVE_DATA_KEY")

ALPHA_VANTAGE_SYMBOLS = {"stocks": "SPY", "bonds": "TLT", "gold": "GLD"}
TWELVE_DATA_SYMBOLS   = {"stocks": "SPY", "bonds": "TLT", "gold": "GLD"}


@dataclass
class MarketPrices:
    """
    Final aggregated prices after multi-source median.
    This is what the ValuationEngine receives.
    """
    spy:          float
    tlt:          float
    gld:          float
    usd_inr:      float
    fetched_at:   datetime
    sources_used: list = field(default_factory=list)
    spy_readings: list = field(default_factory=list)
    tlt_readings: list = field(default_factory=list)
    gld_readings: list = field(default_factory=list)


class YahooSource:
    """Source 1: Yahoo Finance. Always available. No API key."""
    NAME = "Yahoo Finance"

    def fetch_twap(self, ticker: str) -> Optional[float]:
        try:
            data = yf.Ticker(ticker)
            hist = data.history(period="5d", interval="1h")
            if hist.empty or len(hist) < 2:
                hist = data.history(period="5d")
            if hist.empty:
                return None
            return round(float(hist["Close"].mean()), 4)
        except Exception as e:
            print(Fore.RED + f"  [Yahoo] Failed for {ticker}: {e}")
            return None

    def fetch_usd_inr(self) -> Optional[float]:
        try:
            data = yf.Ticker("USDINR=X")
            hist = data.history(period="5d")
            if hist.empty:
                return None
            return round(float(hist["Close"].iloc[-1]), 4)
        except Exception as e:
            print(Fore.RED + f"  [Yahoo] Failed for USD/INR: {e}")
            return None


class AlphaVantageSource:
    """
    Source 2: Alpha Vantage. Free tier: 25 req/day.
    Get key at: https://www.alphavantage.co/support/#api-key
    """
    NAME = "Alpha Vantage"
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self):
        self.key = ALPHA_VANTAGE_KEY

    def is_available(self) -> bool:
        return bool(self.key and "your_" not in str(self.key))

    def fetch_twap(self, symbol: str) -> Optional[float]:
        if not self.is_available():
            return None
        try:
            params = {
                "function":   "TIME_SERIES_DAILY",
                "symbol":     symbol,
                "outputsize": "compact",
                "apikey":     self.key,
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if "Time Series (Daily)" not in data:
                return None
            series = data["Time Series (Daily)"]
            closes = [float(v["4. close"]) for v in list(series.values())[:5]]
            return round(statistics.mean(closes), 4)
        except Exception as e:
            print(Fore.RED + f"  [AlphaVantage] Failed for {symbol}: {e}")
            return None


class TwelveDataSource:
    """
    Source 3: Twelve Data. Free tier: 800 req/day.
    Get key at: https://twelvedata.com/register
    """
    NAME = "Twelve Data"
    BASE_URL = "https://api.twelvedata.com/time_series"

    def __init__(self):
        self.key = TWELVE_DATA_KEY

    def is_available(self) -> bool:
        return bool(self.key and "your_" not in str(self.key))

    def fetch_twap(self, symbol: str) -> Optional[float]:
        if not self.is_available():
            return None
        try:
            params = {
                "symbol":     symbol,
                "interval":   "1day",
                "outputsize": 5,
                "apikey":     self.key,
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if "values" not in data:
                return None
            closes = [float(v["close"]) for v in data["values"]]
            return round(statistics.mean(closes), 4)
        except Exception as e:
            print(Fore.RED + f"  [TwelveData] Failed for {symbol}: {e}")
            return None


class MultiSourceOracle:
    """
    The upgraded ARCX Oracle.

    Aggregation Pipeline:
      1. Query all 3 sources
      2. Collect all valid TWAP readings per asset
      3. Take the median — outliers automatically ignored
      4. Return MarketPrices with full audit trail

    Fallback Logic:
      3 sources → median of 3
      2 sources → median of 2
      1 source  → use that price (with warning)
      0 sources → raise OracleFailureException
    """

    def __init__(self):
        self.yahoo  = YahooSource()
        self.alpha  = AlphaVantageSource()
        self.twelve = TwelveDataSource()

    def fetch_prices(self) -> MarketPrices:
        print(Fore.CYAN + "\n  ── Oracle: Fetching Multi-Source TWAP Prices ───")
        sources_used = []

        spy_readings = self._fetch_asset("SPY", "stocks", sources_used)
        tlt_readings = self._fetch_asset("TLT", "bonds",  sources_used)
        gld_readings = self._fetch_asset("GLD", "gold",   sources_used)

        usd_inr = self.yahoo.fetch_usd_inr()
        if usd_inr is None:
            raise OracleFailureException("Could not fetch USD/INR rate.")

        spy_final = self._median_or_raise(spy_readings, "SPY")
        tlt_final = self._median_or_raise(tlt_readings, "TLT")
        gld_final = self._median_or_raise(gld_readings, "GLD")

        self._print_summary(spy_readings, tlt_readings, gld_readings,
                            spy_final, tlt_final, gld_final, usd_inr, sources_used)

        return MarketPrices(
            spy          = spy_final,
            tlt          = tlt_final,
            gld          = gld_final,
            usd_inr      = usd_inr,
            fetched_at   = datetime.now(),
            sources_used = list(set(sources_used)),
            spy_readings = spy_readings,
            tlt_readings = tlt_readings,
            gld_readings = gld_readings,
        )

    def _fetch_asset(self, ticker: str, asset_key: str, sources_used: list) -> list:
        readings = []

        price = self.yahoo.fetch_twap(ticker)
        if price:
            readings.append((YahooSource.NAME, price))
            if YahooSource.NAME not in sources_used:
                sources_used.append(YahooSource.NAME)

        if self.alpha.is_available():
            price = self.alpha.fetch_twap(ALPHA_VANTAGE_SYMBOLS.get(asset_key, ticker))
            if price:
                readings.append((AlphaVantageSource.NAME, price))
                if AlphaVantageSource.NAME not in sources_used:
                    sources_used.append(AlphaVantageSource.NAME)

        if self.twelve.is_available():
            price = self.twelve.fetch_twap(TWELVE_DATA_SYMBOLS.get(asset_key, ticker))
            if price:
                readings.append((TwelveDataSource.NAME, price))
                if TwelveDataSource.NAME not in sources_used:
                    sources_used.append(TwelveDataSource.NAME)

        return readings

    def _median_or_raise(self, readings: list, asset: str) -> float:
        if not readings:
            raise OracleFailureException(f"All sources failed for: {asset}")
        return round(statistics.median([r[1] for r in readings]), 4)

    def _print_summary(self, spy_r, tlt_r, gld_r, spy, tlt, gld, usd_inr, sources):
        print(Fore.YELLOW + "\n  ── Raw TWAP Readings per Source ────────────────")
        self._print_asset("SPY (Stocks)", spy_r, spy)
        self._print_asset("TLT (Bonds) ", tlt_r, tlt)
        self._print_asset("GLD (Gold)  ", gld_r, gld)
        print(f"  USD/INR      : Rs.{usd_inr:.2f}  (Yahoo spot)")
        print(f"\n  Sources used : {', '.join(sources)}")

    def _print_asset(self, label: str, readings: list, final: float):
        parts = [f"{s}: ${p:.2f}" for s, p in readings]
        print(f"  {label}  {' | '.join(parts)}  =>  Median: ${final:.2f}")


class OracleFailureException(Exception):
    """Raised when no source can provide a valid price."""
    pass
