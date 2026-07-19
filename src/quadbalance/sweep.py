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
from quadbalance.validation import ValidationResult, evaluate_acceptance
from quadbalance.sweep_constants import ARTIFACT_MANIFEST_FILENAME, ARTIFACTS_DIRNAME, SWEEP_RESULTS_FILENAME

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
    from quadbalance.path_stress import run_path_stress_tests as _run_path_stress_tests

    # Sweep historically passed (config, prices, ...); real API is config-only.
    config = args[0] if args else kwargs.get("config")
    return _run_path_stress_tests(config)


def run_behavior_stress_tests(*args, **kwargs) -> list[Any]:
    from quadbalance.behavior_stress import run_behavior_stress_tests as _run_behavior_stress_tests

    return _run_behavior_stress_tests(*args, **kwargs)


def assess_product_risk(*args, **kwargs) -> ProductRiskSummary | None:
    from quadbalance.product_risk import assess_product_risk as _assess_product_risk

    return _assess_product_risk(*args, **kwargs)


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


def _apply_valuation_overlay(prices: pd.DataFrame, config: StrategyConfig, overlay: ValuationOverlay) -> pd.DataFrame:
    """Apply a one-time level shock to sleeves named in overlay.adjustments."""
    shocked = prices.copy()
    for col in shocked.columns:
        if config.is_qdii_symbol(col):
            key = "qdii"
        else:
            key = config.quadrant_for_symbol(col)
        delta = float(overlay.adjustments.get(key, 0.0))
        if delta != 0.0:
            shocked[col] = shocked[col] * (1.0 + delta)
    return shocked


def _evaluate_case(config: StrategyConfig, prices: pd.DataFrame, case: PerturbationCase, inflation_annual: float = 0.03) -> PerturbationResult:
    sim_prices = prices
    if case.overlay is not None:
        sim_prices = _apply_valuation_overlay(prices, case.config, case.overlay)
    sim = simulate(sim_prices, case.config)
    metrics = compute_metrics(sim, case.config, sim_prices, risk_free_annual=0.0, inflation_annual=inflation_annual)
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
    """Primary/alignment symbols only — QDII backups must not truncate the matrix."""
    from quadbalance.asset_universe import PRICE_MATRIX_SYMBOLS, QDII_BACKUP_SYMBOLS

    symbols: set[str] = set(PRICE_MATRIX_SYMBOLS)
    for config in configs:
        symbols.update(config.symbols())
    forbidden = symbols & set(QDII_BACKUP_SYMBOLS)
    if forbidden:
        raise ValueError(f"Alignment symbols must not include QDII backups: {sorted(forbidden)}")
    return sorted(symbols)


