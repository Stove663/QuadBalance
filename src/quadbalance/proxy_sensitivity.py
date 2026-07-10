"""Proxy tracking-error sensitivity analysis and segmented era reporting."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from quadbalance.benchmarks import BenchmarkResult
from quadbalance.config import BACKTEST_PROXIES, StrategyConfig
from quadbalance.data import PriceMatrixMeta, build_perturbed_from_baseline
from quadbalance.metrics import PerformanceMetrics, _max_drawdown, compute_metrics
from quadbalance.simulator import simulate

PROXY_ERA_START = pd.Timestamp("2013-01-01")
PROXY_ERA_END = pd.Timestamp("2016-12-31")
PRIMARY_ERA_START = pd.Timestamp("2017-01-01")
DRIFT_LEVELS = (-0.02, -0.01, 0.01, 0.02)


@dataclass(frozen=True)
class SensitivityScenario:
    scenario_id: str
    primary_symbol: str | None
    annual_drift: float


@dataclass
class SegmentMetrics:
    era: str
    start: str
    end: str
    annualized_return: float
    max_drawdown: float
    positive_years_pct: float


@dataclass
class SensitivityRow:
    scenario_id: str
    primary_symbol: str
    annual_drift: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    worst_year_return: float
    validation_passed: bool


@dataclass
class SensitivitySummary:
    baseline_return: float
    min_return: float
    max_return: float
    min_drawdown: float
    max_drawdown: float
    most_impactful_proxy: str
    max_return_impact: float
    rows: list[SensitivityRow]


def generate_sensitivity_scenarios() -> list[SensitivityScenario]:
    scenarios = [SensitivityScenario("baseline", None, 0.0)]
    for primary in BACKTEST_PROXIES:
        for drift in DRIFT_LEVELS:
            pct = int(drift * 100)
            sign = "+" if drift > 0 else ""
            scenarios.append(
                SensitivityScenario(f"{primary}_proxy_{sign}{pct}pct", primary, drift)
            )
    return scenarios


def compute_segment_metrics(daily_values: pd.Series) -> list[SegmentMetrics]:
    segments = [
        ("proxy_era", PROXY_ERA_START, PROXY_ERA_END),
        ("primary_era", PRIMARY_ERA_START, daily_values.index[-1]),
    ]
    results: list[SegmentMetrics] = []

    for era, start, end in segments:
        sub = daily_values[(daily_values.index >= start) & (daily_values.index <= end)]
        if len(sub) < 2:
            continue
        total = sub.iloc[-1] / sub.iloc[0] - 1.0
        years = len(sub) / 252.0
        ann = (1.0 + total) ** (1.0 / years) - 1.0 if years > 0 else 0.0
        mdd, _, _ = _max_drawdown(sub)
        annual = sub.groupby(sub.index.year).apply(lambda s: s.iloc[-1] / s.iloc[0] - 1.0)
        pos_pct = float((annual > 0).mean()) if len(annual) else 0.0
        results.append(
            SegmentMetrics(
                era=era,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d") if isinstance(end, pd.Timestamp) else str(end),
                annualized_return=ann,
                max_drawdown=mdd,
                positive_years_pct=pos_pct,
            )
        )
    return results


def _run_scenario(
    config: StrategyConfig,
    scenario: SensitivityScenario,
    baseline_prices: pd.DataFrame,
    price_meta: PriceMatrixMeta,
    benchmarks: dict[str, BenchmarkResult],
    rf: float,
    backup_prices: dict[str, pd.Series] | None = None,
) -> tuple[SensitivityRow, pd.Series]:
    if scenario.primary_symbol is None:
        prices = baseline_prices
    else:
        prices = build_perturbed_from_baseline(
            baseline_prices,
            price_meta,
            scenario.primary_symbol,
            scenario.annual_drift,
        )

    result = simulate(prices, config, backup_prices=backup_prices)
    no_rebal = simulate(prices, config, enable_rebalance=False, backup_prices=backup_prices)
    metrics = compute_metrics(result, config, prices, rf, no_rebal)

    cash_bench = benchmarks["cash"]
    bench_6040 = benchmarks["60_40"]
    return_ok = metrics.annualized_return >= bench_6040.annualized_return - 0.02
    drawdown_ok = metrics.max_drawdown > bench_6040.max_drawdown + 0.05
    validation_passed = (
        metrics.max_drawdown >= -0.25
        and metrics.worst_year_return >= -0.20
        and metrics.annualized_return >= cash_bench.annualized_return + 0.02
        and (return_ok or drawdown_ok)
    )

    row = SensitivityRow(
        scenario_id=scenario.scenario_id,
        primary_symbol=scenario.primary_symbol or "",
        annual_drift=scenario.annual_drift,
        annualized_return=metrics.annualized_return,
        max_drawdown=metrics.max_drawdown,
        sharpe_ratio=metrics.sharpe_ratio,
        worst_year_return=metrics.worst_year_return,
        validation_passed=validation_passed,
    )
    return row, result.daily_values


def run_sensitivity(
    config: StrategyConfig,
    baseline_prices: pd.DataFrame,
    price_meta: PriceMatrixMeta,
    benchmarks: dict[str, BenchmarkResult],
    rf: float,
    backup_prices: dict[str, pd.Series] | None = None,
) -> tuple[SensitivitySummary, list[SegmentMetrics], pd.DataFrame]:
    """Run all sensitivity scenarios for one configuration."""
    rows: list[SensitivityRow] = []
    baseline_daily: pd.Series | None = None
    impacts: dict[str, float] = {}

    for scenario in generate_sensitivity_scenarios():
        row, daily = _run_scenario(
            config,
            scenario,
            baseline_prices,
            price_meta,
            benchmarks,
            rf,
            backup_prices=backup_prices,
        )
        rows.append(row)
        if scenario.scenario_id == "baseline":
            baseline_daily = daily
            baseline_return = row.annualized_return
        elif scenario.primary_symbol:
            impacts[scenario.primary_symbol] = max(
                impacts.get(scenario.primary_symbol, 0.0),
                abs(row.annualized_return - baseline_return),
            )

    assert baseline_daily is not None
    segments = compute_segment_metrics(baseline_daily)

    returns = [r.annualized_return for r in rows]
    drawdowns = [r.max_drawdown for r in rows]
    most_impactful = max(impacts, key=impacts.get) if impacts else ""

    summary = SensitivitySummary(
        baseline_return=baseline_return,
        min_return=min(returns),
        max_return=max(returns),
        min_drawdown=min(drawdowns),
        max_drawdown=max(drawdowns),
        most_impactful_proxy=most_impactful,
        max_return_impact=impacts.get(most_impactful, 0.0),
        rows=rows,
    )
    df = pd.DataFrame([asdict(r) for r in rows])
    return summary, segments, df


def write_sensitivity_outputs(
    summary: SensitivitySummary,
    segments: list[SegmentMetrics],
    sensitivity_df: pd.DataFrame,
    output_dir: Path,
    config_id: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    out = sensitivity_df.copy()
    out.insert(0, "config_id", config_id)
    out.to_csv(output_dir / "proxy_sensitivity.csv", index=False)

    seg_df = pd.DataFrame([asdict(s) for s in segments])
    seg_df.insert(0, "config_id", config_id)
    seg_df.to_csv(output_dir / "segment_metrics.csv", index=False)


def format_sensitivity_summary_markdown(summary: SensitivitySummary) -> str:
    lines = [
        "## Proxy Sensitivity Summary",
        "",
        "Independent ±1%/±2% annualized drift on each proxy segment (pre-handoff):",
        "",
        "| Metric | Baseline | Min | Max |",
        "|--------|----------|-----|-----|",
        f"| Annualized return | {summary.baseline_return:.2%} | {summary.min_return:.2%} | {summary.max_return:.2%} |",
        f"| Max drawdown | — | {summary.min_drawdown:.2%} | {summary.max_drawdown:.2%} |",
        "",
        f"Most impactful proxy mapping: **{summary.most_impactful_proxy}** "
        f"(max return deviation {summary.max_return_impact:.2%})",
        "",
    ]
    return "\n".join(lines)
