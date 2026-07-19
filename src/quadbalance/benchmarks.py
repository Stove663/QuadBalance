"""Benchmark portfolio comparison."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quadbalance.asset_universe import (
    BASE_CAPITAL,
    BENCHMARK_BOND,
    BENCHMARK_CASH,
    BENCHMARK_CSI300,
    MONTHLY_CONTRIBUTION,
)
from quadbalance.fees import purchase_fee_rate
from quadbalance.metrics import (
    PerformanceMetrics,
    _max_drawdown,
    annualized_twr,
    dca_schedule_cashflows,
    time_weighted_daily_returns,
)
from quadbalance.simulator import _first_trading_days_per_month, _portfolio_value


@dataclass
class BenchmarkResult:
    name: str
    annualized_return: float
    max_drawdown: float
    daily_values: pd.Series


def _ann_from_dca_values(values: pd.Series, base_capital: float, monthly_contribution: float) -> float:
    month_starts = _first_trading_days_per_month(values.index)
    cashflows = dca_schedule_cashflows(values.index, base_capital, monthly_contribution, month_starts)
    return annualized_twr(time_weighted_daily_returns(values, cashflows))


def _simulate_single_asset_benchmark(
    symbol: str,
    prices: pd.Series,
    base_capital: float = BASE_CAPITAL,
    monthly_contribution: float = MONTHLY_CONTRIBUTION,
) -> pd.Series:
    """Buy-and-hold single asset with monthly contributions."""
    fee = purchase_fee_rate(symbol)
    month_starts = _first_trading_days_per_month(prices.index)
    shares = 0.0
    values: list[float] = []
    for i, (dt, price) in enumerate(prices.items()):
        if i == 0:
            shares = base_capital / (price * (1 + fee))
        elif dt in month_starts:
            shares += monthly_contribution / (price * (1 + fee))
        values.append(shares * price)
    return pd.Series(values, index=prices.index)


def _simulate_weighted_benchmark(
    prices: pd.DataFrame,
    weights: dict[str, float],
    base_capital: float = BASE_CAPITAL,
    monthly_contribution: float = MONTHLY_CONTRIBUTION,
) -> pd.Series:
    """Static-weight multi-asset with monthly contributions."""
    syms = [s for s in weights if s in prices.columns]
    sub = prices[syms].dropna(how="any")
    month_starts = _first_trading_days_per_month(sub.index)
    shares = {s: 0.0 for s in syms}
    values: list[float] = []

    for i, (dt, row) in enumerate(sub.iterrows()):
        if i == 0:
            for s in syms:
                fee = purchase_fee_rate(s)
                amt = base_capital * weights[s]
                shares[s] = amt / (row[s] * (1 + fee))
        elif dt in month_starts:
            for s in syms:
                fee = purchase_fee_rate(s)
                shares[s] += (monthly_contribution * weights[s]) / (
                    row[s] * (1 + fee)
                )
        values.append(_portfolio_value(shares, row))
    return pd.Series(values, index=sub.index)


def run_benchmarks(prices: pd.DataFrame) -> dict[str, BenchmarkResult]:
    results: dict[str, BenchmarkResult] = {}

    csi = _simulate_single_asset_benchmark(BENCHMARK_CSI300, prices[BENCHMARK_CSI300].dropna())
    mdd, _, _ = _max_drawdown(csi)
    ann = _ann_from_dca_values(csi, BASE_CAPITAL, MONTHLY_CONTRIBUTION)
    results["csi300"] = BenchmarkResult(f"CSI 300 ({BENCHMARK_CSI300})", ann, mdd, csi)

    mix = _simulate_weighted_benchmark(
        prices, {BENCHMARK_CSI300: 0.6, BENCHMARK_BOND: 0.4}
    )
    mdd, _, _ = _max_drawdown(mix)
    ann = _ann_from_dca_values(mix, BASE_CAPITAL, MONTHLY_CONTRIBUTION)
    results["60_40"] = BenchmarkResult(
        f"60/40 ({BENCHMARK_CSI300}/{BENCHMARK_BOND})", ann, mdd, mix
    )

    cash = _simulate_single_asset_benchmark(BENCHMARK_CASH, prices[BENCHMARK_CASH].dropna())
    mdd, _, _ = _max_drawdown(cash)
    ann = _ann_from_dca_values(cash, BASE_CAPITAL, MONTHLY_CONTRIBUTION)
    results["cash"] = BenchmarkResult(f"Cash ({BENCHMARK_CASH})", ann, mdd, cash)

    return results


def benchmark_comparison(
    metrics: PerformanceMetrics,
    benchmarks: dict[str, BenchmarkResult],
) -> dict[str, dict[str, float]]:
    """Relative return and max drawdown vs each benchmark."""
    comp: dict[str, dict[str, float]] = {}
    for key, bench in benchmarks.items():
        comp[key] = {
            "relative_return": metrics.annualized_return - bench.annualized_return,
            "relative_max_drawdown": metrics.max_drawdown - bench.max_drawdown,
        }
    return comp
