"""Validate a single StrategyConfig and write run artifacts (no full sweep)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from quadbalance.artifacts import write_run_artifacts
from quadbalance.asset_universe import QDII_BACKUP_SYMBOLS
from quadbalance.benchmarks import benchmark_comparison, run_benchmarks
from quadbalance.config import StrategyConfig
from quadbalance.cross_border_stress import run_cross_border_stress_tests
from quadbalance.data import load_market_data
from quadbalance.long_term_stress import run_long_term_scenario
from quadbalance.long_term_stress import SCENARIOS as LONG_TERM_SCENARIOS
from quadbalance.metrics import cash_risk_free_rate, compute_metrics
from quadbalance.profile_thresholds import DEFAULT_INVESTOR_PROFILES
from quadbalance.simulator import simulate
from quadbalance.stress import run_stress_tests
from quadbalance.sweep import (
    _build_profile_suitability,
    assess_product_risk,
    collect_required_symbols,
    run_behavior_stress_tests,
    run_path_stress_tests,
)
from quadbalance.validation import ValidationResult, evaluate_acceptance


def run_single_config(
    config: StrategyConfig,
    output_dir: Path,
    *,
    use_cache: bool = True,
    intended_profile: str | None = None,
    profile_thresholds_path: Path | None = None,
    include_long_term: bool = True,
    prices: pd.DataFrame | None = None,
    backup_prices: dict[str, pd.Series] | None = None,
) -> tuple[ValidationResult, StrategyConfig, Any]:
    """
    Deep-validate one configuration and write artifacts + strategy-lock.md under output_dir.
    Does not enumerate the sweep space.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    if prices is None:
        required_symbols = collect_required_symbols([config])
        required_backup = sorted(
            set(QDII_BACKUP_SYMBOLS)
            | {sym for sym in config.simulation_symbols() if config.is_qdii_symbol(sym)}
        )
        prices, backup_prices, _ = load_market_data(
            symbols=required_symbols,
            backup_symbols=tuple(required_backup),
            use_cache=use_cache,
        )
    assert backup_prices is not None

    benchmarks = run_benchmarks(prices)
    risk_free_annual = cash_risk_free_rate(prices)
    sim_result = simulate(prices, config, backup_prices=backup_prices)
    metrics = compute_metrics(sim_result, config, prices, risk_free_annual=risk_free_annual, inflation_annual=0.03)

    stress_results, _ = run_stress_tests(config, sim_result, prices, backup_prices=backup_prices)
    path_results = run_path_stress_tests(config, prices, backup_prices=backup_prices)
    behavior_results = run_behavior_stress_tests(sim_result, metrics)
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
    )
    validation.benchmark_comparison = benchmark_comparison(metrics, benchmarks)
    validation.profile_suitability = _build_profile_suitability(
        config, metrics, sim_result, profile_thresholds_path
    )
    if include_long_term:
        validation.long_term_results = [
            run_long_term_scenario(prices, config, scenario) for scenario in LONG_TERM_SCENARIOS
        ]
    else:
        validation.long_term_results = []

    from quadbalance.reporting import generate_lock_document

    generate_lock_document(
        config, sim_result, validation, output_dir / "strategy-lock.md", intended_profile=intended_profile
    )
    write_run_artifacts(
        output_dir,
        config,
        sim_result,
        validation,
        DEFAULT_INVESTOR_PROFILES,
        validation.lifecycle_results,
    )
    # Also emit a one-row sweep_results-like file for UI consistency
    pd.DataFrame(
        [
            {
                "config_id": config.config_id,
                "validation_passed": validation.passed,
                "failure_reasons": "; ".join(validation.failure_reasons),
                "needs_review": "; ".join(validation.needs_review),
                "annualized_return": metrics.annualized_return,
                "max_drawdown": metrics.max_drawdown,
            }
        ]
    ).to_csv(output_dir / "sweep_results.csv", index=False)

    return validation, config, sim_result
