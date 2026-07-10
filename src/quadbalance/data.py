"""Fund price data fetching and caching (off-exchange NAV + ETF fallback)."""

from __future__ import annotations

import time
from pathlib import Path

import akshare as ak
import pandas as pd

from quadbalance.config import ALL_SYMBOLS, PRIMARY_START

CACHE_DIR = Path(".cache")
MAX_RETRIES = 3
RETRY_DELAY = 2.0


def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / f"{symbol}.parquet"


def _is_otc_fund(symbol: str) -> bool:
    """Six-digit codes are treated as off-exchange open-end funds."""
    return len(symbol) == 6 and symbol.isdigit()


def fetch_otc_fund_nav(symbol: str, use_cache: bool = True) -> pd.Series:
    """Fetch daily unit NAV for an off-exchange open-end fund."""
    cache = _cache_path(symbol)
    if use_cache and cache.exists():
        df = pd.read_parquet(cache)
        return df["close"]

    last_error: Exception | None = None
    raw = None
    for attempt in range(MAX_RETRIES):
        try:
            raw = ak.fund_open_fund_info_em(symbol=symbol, indicator="单位净值走势")
            break
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    if raw is None or raw.empty:
        raise RuntimeError(f"Failed to fetch OTC fund {symbol}") from last_error

    df = raw.rename(columns={"净值日期": "date", "单位净值": "close"})
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df = df[["close"]].astype(float)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache)
    return df["close"]


def fetch_etf_prices(symbol: str, use_cache: bool = True) -> pd.Series:
    """Fetch daily adjusted close for an on-exchange ETF (Sina source)."""
    cache = _cache_path(symbol)
    if use_cache and cache.exists():
        df = pd.read_parquet(cache)
        return df["close"]

    sina_symbol = f"sh{symbol}"
    last_error: Exception | None = None
    raw = None
    for attempt in range(MAX_RETRIES):
        try:
            raw = ak.fund_etf_hist_sina(symbol=sina_symbol)
            break
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    if raw is None:
        raise RuntimeError(f"Failed to fetch ETF {symbol}") from last_error

    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df = df[["close"]].astype(float)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache)
    return df["close"]


def fetch_prices(symbol: str, use_cache: bool = True) -> pd.Series:
    """Fetch prices for OTC fund or exchange ETF by symbol format."""
    if _is_otc_fund(symbol):
        return fetch_otc_fund_nav(symbol, use_cache=use_cache)
    return fetch_etf_prices(symbol, use_cache=use_cache)


def load_price_matrix(
    symbols: list[str] | None = None,
    start: str = PRIMARY_START,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Load aligned close/NAV prices for all symbols."""
    symbols = symbols or ALL_SYMBOLS
    series_map: dict[str, pd.Series] = {}
    start_ts = pd.Timestamp(start)

    for i, sym in enumerate(symbols):
        if i > 0:
            time.sleep(0.5)
        prices = fetch_prices(sym, use_cache=use_cache)
        series_map[sym] = prices[prices.index >= start_ts]

    prices = pd.DataFrame(series_map).sort_index().ffill().dropna(how="any")
    return prices


def instrument_start_dates(prices: pd.DataFrame) -> dict[str, str]:
    """First available date per instrument."""
    return {col: prices[col].first_valid_index().strftime("%Y-%m-%d") for col in prices.columns}
