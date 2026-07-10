"""Stress test scenarios S1-S6."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quadbalance.config import StrategyConfig
from quadbalance.simulator import SimulationResult, simulate


@dataclass
class StressResult:
    scenario_id: str
    scenario_name: str
    portfolio_return: float
    worst_quadrant_shock: float
    passed: bool


STRESS_SCENARIOS = {
    "S1": ("A-share crash", {"stocks": -0.40}),
    "S2": ("Stock-bond dual kill", {"stocks": -0.20, "bonds": 0.0, "gold": 0.10, "cash": 0.02}),
    "S3": (
        "CNY depreciation",
        {"stocks": 0.048, "bonds": 0.0, "gold": 0.08, "cash": 0.0},
    ),
    "S4": ("Prolonged low rates", {"bonds": 0.02}),
    "S6": ("Gold crash", {"gold": -0.20}),
}


def _median_quadrant_returns(annual_q: pd.DataFrame) -> dict[str, float]:
    return {
        col: float(annual_q[col].median())
        for col in ("stocks", "bonds", "gold", "cash")
        if col in annual_q.columns
    }


def _portfolio_return_from_quadrants(
    config: StrategyConfig, quadrant_returns: dict[str, float]
) -> float:
    w = config.quadrant_weights
    return sum(w[q] * quadrant_returns.get(q, 0.0) for q in w)


def _worst_shock(quadrant_returns: dict[str, float]) -> float:
    return abs(min(quadrant_returns.values()))


def run_stress_tests(
    config: StrategyConfig,
    sim_result: SimulationResult,
    prices: pd.DataFrame,
) -> list[StressResult]:
    medians = _median_quadrant_returns(sim_result.annual_quadrant_returns)
    results: list[StressResult] = []

    for sid, (name, shocks) in STRESS_SCENARIOS.items():
        q_returns = dict(medians)
        q_returns.update(shocks)
        port_ret = _portfolio_return_from_quadrants(config, q_returns)
        worst = _worst_shock(shocks)
        passed = port_ret >= -worst
        results.append(StressResult(sid, name, port_ret, worst, passed))

    # S5: QDII premium — re-run simulation with 5% premium on 513500 buys
    s5_config = StrategyConfig(
        allocation_name=config.allocation_name,
        stocks=config.stocks,
        bonds=config.bonds,
        gold=config.gold,
        cash=config.cash,
        bond_variant=config.bond_variant,
        dca_method=config.dca_method,
        rebalance_threshold=config.rebalance_threshold,
        qdii_premium=0.05,
    )
    baseline_ret = sim_result.daily_values.iloc[-1] / sim_result.daily_values.iloc[0] - 1
    s5_sim = simulate(prices, s5_config)
    s5_ret = s5_sim.daily_values.iloc[-1] / s5_sim.daily_values.iloc[0] - 1
    s5_impact = s5_ret - baseline_ret
    results.append(
        StressResult("S5", "QDII premium (impact vs baseline)", s5_impact, 0.05, s5_impact > -0.10)
    )

    return results