def _build_sweep_row(config: StrategyConfig, sim_result, metrics, validation, stress_results, path_results, behavior_results, cross_border_results, product_risk, validation_stage: str, artifacts_dir: Path | None = None) -> dict[str, Any]:
    qdii = sim_result.qdii_metrics
    row = {
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
        "needs_review": "; ".join(getattr(validation, "needs_review", []) or []),
        "material_needs_review": "; ".join(getattr(validation, "material_needs_review", []) or []),
        "lockable": getattr(validation, "lockable", False),
        "qdii_pending_days_gate": (
            "fail"
            if (getattr(qdii, "pending_cash_days", 0) or 0) > 252
            else "pass"
        ),
        "qdii_weight_gap_gate": (
            "fail"
            if (getattr(qdii, "qdii_friction_months", 0) or 0) >= 12
            and abs(getattr(qdii, "avg_qdii_weight_gap", 0.0) or 0.0) > 0.02
            else "pass"
        ),
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
    if artifacts_dir is not None:
        row["artifact_manifest"] = str(artifacts_dir / ARTIFACT_MANIFEST_FILENAME)
        row["artifact_bundle"] = str(artifacts_dir)
    return row


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
) -> tuple[dict[str, Any], ValidationResult, StrategyConfig, SimulationResult, bool] | None:
    print(
        f"[{idx}/{total_configs}] Started {config.config_id} | "
        f"alloc={config.allocation_name} bond={config.bond_variant} "
        f"dca={config.dca_method} rebalance={config.rebalance_threshold:.0%}",
        flush=True,
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
        row = _build_sweep_row(config, sim_result, metrics, validation, [], [], [], [], None, "screened-out", None)
        return row, validation, config, sim_result, True

    stress_results, _ = run_stress_tests(config, sim_result, prices, backup_prices=backup_prices)
    path_results = run_path_stress_tests(config, prices, backup_prices=backup_prices)
    behavior_results = run_behavior_stress_tests(
        sim_result, metrics, path_results=path_results, stress_results=stress_results
    )
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
    # LT1–LT3 deferred to lock selection in run_sweep (skip for all sweep candidates).
    validation.long_term_results = []
    validation.benchmark_comparison = benchmark_comparison(metrics, benchmarks)
    validation.profile_suitability = _build_profile_suitability(config, metrics, sim_result, profile_thresholds_path)

    artifacts_dir = None
    row = _build_sweep_row(config, sim_result, metrics, validation, stress_results, path_results, behavior_results, cross_border_results, product_risk, "deep-validated", artifacts_dir)
    return row, validation, config, sim_result, False


def _run_one_config_payload(payload: tuple[int, int, StrategyConfig, pd.DataFrame, dict[str, pd.Series], Any, float, Path | None]):
    return _run_one_config(*payload)


def run_sweep(
    output_dir: Path,
    use_cache: bool = True,
    full_sensitivity: bool = False,
    intended_profile: str | None = None,
    profile_thresholds_path: Path | None = None,
    sign_off_reviewer: str | None = None,
    sign_off_rationale: str | None = None,
    lock_config_id: str | None = None,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    configs = generate_sweep_configs()
    required_symbols = collect_required_symbols(configs)
    required_backup_symbols = sorted(set(QDII_BACKUP_SYMBOLS) | {sym for config in configs for sym in config.simulation_symbols() if config.is_qdii_symbol(sym)})
    prices, backup_prices, _ = load_market_data(symbols=required_symbols, backup_symbols=tuple(required_backup_symbols), use_cache=use_cache)

    benchmarks = run_benchmarks(prices)
    risk_free_annual = cash_risk_free_rate(prices)

    rows: list[dict[str, Any]] = []
    passing_bundles: list[dict[str, Any]] = []

    total_configs = len(configs)
    max_workers = min(8, os.cpu_count() or 2)
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
                qdii = getattr(sim_result, "qdii_metrics", None)
                passing_bundles.append(
                    {
                        "validation": validation,
                        "config": config,
                        "sim_result": sim_result,
                        "annualized_return": validation.metrics.annualized_return,
                        "max_drawdown": validation.metrics.max_drawdown,
                        "qdii_fill_rate": float(getattr(qdii, "qdii_fill_rate", 0.0) or 0.0),
                        "pending_cash_days": int(getattr(qdii, "pending_cash_days", 0) or 0)
                        if qdii is not None
                        else 0,
                        "config_id": config.config_id,
                        "allocation_name": config.allocation_name,
                        "profile_suitability": validation.profile_suitability,
                        "lockable": getattr(validation, "lockable", False),
                        "stock_sub_split": config.stock_sub_split,
                        "material_needs_review": list(
                            getattr(validation, "material_needs_review", None)
                            or getattr(validation, "needs_review", None)
                            or []
                        ),
                        "artifacts_dir": str(output_dir / "artifacts"),
                    }
                )

    df = pd.DataFrame(rows)
    df.to_csv(output_dir / "sweep_results.csv", index=False)
    print(
        f"Parallel sweep done: {len(df)} configs, "
        f"{int(df['validation_passed'].sum()) if 'validation_passed' in df.columns else 0} passed, "
        f"{int(df['lockable'].fillna(False).astype(bool).sum()) if 'lockable' in df.columns else 0} lockable before LT"
    )

    # Prefer lockable candidates; long-term thesis-broken / seq_inflation veto tries next.
    # Cap LT attempts — each LT1–LT3 run is multi-decade and must not fan out over all soft-passes.
    from quadbalance.lock_integrity import HumanSignOff, compute_lockable, material_needs_review
    from quadbalance.validation import apply_long_term_lock_vetoes

    MAX_LT_LOCK_ATTEMPTS = 3

    def _finalize_lock(bundle: dict[str, Any], validation, config, sim_result) -> tuple:
        _generate_lock_document(config, sim_result, validation, output_dir / "strategy-lock.md", intended_profile=intended_profile)
        from quadbalance.artifacts import write_run_artifacts
        from quadbalance.profile_thresholds import DEFAULT_INVESTOR_PROFILES

        write_run_artifacts(
            output_dir,
            config,
            sim_result,
            validation,
            DEFAULT_INVESTOR_PROFILES,
            validation.lifecycle_results,
        )
        if full_sensitivity:
            _write_sensitivity_outputs(output_dir, prices, config)
        if "config_id" in df.columns and "lockable" in df.columns:
            df.loc[df["config_id"] == config.config_id, "lockable"] = validation.lockable
            df.loc[df["config_id"] == config.config_id, "material_needs_review"] = "; ".join(
                getattr(validation, "material_needs_review", []) or []
            )
            df.loc[df["config_id"] == config.config_id, "artifact_manifest"] = str(output_dir / ARTIFACTS_DIRNAME / ARTIFACT_MANIFEST_FILENAME)
            df.loc[df["config_id"] == config.config_id, "artifact_bundle"] = str(output_dir / ARTIFACTS_DIRNAME)
            df.to_csv(output_dir / SWEEP_RESULTS_FILENAME, index=False)
        return df, validation, config

    # Rank once; only evaluate LT for the top few candidates.
    ranked: list[dict[str, Any]] = []
    pool = list(passing_bundles)
    while pool:
        best: dict[str, Any] | None = None
        for bundle in pool:
            best = prefer_lock_candidate(best, bundle, intended_profile)
        assert best is not None
        ranked.append(best)
        pool = [b for b in pool if b["config"].config_id != best["config"].config_id]

    soft_pass_after_lt: list[dict[str, Any]] = []
    for attempt, best_bundle in enumerate(ranked[:MAX_LT_LOCK_ATTEMPTS], start=1):
        validation = best_bundle["validation"]
        config = best_bundle["config"]
        sim_result = best_bundle["sim_result"]
        print(
            f"Lock selection LT attempt {attempt}/{min(MAX_LT_LOCK_ATTEMPTS, len(ranked))}: "
            f"{config.config_id} (pre-LT lockable={getattr(validation, 'lockable', False)})"
        )
        validation.long_term_results = run_long_term_stress_tests(config, prices)
        apply_long_term_lock_vetoes(validation)
        if any(getattr(r, "classification", "") == "thesis-broken" for r in validation.long_term_results):
            validation.passed = False
            validation.lockable = False
            validation.failure_reasons = list(validation.failure_reasons) + [
                f"Long-term stress thesis-broken: {r.scenario_id}"
                for r in validation.long_term_results
                if getattr(r, "classification", "") == "thesis-broken"
            ]
            if "config_id" in df.columns and "validation_passed" in df.columns:
                df.loc[df["config_id"] == config.config_id, "validation_passed"] = False
                df.loc[df["config_id"] == config.config_id, "lockable"] = False
                df.to_csv(output_dir / "sweep_results.csv", index=False)
            print(f"  → LT thesis-broken; skipping")
            continue

        if validation.lockable:
            print(f"  → lockable after LT; writing strategy-lock.md")
            return _finalize_lock(best_bundle, validation, config, sim_result)

        print(
            f"  → soft-pass after LT "
            f"(material reviews={len(getattr(validation, 'material_needs_review', []) or [])})"
        )
        soft_pass_after_lt.append({**best_bundle, "validation": validation, "lockable": False})

    # No naturally lockable config: build return-seeking shortlist; lock only on explicit pick + sign-off.
    from quadbalance.lock_shortlist import build_return_seeking_shortlist, write_lock_shortlist_artifacts

    soft_pool = [
        b
        for b in passing_bundles
        if getattr(b["validation"], "passed", False) and not bool(getattr(b["validation"], "lockable", False))
    ]
    # Prefer LT-enriched bundles when present.
    by_id = {b["config"].config_id: b for b in soft_pool}
    for b in soft_pass_after_lt:
        by_id[b["config"].config_id] = b
    soft_pool = list(by_id.values())

    shortlist = build_return_seeking_shortlist(soft_pool, intended_profile=intended_profile)

    # Ensure LT for shortlist members (capped to role count).
    for role in shortlist.get("roles", []):
        bundle = role.get("bundle")
        if bundle is None:
            continue
        validation = bundle["validation"]
        config = bundle["config"]
        if getattr(validation, "long_term_results", None):
            continue
        print(f"Shortlist LT for {role['role']}: {config.config_id}")
        validation.long_term_results = run_long_term_stress_tests(config, prices)
        apply_long_term_lock_vetoes(validation)
        if any(getattr(r, "classification", "") == "thesis-broken" for r in validation.long_term_results):
            validation.passed = False
            validation.lockable = False
            role["lockable"] = False
            role["cons"] = list(role.get("cons") or []) + ["Long-term stress thesis-broken after shortlist LT"]
            if "config_id" in df.columns and "validation_passed" in df.columns:
                df.loc[df["config_id"] == config.config_id, "validation_passed"] = False
                df.loc[df["config_id"] == config.config_id, "lockable"] = False
                df.to_csv(output_dir / "sweep_results.csv", index=False)
            continue
        role["material_needs_review"] = list(getattr(validation, "material_needs_review", []) or [])
        by_id[config.config_id] = {**bundle, "validation": validation, "lockable": False}

    # Drop thesis-broken roles and rebuild public artifact from surviving bundles.
    surviving = [
        role["bundle"]
        for role in shortlist.get("roles", [])
        if role.get("bundle") is not None and getattr(role["bundle"]["validation"], "passed", False)
    ]
    shortlist = build_return_seeking_shortlist(surviving or soft_pool, intended_profile=intended_profile)
    json_path, md_path = write_lock_shortlist_artifacts(output_dir, shortlist)
    print(
        f"Lock shortlist written: {md_path.name} ({len(shortlist.get('roles', []))} roles); "
        f"JSON: {json_path.name}"
    )

    def _apply_sign_off_and_lock(bundle: dict[str, Any]) -> tuple | None:
        validation = bundle["validation"]
        config = bundle["config"]
        sim_result = bundle["sim_result"]
        if not getattr(validation, "long_term_results", None):
            validation.long_term_results = run_long_term_stress_tests(config, prices)
            apply_long_term_lock_vetoes(validation)
        if any(getattr(r, "classification", "") == "thesis-broken" for r in validation.long_term_results):
            print(f"Cannot lock {config.config_id}: long-term thesis-broken")
            return None
        material = material_needs_review(list(validation.needs_review))
        if material and not (sign_off_reviewer and sign_off_rationale):
            print(
                f"Cannot lock {config.config_id}: material reviews remain "
                "(supply --sign-off-reviewer/--sign-off-rationale)"
            )
            return None
        if material:
            validation.sign_off = HumanSignOff(
                reviewer=sign_off_reviewer,
                rationale=sign_off_rationale,
                acknowledged_items=tuple(material),
            )
        validation.material_needs_review = material
        validation.lockable = compute_lockable(validation.passed, validation.needs_review, validation.sign_off)
        if not validation.lockable:
            print(f"Cannot lock {config.config_id}: still not lockable after sign-off check")
            return None
        print(f"Locking {config.config_id} (sign-off={'yes' if validation.sign_off else 'no'})")
        return _finalize_lock(bundle, validation, config, sim_result)

    if lock_config_id:
        target = by_id.get(lock_config_id)
        if target is None:
            for b in passing_bundles:
                if b["config"].config_id == lock_config_id and getattr(b["validation"], "passed", False):
                    target = b
                    break
        if target is None:
            print(f"No passing configuration matching --lock-config-id={lock_config_id}")
            return df, None, None
        locked = _apply_sign_off_and_lock(target)
        if locked is not None:
            return locked
        return df, None, None

    if sign_off_reviewer and sign_off_rationale and not lock_config_id:
        print(
            "Sign-off provided without --lock-config-id; shortlist written but no auto-lock. "
            "Re-run with --lock-config-id set to a shortlist config_id."
        )
    else:
        print(
            "No lockable configuration after LT. Review lock-shortlist.md and pick with "
            "--lock-config-id plus --sign-off-reviewer/--sign-off-rationale when needed."
        )
    return df, None, None
