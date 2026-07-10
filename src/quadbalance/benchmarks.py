"""Benchmark portfolio comparison."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quadbalance.config import (
    BENCHMARK_BOND,
    BENCHMARK_CASH,
    BENCHMARK_CSI300,
    BASE_CAPITAL,
    MONTHLY_CONTRIBUTION,
    TRANSACTION_COST,
)
from quadbalance.metrics import PerformanceMetrics, _max_drawdown
from quadbalance.simulator import _first_trading_days_per_month, _portfolio_value


@dataclass
class BenchmarkResult:
    name: str
    annualized_return: float
    max_drawdown: float
    daily_values: pd.Series


def _simulate_single_asset_benchmark(
    prices: pd.Series,
    base_capital: float = BASE_CAPITAL,
    monthly_contribution: float = MONTHLY_CONTRIBUTION,
) -> pd.Series:
    """Buy-and-hold single asset with monthly contributions."""
    month_starts = _first_trading_days_per_month(prices.index)
    shares = 0.0
    values: list[float] = []
    for i, (dt, price) in enumerate(prices.items()):
        if i == 0:
            shares = base_capital / (price * (1 + TRANSACTION_COST))
        elif dt in month_starts:
            shares += monthly_contribution / (price * (1 + TRANSACTION_COST))
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
                amt = base_capital * weights[s]
                shares[s] = amt / (row[s] * (1 + TRANSACTION_COST))
        elif dt in month_starts:
            for s in syms:
                shares[s] += (monthly_contribution * weights[s]) / (
                    row[s] * (1 + TRANSACTION_COST)
                )
        values.append(_portfolio_value(shares, row))
    return pd.Series(values, index=sub.index)


def run_benchmarks(prices: pd.DataFrame) -> dict[str, BenchmarkResult]:
    results: dict[str, BenchmarkResult] = {}

    csi = _simulate_single_asset_benchmark(prices[BENCHMARK_CSI300].dropna())
    mdd, _, _ = _max_drawdown(csi)
    years = len(csi) / 252
    ann = (csi.iloc[-1] / csi.iloc[0]) ** (1 / years) - 1
    results["csi300"] = BenchmarkResult(f"CSI 300 ({BENCHMARK_CSI300})", ann, mdd, csi)

    mix = _simulate_weighted_benchmark(
        prices, {BENCHMARK_CSI300: 0.6, BENCHMARK_BOND: 0.4}
    )
    mdd, _, _ = _max_drawdown(mix)
    years = len(mix) / 252
    ann = (mix.iloc[-1] / mix.iloc[0]) ** (1 / years) - 1
    results["60_40"] = BenchmarkResult(
        f"60/40 ({BENCHMARK_CSI300}/{BENCHMARK_BOND})", ann, mdd, mix
    )

    cash = _simulate_single_asset_benchmark(prices[BENCHMARK_CASH].dropna())
    mdd, _, _ = _max_drawdown(cash)
    years = len(cash) / 252
    ann = (cash.iloc[-1] / cash.iloc[0]) ** (1 / years) - 1
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
