"""Shared evaluation pipeline for single-run and sweep orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from quadbalance.benchmarks import benchmark_comparison, run_benchmarks
from quadbalance.cross_border_stress import run_cross_border_stress_tests
from quadbalance.long_term_stress import SCENARIOS as LONG_TERM_SCENARIOS, run_long_term_scenario
from quadbalance.metrics import PerformanceMetrics
from quadbalance.metrics import cash_risk_free_rate, compute_metrics
from quadbalance.orchestration_helpers import assess_product_risk, build_profile_suitability
from quadbalance.simulator import SimulationResult, simulate
from quadbalance.stress import StressResult, run_stress_tests
from quadbalance.validation import ValidationResult, apply_long_term_lock_vetoes, evaluate_acceptance


@dataclass
class EvaluationPipelineResult:
    sim_result: SimulationResult
    metrics: PerformanceMetrics
    benchmarks: dict[str, Any]
    stress_results: list[StressResult]
    path_results: list[Any]
    behavior_results: list[Any]
    cross_border_results: list[Any]
    product_risk: Any
    validation: ValidationResult


def run_evaluation_pipeline(
    config,
    prices: pd.DataFrame,
    *,
    backup_prices: dict[str, pd.Series] | None = None,
    profile_thresholds_path: Path | None = None,
    include_long_term: bool = True,
) -> EvaluationPipelineResult:
    benchmarks = run_benchmarks(prices)
    risk_free_annual = cash_risk_free_rate(prices)
    sim_result = simulate(prices, config, backup_prices=backup_prices)
    metrics = compute_metrics(sim_result, config, prices, risk_free_annual=risk_free_annual, inflation_annual=0.03)

    stress_results, _ = run_stress_tests(config, sim_result, prices, backup_prices=backup_prices)
    from quadbalance.behavior_stress import run_behavior_stress_tests
    from quadbalance.path_stress import run_path_stress_tests

    path_results = run_path_stress_tests(config)
    behavior_results = run_behavior_stress_tests(sim_result, metrics, path_results=path_results, stress_results=stress_results)
    cross_border_results = run_cross_border_stress_tests(config)
    product_risk = assess_product_risk(config)

    validation = evaluate_acceptance(
        config=config,
        metrics=metrics,
        benchmarks=benchmarks,
        stress_results=stress_results,
        path_stress_results=path_results,
        behavior_stress_results=behavior_results,
        cross_border_stress_results=cross_border_results,
        product_risk=product_risk,
        qdii_metrics=sim_result.qdii_metrics,
        rebalance_metrics=sim_result.rebalance_metrics,
    )
    validation.benchmark_comparison = benchmark_comparison(metrics, benchmarks)
    validation.profile_suitability = build_profile_suitability(config, metrics, sim_result, profile_thresholds_path)
    if include_long_term:
        validation.long_term_results = [run_long_term_scenario(prices, config, scenario) for scenario in LONG_TERM_SCENARIOS]
        apply_long_term_lock_vetoes(validation)
    else:
        validation.long_term_results = []
    return EvaluationPipelineResult(
        sim_result=sim_result,
        metrics=metrics,
        benchmarks=benchmarks,
        stress_results=stress_results,
        path_results=path_results,
        behavior_results=behavior_results,
        cross_border_results=cross_border_results,
        product_risk=product_risk,
        validation=validation,
    )
