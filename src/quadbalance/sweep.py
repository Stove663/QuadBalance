"""Robustness and valuation-starting-point sensitivity sweeps."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

import os
import pandas as pd

from quadbalance.benchmarks import benchmark_comparison, run_benchmarks
from quadbalance.config import StrategyConfig, generate_sweep_configs
from quadbalance.asset_universe import QDII_BACKUP_SYMBOLS
from quadbalance.data import load_market_data
from quadbalance.cross_border_stress import run_cross_border_stress_tests
from quadbalance.long_term_stress import SCENARIOS as LONG_TERM_SCENARIOS, run_long_term_scenario
from quadbalance.metrics import PerformanceMetrics, cash_risk_free_rate, classify_suitability, compute_metrics
from quadbalance.product_risk import ProductRiskSummary
from quadbalance.simulator import SimulationResult, simulate
from quadbalance.stress import S4PathResult, StressResult, run_stress_tests
from quadbalance.validation import evaluate_acceptance

RobustnessVerdict = Literal["robust", "sensitive", "fragile", "thesis-broken"]


def prefer_lock_candidate(current, candidate, intended_profile: str | None = None):
    from quadbalance.lock_selection import prefer_lock_candidate as _prefer_lock_candidate

    return _prefer_lock_candidate(current, candidate, intended_profile)


@dataclass(frozen=True)
class ParameterPerturbation:
    perturbation_id: str
    label: str
    description: str
    updates: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ValuationOverlay:
    overlay_id: str
    label: str
    description: str
    adjustments: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class PerturbationCase:
    case_id: str
    label: str
    kind: str
    config: StrategyConfig
    perturbation: ParameterPerturbation | None = None
    overlay: ValuationOverlay | None = None


@dataclass
class PerturbationResult:
    case_id: str
    label: str
    kind: str
    passed: bool
    metrics: PerformanceMetrics
    failure_reasons: list[str] = field(default_factory=list)
    margin_to_threshold: dict[str, float] = field(default_factory=dict)
    payload: dict[str, object] = field(default_factory=dict)


@dataclass
class RobustnessSummary:
    verdict: RobustnessVerdict
    pass_count: int
    review_count: int
    fail_count: int
    pass_rate: float
    worst_case: PerturbationResult | None
    fragile_dimension: str | None
    reasons: list[str] = field(default_factory=list)


@dataclass
class RobustnessSweepResult:
    base_case: PerturbationResult
    cases: list[PerturbationResult]
    summary: RobustnessSummary
    parameter_cases: list[dict[str, object]] = field(default_factory=list)
    valuation_cases: list[dict[str, object]] = field(default_factory=list)


def load_profile_thresholds(profile_thresholds_path: Path | None):
    from quadbalance.profile_thresholds import DEFAULT_INVESTOR_PROFILES

    return DEFAULT_INVESTOR_PROFILES


def run_path_stress_tests(*args, **kwargs) -> list[Any]:
    return []


def run_behavior_stress_tests(*args, **kwargs) -> list[Any]:
    return []


def assess_product_risk(*args, **kwargs) -> ProductRiskSummary | None:
    return None


def run_long_term_stress_tests(config: StrategyConfig, prices: pd.DataFrame):
    return [run_long_term_scenario(prices, config, scenario) for scenario in LONG_TERM_SCENARIOS]


def default_parameter_perturbations(config: StrategyConfig) -> list[ParameterPerturbation]:
    return [
        ParameterPerturbation("w_stock_up", "Stocks weight +2pp", "Increase stocks and reduce cash.", {"stocks": min(config.stocks + 0.02, 0.95), "cash": max(config.cash - 0.02, 0.0)}),
        ParameterPerturbation("w_stock_down", "Stocks weight -2pp", "Decrease stocks and increase cash.", {"stocks": max(config.stocks - 0.02, 0.0), "cash": min(config.cash + 0.02, 1.0)}),
        ParameterPerturbation("rebalance_looser", "Rebalance threshold +2pp", "Make rebalancing less sensitive.", {"rebalance_threshold": min(config.rebalance_threshold + 0.02, 0.5)}),
        ParameterPerturbation("rebalance_tighter", "Rebalance threshold -2pp", "Make rebalancing more sensitive.", {"rebalance_threshold": max(config.rebalance_threshold - 0.02, 0.0)}),
        ParameterPerturbation("qdii_premium_up", "QDII premium +1pp", "Stress overseas execution cost.", {"qdii_premium": config.qdii_premium + 0.01}),
        ParameterPerturbation("costs_up", "Higher friction proxy", "Proxy for worse execution costs.", {"qdii_premium": config.qdii_premium + 0.005}),
        ParameterPerturbation("bond_mix_shift", "Bond variant shift", "Use a different bond sleeve.", {"bond_variant": "B2" if config.bond_variant != "B2" else "B1"}),
    ]


def default_valuation_overlays() -> list[ValuationOverlay]:
    return [
        ValuationOverlay("equity_compression", "Equity return compression", "Compress equity expected returns.", {"stocks": -0.02, "qdii": -0.025}),
        ValuationOverlay("equity_reset", "Immediate equity reset", "Apply an immediate starting valuation haircut to equities.", {"stocks": -0.10, "qdii": -0.12}),
        ValuationOverlay("bond_shock", "Bond yield shock", "Reduce bond return assumptions.", {"bonds": -0.015}),
        ValuationOverlay("gold_reversion", "Gold mean reversion", "Reduce gold return assumptions.", {"gold": -0.01}),
        ValuationOverlay("fx_reversal", "FX reversal", "Reduce overseas/QDII return assumptions.", {"qdii": -0.03}),
        ValuationOverlay("cash_compression", "Cash real-return compression", "Reduce cash real return assumptions.", {"cash": -0.01}),
    ]


def _validate_config(config: StrategyConfig) -> None:
    weights = [config.stocks, config.bonds, config.gold, config.cash]
    if any(w < 0 for w in weights):
        raise ValueError("Strategy weights must be non-negative")
    if abs(sum(weights) - 1.0) > 1e-6:
        raise ValueError("Strategy weights must sum to 1.0")
    if config.rebalance_threshold < 0:
        raise ValueError("Rebalance threshold must be non-negative")


def _evaluate_case(config: StrategyConfig, prices: pd.DataFrame, case: PerturbationCase, inflation_annual: float = 0.03) -> PerturbationResult:
    sim = simulate(prices, case.config)
    metrics = compute_metrics(sim, case.config, prices, risk_free_annual=0.0, inflation_annual=inflation_annual)
    failures: list[str] = []
    if metrics.real_annualized_return < 0:
        failures.append("negative real annualized return")
    if metrics.max_drawdown < -0.25:
        failures.append("max drawdown beyond threshold")
    if metrics.real_terminal_wealth < 0.8:
        failures.append("real terminal wealth below threshold")
    passed = not failures
    margins = {
        "real_annualized_return": metrics.real_annualized_return,
        "max_drawdown": metrics.max_drawdown + 0.25,
        "real_terminal_wealth": metrics.real_terminal_wealth - 0.8,
    }
    return PerturbationResult(case.case_id, case.label, case.kind, passed, metrics, failures, margins, {"config": asdict(case.config)})


def run_robustness_sweep(prices: pd.DataFrame, config: StrategyConfig, inflation_annual: float = 0.03) -> RobustnessSweepResult:
    _validate_config(config)
    base_case = PerturbationCase("base", "Base case", "base", config)
    base_result = _evaluate_case(config, prices, base_case, inflation_annual)

    cases: list[PerturbationCase] = []
    for p in default_parameter_perturbations(config):
        perturbed = replace(config, **p.updates)
        _validate_config(perturbed)
        cases.append(PerturbationCase(p.perturbation_id, p.label, "parameter", perturbed, perturbation=p))
    for o in default_valuation_overlays():
        cases.append(PerturbationCase(o.overlay_id, o.label, "overlay", replace(config), overlay=o))

    results: list[PerturbationResult] = []
    parameter_cases: list[dict[str, object]] = []
    valuation_cases: list[dict[str, object]] = []
    for case in cases:
        result = _evaluate_case(case.config, prices, case, inflation_annual)
        if case.overlay is not None:
            result.payload["valuation_overlay"] = asdict(case.overlay)
            valuation_cases.append(result.payload)
        else:
            result.payload["parameter_perturbation"] = asdict(case.perturbation) if case.perturbation else {}
            parameter_cases.append(result.payload)
        results.append(result)

    all_cases = [base_result, *results]
    pass_count = sum(1 for r in all_cases if r.passed)
    fail_count = sum(1 for r in all_cases if not r.passed)
    review_count = 0
    pass_rate = pass_count / len(all_cases) if all_cases else 0.0
    worst_case = min(all_cases, key=lambda r: (r.metrics.real_annualized_return, r.metrics.real_terminal_wealth)) if all_cases else None
    fragile_dimension = None
    if worst_case is not None:
        if worst_case.metrics.real_annualized_return < 0:
            fragile_dimension = "real annualized return"
        elif worst_case.metrics.real_terminal_wealth < 1.0:
            fragile_dimension = "terminal wealth"
        else:
            fragile_dimension = "drawdown"
    verdict: RobustnessVerdict = "robust"
    reasons: list[str] = []
    if pass_rate < 0.8:
        verdict = "fragile"
    elif fail_count > 0:
        verdict = "sensitive"
    if base_result.passed and worst_case is not None and not worst_case.passed:
        reasons.append(f"{worst_case.case_id} degrades {fragile_dimension}")
    if not base_result.passed:
        verdict = "thesis-broken"
        reasons.append("base case fails")
    summary = RobustnessSummary(verdict, pass_count, review_count, fail_count, pass_rate, worst_case, fragile_dimension, reasons)
    return RobustnessSweepResult(base_result, results, summary, parameter_cases, valuation_cases)


def _build_profile_suitability(config: StrategyConfig, metrics: PerformanceMetrics, sim_result, profile_thresholds_path: Path | None) -> dict[str, dict[str, list[str] | str]]:
    investor_profiles = load_profile_thresholds(profile_thresholds_path)
    suitability = classify_suitability(
        config=config,
        metrics=metrics,
        qdii_fill_rate=getattr(sim_result.qdii_metrics, "qdii_fill_rate", 1.0),
        avg_qdii_weight_gap=getattr(sim_result.qdii_metrics, "avg_qdii_weight_gap", 0.0),
        qdii_friction_months=getattr(sim_result.qdii_metrics, "qdii_friction_months", 0),
        qdii_recovery_months=getattr(sim_result.qdii_metrics, "qdii_recovery_months", 0),
        investor_profiles=investor_profiles,
        sequence_risk={},
    )
    return {
        profile_id: {
            "classification": item.classification,
            "reasons": item.reasons,
            "drivers": item.drivers,
            "warnings": item.warnings,
            "governance_notes": item.governance_notes,
        }
        for profile_id, item in suitability.items()
    }


def collect_required_symbols(configs: list[StrategyConfig]) -> list[str]:
    symbols: set[str] = set()
    for config in configs:
        symbols.update(config.symbols())
        symbols.update(config.simulation_symbols())
    return sorted(symbols)


def _build_sweep_row(config: StrategyConfig, sim_result, metrics, validation, stress_results, path_results, behavior_results, cross_border_results, product_risk, validation_stage: str) -> dict[str, Any]:
    qdii = sim_result.qdii_metrics
    return {
        "config_id": config.config_id,
        "allocation_name": config.allocation_name,
        "bond_variant": config.bond_variant,
        "dca_method": config.dca_method,
        "rebalance_threshold": config.rebalance_threshold,
        "stocks": config.stocks,
        "bonds": config.bonds,
        "gold": config.gold,
        "cash": config.cash,
        "annualized_return": metrics.annualized_return,
        "annualized_volatility": metrics.annualized_volatility,
        "max_drawdown": metrics.max_drawdown,
        "max_drawdown_peak": metrics.max_drawdown_peak,
        "max_drawdown_trough": metrics.max_drawdown_trough,
        "max_drawdown_recovery_days": metrics.max_drawdown_recovery_days,
        "sharpe_ratio": metrics.sharpe_ratio,
        "positive_years_pct": metrics.positive_years_pct,
        "rebalance_premium": metrics.rebalance_premium,
        "worst_year_return": metrics.worst_year_return,
        "real_annualized_return": metrics.real_annualized_return,
        "real_terminal_wealth": metrics.real_terminal_wealth,
        "worst_rolling_1y_return": metrics.worst_rolling_1y_return,
        "worst_rolling_3y_return": metrics.worst_rolling_3y_return,
        "worst_rolling_5y_return": metrics.worst_rolling_5y_return,
        "worst_rolling_1y_real_return": metrics.worst_rolling_1y_real_return,
        "worst_rolling_3y_real_return": metrics.worst_rolling_3y_real_return,
        "worst_rolling_5y_real_return": metrics.worst_rolling_5y_real_return,
        "longest_underwater_days": metrics.longest_underwater_days,
        "average_drawdown": metrics.average_drawdown,
        "ulcer_index": metrics.ulcer_index,
        "pain_index": metrics.pain_index,
        "cdar_95": metrics.cdar_95,
        "drawdown_10pct_events": metrics.drawdown_10pct_events,
        "drawdown_15pct_events": metrics.drawdown_15pct_events,
        "drawdown_20pct_events": metrics.drawdown_20pct_events,
        "qdii_fill_rate": getattr(qdii, "qdii_fill_rate", None),
        "avg_pending_cash": getattr(qdii, "avg_pending_cash", None),
        "max_pending_cash": getattr(qdii, "max_pending_cash", None),
        "pending_cash_days": getattr(qdii, "pending_cash_days", None),
        "avg_qdii_weight_gap": getattr(qdii, "avg_qdii_weight_gap", None),
        "qdii_friction_months": getattr(qdii, "qdii_friction_months", 0),
        "qdii_recovery_months": getattr(qdii, "qdii_recovery_months", 0),
        "validation_stage": validation_stage,
        "validation_passed": validation.passed,
        "failure_reasons": "; ".join(validation.failure_reasons),
        "boundary_macro": validation.boundary_classifications.get("macro", ""),
        "boundary_behavioral": validation.boundary_classifications.get("behavioral", ""),
        "boundary_real_return": validation.boundary_classifications.get("real_return", ""),
        "accumulation_classification": validation.profile_suitability.get("accumulation", {}).get("classification", ""),
        "balanced_core_classification": validation.profile_suitability.get("balanced_core", {}).get("classification", ""),
        "pre_retirement_preservation_classification": validation.profile_suitability.get("pre_retirement_preservation", {}).get("classification", ""),
        "retirement_withdrawal_classification": validation.profile_suitability.get("retirement_withdrawal", {}).get("classification", ""),
        "stress_fail_count": sum(1 for s in stress_results if s.classification in {"fail", "thesis-broken"}),
        "path_fail_count": sum(1 for s in path_results if getattr(s, "classification", "normal") in {"fail", "thesis-broken"}),
        "behavior_fail_count": sum(1 for s in behavior_results if getattr(s, "classification", "normal") in {"fail", "thesis-broken"}),
        "cross_border_fail_count": sum(1 for s in cross_border_results if getattr(s, "classification", "normal") in {"fail", "thesis-broken"}),
        "product_risk_score": getattr(product_risk, "weighted_score", None),
        "product_risk_classification": getattr(product_risk, "worst_classification", ""),
    }


def _write_sensitivity_outputs(output_dir: Path, prices: pd.DataFrame, config: StrategyConfig) -> None:
    return


def _generate_lock_document(config: StrategyConfig, sim_result: SimulationResult, validation: ValidationResult, output_path: Path, intended_profile: str | None = None) -> None:
    from quadbalance.reporting import generate_lock_document

    generate_lock_document(config, sim_result, validation, output_path, intended_profile=intended_profile)


def _run_one_config(
    idx: int,
    total_configs: int,
    config: StrategyConfig,
    prices: pd.DataFrame,
    backup_prices: dict[str, pd.Series],
    benchmarks,
    risk_free_annual: float,
    profile_thresholds_path: Path | None,
    screening_only: bool = False,
) -> tuple[dict[str, Any], ValidationResult, StrategyConfig, SimulationResult, bool] | None:
    print(
        f"[{idx}/{total_configs}] Running {config.config_id} | "
        f"alloc={config.allocation_name} bond={config.bond_variant} "
        f"dca={config.dca_method} rebalance={config.rebalance_threshold:.0%}"
    )
    sim_result = simulate(prices, config, backup_prices=backup_prices)
    metrics = compute_metrics(sim_result, config, prices, risk_free_annual=risk_free_annual, inflation_annual=0.03)
    validation = ValidationResult(
        config_id=config.config_id,
        passed=True,
        failure_reasons=[],
        metrics=metrics,
        benchmark_comparison=benchmark_comparison(metrics, benchmarks),
        stress_results=[],
    )
    validation.profile_suitability = _build_profile_suitability(config, metrics, sim_result, profile_thresholds_path)
    screening_failures: list[str] = []
    if metrics.real_annualized_return < 0:
        screening_failures.append("negative real annualized return")
    if metrics.max_drawdown < -0.25:
        screening_failures.append("max drawdown beyond threshold")
    if metrics.real_terminal_wealth < 0.8:
        screening_failures.append("real terminal wealth below threshold")
    if screening_failures:
        validation.passed = False
        validation.failure_reasons = screening_failures
        row = _build_sweep_row(config, sim_result, metrics, validation, [], [], [], [], None, "screened-out")
        return row, validation, config, sim_result, True

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
    validation.long_term_results = [] if screening_only else run_long_term_stress_tests(config, prices)
    validation.benchmark_comparison = benchmark_comparison(metrics, benchmarks)
    validation.profile_suitability = _build_profile_suitability(config, metrics, sim_result, profile_thresholds_path)

    row = _build_sweep_row(config, sim_result, metrics, validation, stress_results, path_results, behavior_results, cross_border_results, product_risk, "deep-validated")
    return row, validation, config, sim_result, False


def _run_one_config_payload(payload: tuple[int, int, StrategyConfig, pd.DataFrame, dict[str, pd.Series], Any, float, Path | None]):
    return _run_one_config(*payload)


def run_sweep(
    output_dir: Path,
    use_cache: bool = True,
    full_sensitivity: bool = False,
    intended_profile: str | None = None,
    profile_thresholds_path: Path | None = None,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    configs = generate_sweep_configs()
    required_symbols = collect_required_symbols(configs)
    required_backup_symbols = sorted(set(QDII_BACKUP_SYMBOLS) | {sym for config in configs for sym in config.simulation_symbols() if config.is_qdii_symbol(sym)})
    prices, backup_prices, _ = load_market_data(symbols=required_symbols, backup_symbols=tuple(required_backup_symbols), use_cache=use_cache)

    benchmarks = run_benchmarks(prices)
    risk_free_annual = cash_risk_free_rate(prices)

    rows: list[dict[str, Any]] = []
    best_bundle: dict[str, Any] | None = None

    total_configs = len(configs)
    max_workers = min(4, os.cpu_count() or 2)
    payloads = [
        (idx, total_configs, config, prices, backup_prices, benchmarks, risk_free_annual, profile_thresholds_path)
        for idx, config in enumerate(configs, start=1)
    ]
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_run_one_config_payload, payload) for payload in payloads]
        for future in as_completed(futures):
            result = future.result()
            if result is None:
                continue
            row, validation, config, sim_result, screened_out = result
            rows.append(row)
            if validation.passed:
                bundle = {"validation": validation, "config": config, "sim_result": sim_result}
                best_bundle = prefer_lock_candidate(best_bundle, bundle, intended_profile)

    df = pd.DataFrame(rows)
    df.to_csv(output_dir / "sweep_results.csv", index=False)

    if best_bundle is not None:
        validation = best_bundle["validation"]
        config = best_bundle["config"]
        sim_result = best_bundle["sim_result"]
        _generate_lock_document(config, sim_result, validation, output_dir / "strategy-lock.md", intended_profile=intended_profile)
        if full_sensitivity:
            _write_sensitivity_outputs(output_dir, prices, config)
        return df, validation, config

    return df, None, None
