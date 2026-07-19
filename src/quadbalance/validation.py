"""Acceptance criteria evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from quadbalance.benchmarks import BenchmarkResult
from quadbalance.behavior_stress import BehaviorStressResult
from quadbalance.config import StrategyConfig
from quadbalance.cross_border_stress import CrossBorderStressResult, run_cross_border_stress_tests
from quadbalance.lock_integrity import (
    HumanSignOff,
    compute_lockable,
    material_needs_review,
    qdii_quality_reviews,
)
from quadbalance.long_term_stress import LongTermScenarioResult
from quadbalance.metrics import PerformanceMetrics, classify_suitability
from quadbalance.path_stress import PathStressResult
from quadbalance.product_risk import ProductRiskSummary
from quadbalance.simulator import LifecycleResult, QdiiExecutionMetrics, RebalanceExecutionMetrics
from quadbalance.stress import StressResult

if TYPE_CHECKING:
    from quadbalance.sweep import RobustnessSweepResult

MAX_NAV_RECOVERY_DAYS = 252
# Unrecovered drawdowns deeper than this remain hard fail; shallower stay review.
SHALLOW_UNRECOVERED_MDD = -0.10


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
    long_term_results: list[LongTermScenarioResult] = field(default_factory=list)
    profile_suitability: dict[str, dict[str, list[str] | str]] = field(default_factory=dict)
    robustness: object | None = None
    path_stress_results: list[PathStressResult] = field(default_factory=list)
    behavior_stress_results: list[BehaviorStressResult] = field(default_factory=list)
    cross_border_stress_results: list[CrossBorderStressResult] = field(default_factory=list)
    product_risk: ProductRiskSummary | None = None
    needs_review: list[str] = field(default_factory=list)
    lockable: bool = False
    sign_off: HumanSignOff | None = None
    material_needs_review: list[str] = field(default_factory=list)


def apply_long_term_lock_vetoes(validation: ValidationResult) -> None:
    """Escalate seq_inflation thesis-broken into material needs_review / lock veto."""
    from dataclasses import replace

    updated: list = []
    for result in validation.long_term_results:
        seq_rows = getattr(result, "sequence_risk_results", None) or []
        new_result = result
        for row in seq_rows:
            if row.get("scenario_id") != "seq_inflation":
                continue
            if row.get("classification") != "thesis-broken":
                continue
            note = (
                f"Criterion 3: long-term {result.scenario_id} seq_inflation thesis-broken "
                "(inflation-escalating withdrawal)"
            )
            if note not in validation.needs_review:
                validation.needs_review.append(note)
            if result.classification == "normal":
                reasons = list(result.threshold_reasons) + [
                    "seq_inflation: thesis-broken escalates scenario to review-required"
                ]
                new_result = replace(result, classification="review-required", threshold_reasons=reasons)
        updated.append(new_result)
    validation.long_term_results = updated
    validation.material_needs_review = material_needs_review(validation.needs_review)
    validation.lockable = compute_lockable(validation.passed, validation.needs_review, validation.sign_off)


def evaluate_acceptance(
    config: StrategyConfig,
    metrics: PerformanceMetrics,
    benchmarks: dict[str, BenchmarkResult],
    stress_results: list[StressResult],
    robustness: RobustnessSweepResult | None = None,
    path_stress_results: list[PathStressResult] | None = None,
    behavior_stress_results: list[BehaviorStressResult] | None = None,
    cross_border_stress_results: list[CrossBorderStressResult] | None = None,
    product_risk: ProductRiskSummary | None = None,
    qdii_metrics: QdiiExecutionMetrics | None = None,
    rebalance_metrics: RebalanceExecutionMetrics | None = None,
    sequence_risk: dict[str, Any] | None = None,
    sign_off: HumanSignOff | None = None,
) -> ValidationResult:
    failures: list[str] = []
    needs_review: list[str] = []

    if metrics.max_drawdown < -0.25:
        failures.append(f"Criterion 1: max drawdown {metrics.max_drawdown:.1%} > 25%")

    if metrics.worst_year_return < -0.20:
        failures.append(f"Criterion 2: worst year {metrics.worst_year_return:.1%} < -20%")

    if metrics.max_drawdown_recovery_days is None:
        # Always material for lockable; deep unrecovered remains hard fail.
        needs_review.append(
            "Criterion 3: maximum drawdown not fully recovered by window end (unrecovered)"
        )
        if metrics.max_drawdown <= SHALLOW_UNRECOVERED_MDD:
            failures.append("Criterion 3: maximum drawdown never recovered within the test window")
    elif metrics.max_drawdown_recovery_days > MAX_NAV_RECOVERY_DAYS:
        failures.append(
            f"Criterion 3: maximum drawdown recovery took {metrics.max_drawdown_recovery_days} trading days, exceeding {MAX_NAV_RECOVERY_DAYS}"
        )

    for sr in stress_results:
        if sr.classification in {"fail", "thesis-broken"}:
            failures.append(f"Criterion 3: stress {sr.scenario_id} failed ({sr.classification})")
        elif sr.classification == "review-required":
            needs_review.append(f"Criterion 3: stress {sr.scenario_id} requires review")
        elif not sr.passed:
            failures.append(f"Criterion 3: stress {sr.scenario_id} failed ({sr.classification})")
        if sr.scenario_id == "S13" and sr.liquidity_impairment_days >= 252:
            note = "Criterion 3: persistent correlation/liquidity stress indicates prolonged liquidity impairment"
            if sr.classification not in {"fail", "thesis-broken"}:
                needs_review.append(note)

    path_stress_results = path_stress_results or []
    behavior_stress_results = behavior_stress_results or []
    if cross_border_stress_results is None:
        cross_border_stress_results = run_cross_border_stress_tests(config)
    for pr in path_stress_results:
        if pr.classification == "thesis-broken":
            failures.append(f"Criterion 3: path stress {pr.scenario_id} failed")
        elif pr.classification == "review-required":
            needs_review.append(f"Criterion 3: path stress {pr.scenario_id} requires review")
    for br in behavior_stress_results:
        if br.classification == "thesis-broken":
            failures.append(f"Criterion 3: behavior stress {br.rule_id} failed")
        elif br.classification == "review-required":
            needs_review.append(f"Criterion 3: behavior stress {br.rule_id} requires review")
    for cr in cross_border_stress_results:
        if cr.classification == "thesis-broken":
            failures.append(f"Criterion 3: cross-border stress {cr.scenario_id} failed")
        elif cr.classification == "review-required":
            needs_review.append(f"Criterion 3: cross-border stress {cr.scenario_id} requires review")
    if product_risk is not None:
        if product_risk.worst_classification == "thesis-broken":
            failures.append("Criterion 3: product-level risk failed")
        elif product_risk.worst_classification == "review-required" or product_risk.weighted_score >= 40:
            needs_review.append("Criterion 3: product-level risk requires review")

    if qdii_metrics is not None:
        max_dev = rebalance_metrics.max_post_rebalance_deviation if rebalance_metrics is not None else None
        needs_review.extend(
            qdii_quality_reviews(
                pending_cash_days=qdii_metrics.pending_cash_days,
                qdii_friction_months=qdii_metrics.qdii_friction_months,
                avg_qdii_weight_gap=qdii_metrics.avg_qdii_weight_gap,
                max_post_rebalance_deviation=max_dev,
                rebalance_threshold=config.rebalance_threshold,
            )
        )

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
        "macro": "review-required" if any(sr.scenario_id in {"S8", "S9", "S10", "S11", "S12", "S13"} and not sr.passed for sr in stress_results) else "normal",
        "behavioral": (
            "thesis-broken"
            if (
                (metrics.max_drawdown_recovery_days is None and metrics.max_drawdown <= SHALLOW_UNRECOVERED_MDD)
                or (
                    metrics.max_drawdown_recovery_days is not None
                    and metrics.max_drawdown_recovery_days > MAX_NAV_RECOVERY_DAYS
                )
            )
            else (
                "review-required"
                if (
                    metrics.max_drawdown_recovery_days is None
                    or metrics.longest_underwater_days > 252 * 3
                )
                else "normal"
            )
        ),
        "real_return": "thesis-broken" if metrics.worst_rolling_5y_real_return < -0.10 else ("review-required" if metrics.worst_rolling_3y_real_return < 0 else "normal"),
    }

    fill = qdii_metrics.qdii_fill_rate if qdii_metrics is not None else 1.0
    gap = qdii_metrics.avg_qdii_weight_gap if qdii_metrics is not None else 0.0
    friction_months = qdii_metrics.qdii_friction_months if qdii_metrics is not None else 0
    recovery_months = qdii_metrics.qdii_recovery_months if qdii_metrics is not None else 0
    profile_results = classify_suitability(
        config,
        metrics,
        qdii_fill_rate=fill,
        avg_qdii_weight_gap=gap,
        qdii_friction_months=friction_months,
        qdii_recovery_months=recovery_months,
        sequence_risk=sequence_risk or {},
    )
    if robustness is not None and robustness.summary.worst_case is not None and robustness.summary.verdict in {"sensitive", "fragile", "thesis-broken"}:
        failures.append(f"Criterion 6: robustness verdict {robustness.summary.verdict}")
    profile_payload: dict[str, dict[str, list[str] | str]] = {}
    for profile_id, suit in profile_results.items():
        profile_payload[profile_id] = {
            "classification": suit.classification,
            "reasons": suit.reasons,
            "drivers": suit.drivers,
            "warnings": suit.warnings,
            "governance_notes": suit.governance_notes,
        }

    passed = len(failures) == 0
    material = material_needs_review(needs_review)
    result = ValidationResult(
        config.config_id,
        passed,
        failures,
        metrics,
        comp,
        stress_results,
        boundary,
        [],
        [],
        profile_payload,
        robustness,
        needs_review=needs_review,
        lockable=compute_lockable(passed, needs_review, sign_off),
        sign_off=sign_off,
        material_needs_review=material,
    )
    result.path_stress_results = path_stress_results
    result.behavior_stress_results = behavior_stress_results
    result.cross_border_stress_results = cross_border_stress_results
    result.product_risk = product_risk
    return result
