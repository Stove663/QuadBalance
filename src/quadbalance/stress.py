"""Stress test scenarios and path simulation."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum

import pandas as pd

from quadbalance.config import StrategyConfig
from quadbalance.instrument_pool import qdii_pool_codes
from quadbalance.simulator import SimulationResult, simulate
from quadbalance.stress_scenarios import STRESS_SCENARIOS
from quadbalance.stress_thresholds import DEFAULT_STRESS_THRESHOLDS


@dataclass
class StressResult:
    scenario_id: str
    scenario_name: str
    portfolio_return: float
    worst_quadrant_shock: float
    passed: bool
    classification: str = "normal"
    threshold_reasons: list[str] = field(default_factory=list)
    threshold_basis: str = "portfolio_return"
    duration_days: int = 0
    liquidity_impairment_days: int = 0
    concurrent_drawdown_count: int = 0
    hedge_failure_days: int = 0
    notes: list[str] = field(default_factory=list)


@dataclass
class S4PathResult:
    window_years: list[int]
    cumulative_return: float
    worst_year_return: float
    window_annualized_return: float
    passed: bool


class StressMode(str, Enum):
    exact = "exact"
    exploratory = "exploratory"


S4_CUMULATIVE_FLOOR = -0.10
FAST_STRESS_SCENARIOS = {sid for sid in STRESS_SCENARIOS if sid in {"S1", "S2", "S3", "S6"}}
MECHANISM_STRESS_SCENARIOS = {"S14", "S15", "S16", "S17", "S18", "S19", "S20", "S21"}
FULL_STRESS_SCENARIOS = {sid for sid in STRESS_SCENARIOS if sid not in FAST_STRESS_SCENARIOS} | {"S5", "S7"}

MECHANISM_STRESS_NOTES: dict[str, list[str]] = {
    "S14": ["all defensive quadrants lose hedge value", "cash is haircut for real purchasing-power erosion"],
    "S15": ["rebalancing buy orders are delayed", "target underweights cannot be corrected for one quarter"],
    "S16": ["QDII sleeve suffers equity drawdown, FX reversal, premium compression, and quota scarcity"],
    "S17": ["nominal drawdown can look mild while real wealth is impaired", "persistent inflation taxes cash and bonds"],
    "S18": ["large initial deployment is followed by a front-loaded crash", "monthly contributions have limited averaging power"],
    "S19": ["bond fund faces redemption pressure and liquidity discount", "bond sleeve is not treated as risk-free"],
    "S20": ["cash-like fund liquidity is impaired", "real cash return is negative under inflation"],
    "S21": ["investor capitulates after deep drawdown", "discipline failure adds a behavioral haircut"],
}


def _median_quadrant_returns(annual_q: pd.DataFrame) -> dict[str, float]:
    return {
        col: float(annual_q[col].median())
        for col in ("stocks", "bonds", "gold", "cash")
        if col in annual_q.columns
    }


def _portfolio_return_from_quadrants(config: StrategyConfig, quadrant_returns: dict[str, float]) -> float:
    w = config.quadrant_weights
    return sum(w[q] * quadrant_returns.get(q, 0.0) for q in w)


def _worst_shock(quadrant_returns: dict[str, float]) -> float:
    return abs(min(quadrant_returns.values()))


def get_s4_window_years(prices: pd.DataFrame, window_years: int = 5) -> list[int]:
    years = sorted(set(prices.index.year))
    if len(years) < window_years:
        return years
    return years[-window_years:]


def cap_bond_annual_returns(
    prices: pd.DataFrame,
    config: StrategyConfig,
    window_years: list[int],
    cap_rate: float = 0.02,
) -> pd.DataFrame:
    """Cap bond instrument annual returns at cap_rate for each year in window."""
    result = prices.copy()
    bond_symbols = [s for s in config.symbols() if config.quadrant_for_symbol(s) == "bonds"]

    for year in window_years:
        for sym in bond_symbols:
            if sym not in result.columns:
                continue
            mask = result.index.year == year
            year_prices = result.loc[mask, sym]
            if len(year_prices) < 2:
                continue
            start_p = float(year_prices.iloc[0])
            end_p = float(year_prices.iloc[-1])
            if start_p <= 0:
                continue
            actual_ann = end_p / start_p - 1.0
            if actual_ann <= cap_rate:
                continue
            target_end = start_p * (1.0 + cap_rate)
            span = end_p - start_p
            if span == 0:
                continue
            result.loc[mask, sym] = start_p + (year_prices - start_p) * ((target_end - start_p) / span)
    return result


def run_s4_path_test(
    config: StrategyConfig,
    prices: pd.DataFrame,
    window_years: int = 5,
    cap_rate: float = 0.02,
    backup_prices: dict[str, pd.Series] | None = None,
    *,
    mode: StressMode = StressMode.exact,
) -> S4PathResult:
    """Full simulation with bond returns capped for consecutive calendar years."""
    years = get_s4_window_years(prices, window_years)
    if mode == StressMode.exploratory:
        prices = prices[prices.index.year.isin(years)]
    capped = cap_bond_annual_returns(prices, config, years, cap_rate)
    sim = simulate(capped, config, backup_prices=backup_prices)

    daily = sim.daily_values
    window_mask = daily.index.year.isin(years)
    window_daily = daily[window_mask]
    if len(window_daily) < 2:
        return S4PathResult(years, 0.0, 0.0, 0.0, True)

    cumulative = window_daily.iloc[-1] / window_daily.iloc[0] - 1.0
    annual = window_daily.groupby(window_daily.index.year).apply(lambda s: s.iloc[-1] / s.iloc[0] - 1.0)
    worst_year = float(annual.min()) if len(annual) else 0.0
    span_years = len(years)
    window_ann = (1.0 + cumulative) ** (1.0 / span_years) - 1.0 if span_years else 0.0
    passed = bool(cumulative >= S4_CUMULATIVE_FLOOR)

    return S4PathResult(years, cumulative, worst_year, window_ann, passed)


def _classify_stress_result(result: StressResult, metric_value: float | None = None) -> StressResult:
    threshold = DEFAULT_STRESS_THRESHOLDS.get(result.scenario_id)
    if threshold is None or metric_value is None:
        return result
    classification, reasons = threshold.classify(metric_value)
    return replace(result, classification=classification, threshold_reasons=reasons, threshold_basis=threshold.metric_type)


def _persistent_liquidity_result(config: StrategyConfig, sim_result: SimulationResult) -> StressResult:
    medians = _median_quadrant_returns(sim_result.annual_quadrant_returns)
    stressed = dict(medians)
    stressed.update({"stocks": -0.16, "bonds": -0.09, "gold": -0.05, "cash": -0.01})
    port_ret = _portfolio_return_from_quadrants(config, stressed)
    notes = ["correlation convergence across defensive assets", "liquidity drag persists across multiple periods"]
    concurrent = sum(1 for q in ("stocks", "bonds", "gold") if stressed.get(q, 0.0) < 0)
    hedge_failure = 1 if stressed["stocks"] < 0 and (stressed["bonds"] < 0 or stressed["gold"] < 0) else 0
    result = StressResult(
        "S13",
        "Persistent correlation/liquidity stress",
        port_ret,
        abs(min(stressed.values())),
        port_ret > -0.15,
        duration_days=252 * 2,
        liquidity_impairment_days=252,
        concurrent_drawdown_count=concurrent,
        hedge_failure_days=hedge_failure * 252,
        notes=notes,
    )
    return _classify_stress_result(result, port_ret)


def _mechanism_stress_result(config: StrategyConfig, scenario_id: str) -> StressResult:
    name, shocks = STRESS_SCENARIOS[scenario_id]
    port_ret = _portfolio_return_from_quadrants(config, shocks)
    friction = {
        "S15": 0.03,
        "S16": config.qdii_target_weight() * 0.10 + 0.02,
        "S18": 0.04,
        "S19": config.bonds * 0.03,
        "S20": config.cash * 0.04,
        "S21": 0.06,
    }.get(scenario_id, 0.0)
    stressed_return = port_ret - friction
    concurrent = sum(1 for q in ("stocks", "bonds", "gold", "cash") if shocks.get(q, 0.0) < 0)
    hedge_failure = 1 if shocks.get("stocks", 0.0) < 0 and (shocks.get("bonds", 0.0) < 0 or shocks.get("gold", 0.0) < 0) else 0
    result = StressResult(
        scenario_id,
        name,
        stressed_return,
        _worst_shock(shocks),
        stressed_return > -0.18,
        duration_days=252 if scenario_id in {"S15", "S16", "S20", "S21"} else 252 * 2,
        liquidity_impairment_days=63 if scenario_id in {"S15", "S16", "S19", "S20"} else 0,
        concurrent_drawdown_count=concurrent,
        hedge_failure_days=hedge_failure * 126,
        notes=MECHANISM_STRESS_NOTES.get(scenario_id, []),
    )
    return _classify_stress_result(result, stressed_return)


def run_fast_stress_tests(config: StrategyConfig, sim_result: SimulationResult) -> list[StressResult]:
    medians = _median_quadrant_returns(sim_result.annual_quadrant_returns)
    results: list[StressResult] = []
    for sid in sorted(FAST_STRESS_SCENARIOS):
        name, shocks = STRESS_SCENARIOS[sid]
        q_returns = dict(medians)
        q_returns.update(shocks)
        port_ret = _portfolio_return_from_quadrants(config, q_returns)
        worst = _worst_shock(shocks)
        passed = port_ret >= -worst
        result = StressResult(sid, name, port_ret, worst, passed, notes=["one-time shock" if sid != "S9" else "global liquidity shock"])
        results.append(_classify_stress_result(result, port_ret))
    results.append(_persistent_liquidity_result(config, sim_result))
    return results


def _approximate_s5_result(config: StrategyConfig, sim_result: SimulationResult, baseline_ret: float) -> StressResult:
    qdii_fill = sim_result.qdii_metrics.qdii_fill_rate if sim_result.qdii_metrics else 1.0
    qdii_gap = abs(sim_result.qdii_metrics.avg_qdii_weight_gap) if sim_result.qdii_metrics else 0.0
    impact = -(config.qdii_premium * max(0.0, 1.0 - qdii_fill)) - (qdii_gap * 0.5)
    return StressResult("S5", "QDII premium (approximate impact vs baseline)", impact, 0.05, impact > -0.10, notes=["approximate"])


def _approximate_s7_result(config: StrategyConfig, sim_result: SimulationResult, baseline_ret: float) -> StressResult:
    qdii_fill = sim_result.qdii_metrics.qdii_fill_rate if sim_result.qdii_metrics else 1.0
    pending = sim_result.qdii_metrics.avg_pending_cash if sim_result.qdii_metrics else 0.0
    impact = -(1.0 - qdii_fill) * 0.08 - (pending / 1_000_000.0)
    return StressResult("S7", "Low QDII quota (approximate impact vs baseline)", impact, 0.10, True)


def run_full_stress_tests(
    config: StrategyConfig,
    sim_result: SimulationResult,
    prices: pd.DataFrame,
    backup_prices: dict[str, pd.Series] | None = None,
    *,
    include_s4: bool = True,
    include_s5: bool = True,
    include_s7: bool = True,
    mode: StressMode = StressMode.exact,
) -> tuple[list[StressResult], S4PathResult | None]:
    results = [sr for sr in run_fast_stress_tests(config, sim_result) if sr.scenario_id != "S4"]
    baseline_ret = sim_result.daily_values.iloc[-1] / sim_result.daily_values.iloc[0] - 1
    for sid in sorted(FULL_STRESS_SCENARIOS):
        if sid in MECHANISM_STRESS_SCENARIOS:
            results.append(_mechanism_stress_result(config, sid))
        elif sid == "S5" and include_s5:
            if mode == StressMode.exploratory:
                results.append(_approximate_s5_result(config, sim_result, baseline_ret))
            else:
                s5_config = replace(config, qdii_premium=0.05)
                s5_sim = simulate(prices, s5_config, backup_prices=backup_prices)
                s5_ret = s5_sim.daily_values.iloc[-1] / s5_sim.daily_values.iloc[0] - 1
                s5_impact = s5_ret - baseline_ret
                result = StressResult("S5", "QDII premium (impact vs baseline)", s5_impact, 0.05, s5_impact > -0.10)
                results.append(_classify_stress_result(result, s5_impact))
        elif sid == "S7" and include_s7:
            if mode == StressMode.exploratory:
                results.append(_approximate_s7_result(config, sim_result, baseline_ret))
            else:
                low_caps = {code: 10.0 for code in qdii_pool_codes()}
                s7_config = replace(config, qdii_daily_caps=low_caps)
                s7_sim = simulate(prices, s7_config, backup_prices=backup_prices)
                s7_ret = s7_sim.daily_values.iloc[-1] / s7_sim.daily_values.iloc[0] - 1
                s7_impact = s7_ret - baseline_ret
                s7_fill = s7_sim.qdii_metrics.qdii_fill_rate if s7_sim.qdii_metrics else 0.0
                result = StressResult("S7", f"Low QDII quota (fill {s7_fill:.0%}, impact vs baseline)", s7_impact, 0.10, True)
                result = replace(result, threshold_basis="impact_vs_baseline")
                results.append(_classify_stress_result(result, s7_impact))
    s4_path = run_s4_path_test(config, prices, backup_prices=backup_prices, mode=mode) if include_s4 else None
    if s4_path is not None:
        result = StressResult("S4", f"Prolonged low rates ({len(s4_path.window_years)}yr path)", s4_path.cumulative_return, 0.02, s4_path.passed, threshold_basis="cumulative_return")
        result = _classify_stress_result(result, s4_path.cumulative_return)
        if s4_path.worst_year_return < DEFAULT_STRESS_THRESHOLDS["S4"].fail:
            result = replace(result, threshold_reasons=result.threshold_reasons + [f"worst_year_return {s4_path.worst_year_return:.2%} breaches fail floor"])
        results.append(result)
    return results, s4_path


def run_stress_tests(
    config: StrategyConfig,
    sim_result: SimulationResult,
    prices: pd.DataFrame,
    backup_prices: dict[str, pd.Series] | None = None,
    fast_only: bool = False,
) -> tuple[list[StressResult], S4PathResult | None]:
    if fast_only:
        return run_fast_stress_tests(config, sim_result), None
    return run_full_stress_tests(config, sim_result, prices, backup_prices)
