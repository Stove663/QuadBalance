"""Acceptance criteria evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field

from quadbalance.benchmarks import BenchmarkResult
from quadbalance.config import StrategyConfig
from quadbalance.metrics import PerformanceMetrics, ProfileSuitability, classify_suitability
from quadbalance.simulator import LifecycleResult
from quadbalance.stress import StressResult

MAX_NAV_RECOVERY_DAYS = 252


@dataclass
class ValidationResult:
    config_id: str
    passed: bool
    failure_reasons: list[str]
    metrics: PerformanceMetrics
    benchmark_comparison: dict[str, dict[str, float]]
    stress_results: list[StressResult]
    boundary_classifications: dict[str, str] = field(default_factory=dict)
    lifecycle_results: list[LifecycleResult] = field(default_factory=list)
    profile_suitability: dict[str, dict[str, list[str] | str]] = field(default_factory=dict)


def evaluate_acceptance(
    config: StrategyConfig,
    metrics: PerformanceMetrics,
    benchmarks: dict[str, BenchmarkResult],
    stress_results: list[StressResult],
) -> ValidationResult:
    failures: list[str] = []

    if metrics.max_drawdown < -0.25:
        failures.append(f"Criterion 1: max drawdown {metrics.max_drawdown:.1%} > 25%")

    if metrics.worst_year_return < -0.20:
        failures.append(f"Criterion 2: worst year {metrics.worst_year_return:.1%} < -20%")

    if metrics.max_drawdown_recovery_days is None:
        failures.append("Criterion 3: maximum drawdown never recovered within the test window")
    elif metrics.max_drawdown_recovery_days > MAX_NAV_RECOVERY_DAYS:
        failures.append(
            f"Criterion 3: maximum drawdown recovery took {metrics.max_drawdown_recovery_days} trading days, exceeding {MAX_NAV_RECOVERY_DAYS}"
        )

    for sr in stress_results:
        if not sr.passed:
            failures.append(f"Criterion 3: stress {sr.scenario_id} failed")

    cash_bench = benchmarks["cash"]
    if metrics.annualized_return < cash_bench.annualized_return + 0.02:
        failures.append(
            f"Criterion 4: return {metrics.annualized_return:.1%} does not exceed cash benchmark by 2%"
        )

    bench_6040 = benchmarks["60_40"]
    return_ok = metrics.annualized_return >= bench_6040.annualized_return - 0.02
    drawdown_ok = metrics.max_drawdown > bench_6040.max_drawdown + 0.05
    if not (return_ok or drawdown_ok):
        failures.append("Criterion 5: neither within 2% of 60/40 return nor 5% lower max drawdown")

    comp = {
        key: {
            "relative_return": metrics.annualized_return - b.annualized_return,
            "relative_max_drawdown": metrics.max_drawdown - b.max_drawdown,
        }
        for key, b in benchmarks.items()
    }

    boundary = {
        "macro": "review-required" if any(sr.scenario_id in {"S8", "S9", "S10", "S11", "S12"} and not sr.passed for sr in stress_results) else "normal",
        "behavioral": "thesis-broken" if metrics.max_drawdown_recovery_days is None or metrics.max_drawdown_recovery_days > MAX_NAV_RECOVERY_DAYS else ("review-required" if metrics.longest_underwater_days > 252 * 3 else "normal"),
        "real_return": "thesis-broken" if metrics.worst_rolling_5y_real_return < -0.10 else ("review-required" if metrics.worst_rolling_3y_real_return < 0 else "normal"),
    }

    profile_results = classify_suitability(config, metrics, qdii_fill_rate=1.0, avg_qdii_weight_gap=0.0)
    profile_payload: dict[str, dict[str, list[str] | str]] = {}
    for profile_id, suit in profile_results.items():
        profile_payload[profile_id] = {
            "classification": suit.classification,
            "reasons": suit.reasons,
            "drivers": suit.drivers,
            "warnings": suit.warnings,
            "governance_notes": suit.governance_notes,
        }

    return ValidationResult(config.config_id, len(failures) == 0, failures, metrics, comp, stress_results, boundary, [], profile_payload)
