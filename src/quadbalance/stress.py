"""Stress test scenarios and path simulation."""

from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from quadbalance.config import StrategyConfig
from quadbalance.instrument_pool import qdii_pool_codes
from quadbalance.simulator import SimulationResult, simulate
from quadbalance.stress_scenarios import STRESS_SCENARIOS


@dataclass
class StressResult:
    scenario_id: str
    scenario_name: str
    portfolio_return: float
    worst_quadrant_shock: float
    passed: bool


@dataclass
class S4PathResult:
    window_years: list[int]
    cumulative_return: float
    worst_year_return: float
    window_annualized_return: float
    passed: bool


S4_CUMULATIVE_FLOOR = -0.10
FAST_STRESS_SCENARIOS = {sid for sid in STRESS_SCENARIOS if sid in {"S1", "S2", "S3", "S6"}}
FULL_STRESS_SCENARIOS = {sid for sid in STRESS_SCENARIOS if sid not in FAST_STRESS_SCENARIOS}


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
) -> S4PathResult:
    """Full simulation with bond returns capped for consecutive calendar years."""
    years = get_s4_window_years(prices, window_years)
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
    passed = cumulative >= S4_CUMULATIVE_FLOOR

    return S4PathResult(years, cumulative, worst_year, window_ann, passed)


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
        results.append(StressResult(sid, name, port_ret, worst, passed))
    return results


def run_full_stress_tests(
    config: StrategyConfig,
    sim_result: SimulationResult,
    prices: pd.DataFrame,
    backup_prices: dict[str, pd.Series] | None = None,
) -> tuple[list[StressResult], S4PathResult]:
    results = run_fast_stress_tests(config, sim_result)
    baseline_ret = sim_result.daily_values.iloc[-1] / sim_result.daily_values.iloc[0] - 1
    for sid in sorted(FULL_STRESS_SCENARIOS):
        if sid == "S5":
            s5_config = replace(config, qdii_premium=0.05)
            s5_sim = simulate(prices, s5_config, backup_prices=backup_prices)
            s5_ret = s5_sim.daily_values.iloc[-1] / s5_sim.daily_values.iloc[0] - 1
            s5_impact = s5_ret - baseline_ret
            results.append(StressResult("S5", "QDII premium (impact vs baseline)", s5_impact, 0.05, s5_impact > -0.10))
        elif sid == "S7":
            low_caps = {code: 10.0 for code in qdii_pool_codes()}
            s7_config = replace(config, qdii_daily_caps=low_caps)
            s7_sim = simulate(prices, s7_config, backup_prices=backup_prices)
            s7_ret = s7_sim.daily_values.iloc[-1] / s7_sim.daily_values.iloc[0] - 1
            s7_impact = s7_ret - baseline_ret
            s7_fill = s7_sim.qdii_metrics.qdii_fill_rate if s7_sim.qdii_metrics else 0.0
            results.append(StressResult("S7", f"Low QDII quota (fill {s7_fill:.0%}, impact vs baseline)", s7_impact, 0.10, True))
    s4_path = run_s4_path_test(config, prices, backup_prices=backup_prices)
    results.append(StressResult("S4", f"Prolonged low rates ({len(s4_path.window_years)}yr path)", s4_path.cumulative_return, 0.02, s4_path.passed))
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
