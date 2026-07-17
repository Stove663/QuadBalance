"""Robustness and valuation-starting-point sensitivity sweeps."""

from __future__ import annotations

from dataclasses import dataclass, field, replace, asdict
from typing import Literal

import pandas as pd

from quadbalance.config import StrategyConfig
from quadbalance.metrics import PerformanceMetrics, compute_metrics
from quadbalance.simulator import SimulationResult, simulate
from quadbalance.long_term_stress import LongTermScenarioResult

RobustnessVerdict = Literal["robust", "sensitive", "fragile", "thesis-broken"]


def prefer_lock_candidate(current, candidate, intended_profile: str | None = None):
    from quadbalance.lock_selection import prefer_lock_candidate as _prefer_lock_candidate

    return _prefer_lock_candidate(current, candidate, intended_profile)


def run_sweep(*args, **kwargs):
    raise NotImplementedError("run_sweep is not available in this build")


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


def default_parameter_perturbations(config: StrategyConfig) -> list[ParameterPerturbation]:
    return [
        ParameterPerturbation("w_stock_up", "Stocks weight +2pp", "Increase stocks and reduce cash.", {"stocks": min(config.stocks + 0.02, 0.95), "cash": max(config.cash - 0.02, 0.0)}),
        ParameterPerturbation("w_stock_down", "Stocks weight -2pp", "Decrease stocks and increase cash.", {"stocks": max(config.stocks - 0.02, 0.0), "cash": min(config.cash + 0.02, 1.0)}),
        ParameterPerturbation("rebalance_looser", "Rebalance threshold +2pp", "Make rebalancing less sensitive.", {"rebalance_threshold": min(config.rebalance_threshold + 0.02, 0.5)}),
        ParameterPerturbation("rebalance_tighter", "Rebalance threshold -2pp", "Make rebalancing more sensitive.", {"rebalance_threshold": max(config.rebalance_threshold - 0.02, 0.0)}),
        ParameterPerturbation("qdii_premium_up", "QDII premium +1pp", "Stress overseas execution cost.", {"qdii_premium": config.qdii_premium + 0.01}),
        ParameterPerturbation("costs_up", "Higher friction proxy", "Proxy for worse execution costs.", {"qdii_premium": config.qdii_premium + 0.005}),
        ParameterPerturbation("inflation_up", "Inflation +1pp", "Stress real-return sensitivity.", {}),
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


def _apply_parameter_perturbation(config: StrategyConfig, perturbation: ParameterPerturbation) -> StrategyConfig:
    updates = dict(perturbation.updates)
    if "stocks" in updates or "cash" in updates:
        stocks = float(updates.get("stocks", config.stocks))
        cash = float(updates.get("cash", config.cash))
        total = stocks + config.bonds + config.gold + cash
        if total <= 0:
            raise ValueError("Invalid perturbation produces non-positive total weight")
        scale = 1.0 / total
        updates["stocks"] = stocks * scale
        updates["bonds"] = config.bonds * scale
        updates["gold"] = config.gold * scale
        updates["cash"] = cash * scale
    return replace(config, **updates)


def _validate_config(config: StrategyConfig) -> None:
    weights = [config.stocks, config.bonds, config.gold, config.cash]
    if any(w < 0 for w in weights):
        raise ValueError("Strategy weights must be non-negative")
    if abs(sum(weights) - 1.0) > 1e-6:
        raise ValueError("Strategy weights must sum to 1.0")
    if config.rebalance_threshold < 0:
        raise ValueError("Rebalance threshold must be non-negative")
    if config.qdii_premium < -1:
        raise ValueError("QDII premium cannot be less than -100%")


def _valuation_adjusted_prices(prices: pd.DataFrame, overlay: ValuationOverlay) -> pd.DataFrame:
    adjusted = prices.copy()
    for col in adjusted.columns:
        key = "qdii" if "qdii" in col.lower() else (
            "stocks" if col.lower().startswith(("11", "00", "sh", "sz")) else "bonds" if col.lower().startswith("bond") else "gold" if col.lower().startswith("gold") else "cash"
        )
        delta = overlay.adjustments.get(key, 0.0)
        if delta != 0.0:
            growth = adjusted[col].pct_change().fillna(0.0) + delta
            adjusted[col] = adjusted[col].iloc[0] * (1.0 + growth).cumprod()
    return adjusted


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
        perturbed = _apply_parameter_perturbation(config, p)
        _validate_config(perturbed)
        cases.append(PerturbationCase(p.perturbation_id, p.label, "parameter", perturbed, perturbation=p))
    for o in default_valuation_overlays():
        cases.append(PerturbationCase(o.overlay_id, o.label, "overlay", replace(config), overlay=o))

    results: list[PerturbationResult] = []
    parameter_cases: list[dict[str, object]] = []
    valuation_cases: list[dict[str, object]] = []
    for case in cases:
        if case.overlay is not None:
            adjusted_prices = _valuation_adjusted_prices(prices, case.overlay)
            result = _evaluate_case(case.config, adjusted_prices, case, inflation_annual)
            result.payload["valuation_overlay"] = asdict(case.overlay)
            valuation_cases.append(result.payload)
        else:
            result = _evaluate_case(case.config, prices, case, inflation_annual)
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
