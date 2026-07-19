"""Fund price data fetching and caching (off-exchange NAV + ETF fallback)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import akshare as ak
import pandas as pd

from quadbalance.asset_universe import PRICE_MATRIX_SYMBOLS, PRIMARY_START, QDII_BACKUP_SYMBOLS
from quadbalance.instrument_catalog import BACKTEST_PROXIES, INSTRUMENT_NAMES, BacktestProxy

CACHE_DIR = Path(".cache")
MAX_RETRIES = 3
RETRY_DELAY = 2.0
_SERIES_MEMORY_CACHE: dict[str, pd.Series] = {}


@dataclass(frozen=True)
class BacktestProxyUsage:
    primary: str
    proxy: str
    proxy_start: str
    handoff: str


@dataclass(frozen=True)
class PriceMatrixMeta:
    proxy_usage: tuple[BacktestProxyUsage, ...]


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
        if use_cache and cache.exists():
            df = pd.read_parquet(cache)
            return df["close"]
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
        if use_cache and cache.exists():
            df = pd.read_parquet(cache)
            return df["close"]
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


def _fetch_proxy_prices(proxy: BacktestProxy, use_cache: bool = True) -> pd.Series:
    if proxy.source == "etf":
        return fetch_etf_prices(proxy.code, use_cache=use_cache)
    return fetch_otc_fund_nav(proxy.code, use_cache=use_cache)


def stitch_with_proxy(
    primary: pd.Series,
    proxy: pd.Series,
) -> tuple[pd.Series, BacktestProxyUsage | None]:
    """Splice scaled proxy history before primary fund inception."""
    primary = primary.dropna().sort_index()
    proxy = proxy.dropna().sort_index()
    if primary.empty:
        if proxy.empty:
            raise ValueError("Both primary and proxy price series are empty")
        return proxy, BacktestProxyUsage(
            primary="",
            proxy=proxy.name or "",
            proxy_start=proxy.index[0].strftime("%Y-%m-%d"),
            handoff=proxy.index[0].strftime("%Y-%m-%d"),
        )

    handoff = primary.index[0]
    proxy_hist = proxy[proxy.index < handoff]
    if proxy_hist.empty:
        return primary, None

    scale = primary.iloc[0] / proxy_hist.iloc[-1]
    scaled = proxy_hist * scale
    stitched = pd.concat([scaled, primary])
    stitched = stitched[~stitched.index.duplicated(keep="last")].sort_index()
    stitched.name = primary.name
    return stitched, BacktestProxyUsage(
        primary=str(primary.name or ""),
        proxy=str(proxy.name or ""),
        proxy_start=proxy_hist.index[0].strftime("%Y-%m-%d"),
        handoff=handoff.strftime("%Y-%m-%d"),
    )


def load_backtest_prices(
    symbol: str,
    use_cache: bool = True,
) -> tuple[pd.Series, BacktestProxyUsage | None]:
    """Load prices for backtest, stitching a longer-history proxy when configured."""
    if symbol in _SERIES_MEMORY_CACHE:
        cached = _SERIES_MEMORY_CACHE[symbol]
        proxy_cfg = BACKTEST_PROXIES.get(symbol)
        if proxy_cfg is None:
            return cached, None
        proxy = _SERIES_MEMORY_CACHE.get(proxy_cfg.code)
        if proxy is not None:
            stitched, usage = stitch_with_proxy(cached, proxy)
            if usage is not None:
                usage = BacktestProxyUsage(
                    primary=symbol,
                    proxy=proxy_cfg.code,
                    proxy_start=usage.proxy_start,
                    handoff=usage.handoff,
                )
            return stitched, usage
        return cached, None

    primary = fetch_prices(symbol, use_cache=use_cache)
    primary.name = symbol
    _SERIES_MEMORY_CACHE[symbol] = primary
    proxy_cfg = BACKTEST_PROXIES.get(symbol)
    if proxy_cfg is None:
        return primary, None

    proxy = _fetch_proxy_prices(proxy_cfg, use_cache=use_cache)
    proxy.name = proxy_cfg.code
    _SERIES_MEMORY_CACHE[proxy_cfg.code] = proxy
    stitched, usage = stitch_with_proxy(primary, proxy)
    if usage is not None:
        usage = BacktestProxyUsage(
            primary=symbol,
            proxy=proxy_cfg.code,
            proxy_start=usage.proxy_start,
            handoff=usage.handoff,
        )
    return stitched, usage


def perturb_price_segment(
    series: pd.Series,
    end_exclusive: pd.Timestamp,
    annual_drift: float,
) -> pd.Series:
    """Apply constant annualized drift to dates strictly before end_exclusive.

    Rescales the proxy segment so the last pre-handoff price is unchanged,
    preserving stitch continuity at the handoff boundary.
    """
    if annual_drift == 0.0:
        return series

    series = series.sort_index().copy()
    mask = series.index < end_exclusive
    if not mask.any():
        return series

    proxy_part = series.loc[mask]
    daily_factor = (1.0 + annual_drift) ** (1.0 / 252.0)
    perturbed = proxy_part.copy()
    values = [proxy_part.iloc[0]]
    for i in range(1, len(proxy_part)):
        prev = values[-1]
        ret = proxy_part.iloc[i] / proxy_part.iloc[i - 1] - 1.0
        values.append(prev * (1.0 + ret) * daily_factor)

    perturbed.iloc[:] = values
    if perturbed.iloc[-1] != 0:
        perturbed *= proxy_part.iloc[-1] / perturbed.iloc[-1]

    result = series.copy()
    result.loc[mask] = perturbed
    return result


def build_perturbed_from_baseline(
    baseline_prices: pd.DataFrame,
    meta: PriceMatrixMeta,
    primary_symbol: str,
    annual_drift: float,
) -> pd.DataFrame:
    """Apply drift to one proxy segment using an existing price matrix."""
    if annual_drift == 0.0 or primary_symbol not in baseline_prices.columns:
        return baseline_prices

    usage = next((u for u in meta.proxy_usage if u.primary == primary_symbol), None)
    if usage is None:
        return baseline_prices

    handoff = pd.Timestamp(usage.handoff)
    perturbed = baseline_prices.copy()
    perturbed[primary_symbol] = perturb_price_segment(
        baseline_prices[primary_symbol], handoff, annual_drift
    )
    return perturbed


def build_perturbed_price_matrix(
    primary_symbol: str,
    annual_drift: float,
    symbols: list[str] | None = None,
    start: str = PRIMARY_START,
    use_cache: bool = True,
) -> tuple[pd.DataFrame, PriceMatrixMeta]:
    """Rebuild price matrix with drift applied to one proxy mapping only."""
    prices, meta = load_price_matrix_with_meta(
        symbols=symbols, start=start, use_cache=use_cache
    )
    return build_perturbed_from_baseline(prices, meta, primary_symbol, annual_drift), meta


def load_backup_prices(
    symbols: tuple[str, ...] | None = None,
    use_cache: bool = True,
) -> dict[str, pd.Series]:
    """Load QDII backup prices independently of the alignment matrix."""
    symbols = symbols or QDII_BACKUP_SYMBOLS
    result: dict[str, pd.Series] = {}
    for sym in symbols:
        prices, _ = load_backtest_prices(sym, use_cache=use_cache)
        result[sym] = prices
    return result


def load_price_matrix(
    symbols: list[str] | None = None,
    start: str = PRIMARY_START,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Load aligned close/NAV prices for all symbols."""
    prices, _ = load_price_matrix_with_meta(symbols=symbols, start=start, use_cache=use_cache)
    return prices


