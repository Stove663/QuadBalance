"""Tests for drawdown and stress-gap coverage."""

from __future__ import annotations

from quadbalance.cross_border_stress import run_cross_border_stress_tests
from quadbalance.config import StrategyConfig
from quadbalance.reporting_sections import format_uncovered_risk_summary
from quadbalance.stress_scenarios import STRESS_SCENARIOS


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


def test_stress_scenarios_include_s22_to_s27():
    for scenario_id in ("S22", "S23", "S24", "S25", "S26", "S27"):
        assert scenario_id in STRESS_SCENARIOS


def test_cross_border_stress_tests_return_expected_scenarios():
    config = _config()
    results = run_cross_border_stress_tests(config)
    scenario_ids = {result.scenario_id for result in results}
    assert {"CB1", "CB2", "CB3"} <= scenario_ids
    assert all(result.classification in {"normal", "review-required", "thesis-broken"} for result in results)


def test_uncovered_risk_summary_mentions_key_themes():
    class _DummyMetrics:
        max_drawdown = -0.24
        worst_rolling_5y_real_return = -0.03
        longest_underwater_days = 400
        pain_index = 0.02

    class _DummyValidation:
        metrics = _DummyMetrics()
        path_stress_results = []
        behavior_stress_results = []
        cross_border_stress_results = []
        product_risk = None
        stress_results = []

    text = format_uncovered_risk_summary(_DummyValidation())
    assert "深回撤" in text
    assert "真实购买力" in text
