"""Tests for optimized stress runtime behavior."""

from __future__ import annotations

import pandas as pd

from quadbalance.config import StrategyConfig
from quadbalance.simulator import SimulationResult
from quadbalance.stress import StressMode, run_full_stress_tests, run_s4_path_test


def _config() -> StrategyConfig:
    return StrategyConfig(
        allocation_name="25-25-25-25",
        stocks=0.25,
        bonds=0.25,
        gold=0.25,
        cash=0.25,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
    )


def _simulation_result() -> SimulationResult:
    dates = pd.bdate_range("2020-01-02", periods=10)
    daily_values = pd.Series(range(100, 110), index=dates)
    annual_quadrant_returns = pd.DataFrame({"stocks": [0.05], "bonds": [0.02], "gold": [0.01], "cash": [0.0]})
    return SimulationResult(
        config_id="test",
        daily_values=daily_values,
        annual_quadrant_returns=annual_quadrant_returns,
        effective_start=str(dates[0].date()),
        effective_end=str(dates[-1].date()),
        instrument_starts={},
    )


def test_exploratory_s5_s7_returns_approximate_modes():
    config = _config()
    sim = _simulation_result()
    prices = pd.DataFrame({"003358": [1.0, 1.01, 1.02], "000216": [1.0, 1.0, 1.0], "006874": [1.0, 1.0, 1.0]}, index=pd.bdate_range("2020-01-02", periods=3))
    results, _ = run_full_stress_tests(config, sim, prices, mode=StressMode.exploratory, include_s4=False)
    scenario_ids = {r.scenario_id for r in results}
    assert "S5" in scenario_ids
    assert "S7" in scenario_ids
    assert "S13" in scenario_ids


def test_s13_persistent_stress_includes_liquidity_notes():
    config = _config()
    sim = _simulation_result()
    result = [r for r in run_full_stress_tests(config, sim, pd.DataFrame({"003358": [1.0], "000216": [1.0], "006874": [1.0]}, index=pd.bdate_range("2020-01-02", periods=1)), include_s4=False)[0] if r.scenario_id == "S13"][0]
    assert result.duration_days > 0
    assert result.liquidity_impairment_days > 0
    assert result.concurrent_drawdown_count >= 1
    assert result.notes


def test_s4_window_mode_returns_result():
    config = _config()
    dates = pd.bdate_range("2019-01-02", "2024-12-31")
    prices = pd.DataFrame(
        {"110020": [1.0] * len(dates), "003358": [1.0] * len(dates), "000216": [1.0] * len(dates), "006874": [1.0] * len(dates)},
        index=dates,
    )
    result = run_s4_path_test(config, prices, mode=StressMode.exploratory)
    assert result.window_years
    assert result.passed is True