def load_market_data(
    symbols: list[str] | None = None,
    backup_symbols: tuple[str, ...] | None = None,
    start: str = PRIMARY_START,
    use_cache: bool = True,
) -> tuple[pd.DataFrame, dict[str, pd.Series], PriceMatrixMeta]:
    """Load main and backup data in one pass, sharing the in-memory cache."""
    prices, meta = load_price_matrix_with_meta(symbols=symbols, start=start, use_cache=use_cache)
    backups = load_backup_prices(symbols=backup_symbols, use_cache=use_cache)
    return prices, backups, meta


MAX_NAV_STALE_DAYS = 5


def _assert_no_backup_alignment(symbols: list[str]) -> None:
    forbidden = set(symbols) & set(QDII_BACKUP_SYMBOLS)
    if forbidden:
        raise ValueError(
            f"Alignment price matrix must not include QDII backups: {sorted(forbidden)}"
        )


def load_price_matrix_with_meta(
    symbols: list[str] | None = None,
    start: str = PRIMARY_START,
    use_cache: bool = True,
) -> tuple[pd.DataFrame, PriceMatrixMeta]:
    """Load aligned prices and record any backtest proxy stitching."""
    symbols = list(symbols or PRICE_MATRIX_SYMBOLS)
    _assert_no_backup_alignment(symbols)
    series_map: dict[str, pd.Series] = {}
    proxy_usage: list[BacktestProxyUsage] = []
    start_ts = pd.Timestamp(start)

    for i, sym in enumerate(symbols):
        if i > 0:
            time.sleep(0.5)
        prices, usage = load_backtest_prices(sym, use_cache=use_cache)
        series_map[sym] = prices[prices.index >= start_ts]
        if usage is not None:
            proxy_usage.append(usage)

    # Bound forward-fill so suspended/missing NAVs do not stay tradable indefinitely.
    raw = pd.DataFrame(series_map).sort_index()
    if raw.empty:
        return raw, PriceMatrixMeta(proxy_usage=tuple(proxy_usage))
    calendar = pd.bdate_range(raw.index.min(), raw.index.max())
    prices = raw.reindex(calendar).ffill(limit=MAX_NAV_STALE_DAYS).dropna(how="any")
    _assert_no_backup_alignment(list(prices.columns))
    return prices, PriceMatrixMeta(proxy_usage=tuple(proxy_usage))


def format_proxy_usage_markdown(meta: PriceMatrixMeta) -> str:
    """Render backtest proxy stitching notes for reports."""
    if not meta.proxy_usage:
        return ""
    lines = [
        "## Backtest Proxies",
        "",
        "Longer-history instruments used before primary fund inception:",
        "",
        "| Primary | Proxy | Proxy Period | Handoff to Primary |",
        "|---------|-------|--------------|--------------------|",
    ]
    for usage in meta.proxy_usage:
        primary_name = INSTRUMENT_NAMES.get(usage.primary, usage.primary)
        proxy_name = INSTRUMENT_NAMES.get(usage.proxy, usage.proxy)
        lines.append(
            f"| {usage.primary} {primary_name} | {usage.proxy} {proxy_name} | "
            f"{usage.proxy_start} → {usage.handoff} | {usage.handoff} |"
        )
    lines.append("")
    return "\n".join(lines)


def instrument_start_dates(prices: pd.DataFrame) -> dict[str, str]:
    """First available date per instrument."""
    return {col: prices[col].first_valid_index().strftime("%Y-%m-%d") for col in prices.columns}
