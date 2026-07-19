"""Tests for Criterion 3 review-vs-fail acceptance split."""

from __future__ import annotations

import pandas as pd

from quadbalance.config import StrategyConfig
from quadbalance.cross_border_stress import CrossBorderStressResult, _classify, run_cross_border_stress_tests
from quadbalance.metrics import PerformanceMetrics
from quadbalance.reporting_sections import format_boundary_summary
from quadbalance.stress import StressResult
from quadbalance.validation import ValidationResult, evaluate_acceptance


def _config(**kwargs) -> StrategyConfig:
    base = dict(
        allocation_name="25-25-25-25",
        stocks=0.25,
        bonds=0.25,
        gold=0.25,
        cash=0.25,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
    )
    base.update(kwargs)
    return StrategyConfig(**base)


def _metrics(**overrides) -> PerformanceMetrics:
    data = dict(
        annualized_return=0.10,
        annualized_volatility=0.12,
        max_drawdown=-0.12,
        max_drawdown_peak="2020-01-01",
        max_drawdown_trough="2020-03-01",
        sharpe_ratio=0.8,
        positive_years_pct=0.8,
        rebalance_premium=0.01,
        worst_year_return=-0.08,
        annual_returns=pd.Series(dtype=float),
        max_drawdown_recovery_days=40,
        real_annualized_return=0.07,
        real_terminal_wealth=120.0,
        worst_rolling_3y_real_return=0.02,
        worst_rolling_5y_real_return=0.01,
        longest_underwater_days=80,
    )
    data.update(overrides)
    return PerformanceMetrics(**data)


def _bench(metrics: PerformanceMetrics) -> dict:
    cash = _metrics(annualized_return=0.02, max_drawdown=-0.01)
    sixty = _metrics(annualized_return=0.09, max_drawdown=-0.20)
    return {"cash": cash, "60_40": sixty}


def test_cb3_moderate_qdii_is_not_auto_thesis_broken():
    config = _config(stocks=0.25, stock_sub_split="60-40")
    results = {r.scenario_id: r for r in run_cross_border_stress_tests(config)}
    assert results["CB3"].classification == "review-required"
    assert results["CB3"].frozen_asset_weight < 0.30
    assert results["CB3"].capital_mobility_constraint_months >= 18


def test_cb3_severe_frozen_weight_is_review_not_thesis_broken():
    result = CrossBorderStressResult(
        "CB3",
        "Severe external asset availability constraint",
        portfolio_return=-0.20,
        liquid_portfolio_return=-0.25,
        frozen_asset_weight=0.35,
        qdii_haircut=0.65,
        liquidity_impairment_months=24,
        capital_mobility_constraint_months=24,
        rebalance_locked_months=18,
        classification="normal",
        reasons=[],
    )
    classified = _classify(result)
    assert classified.classification == "review-required"


def test_cb3_severe_portfolio_loss_is_thesis_broken():
    result = CrossBorderStressResult(
        "CB3",
        "Severe external asset availability constraint",
        portfolio_return=-0.35,
        liquid_portfolio_return=-0.40,
        frozen_asset_weight=0.35,
        qdii_haircut=0.65,
        liquidity_impairment_months=24,
        capital_mobility_constraint_months=24,
        rebalance_locked_months=18,
        classification="normal",
        reasons=[],
    )
    classified = _classify(result)
    assert classified.classification == "thesis-broken"


def test_acceptance_passes_with_review_required_only():
    config = _config()
    metrics = _metrics()
    stress = [
        StressResult("S20", "Cash liquidity", -0.04, 0.06, True, classification="review-required"),
        StressResult(
            "S13",
            "Persistent correlation",
            -0.08,
            0.16,
            True,
            classification="review-required",
            liquidity_impairment_days=252,
        ),
    ]
    cross = [
        CrossBorderStressResult(
            "CB1",
            "friction",
            -0.02,
            -0.03,
            0.05,
            0.08,
            6,
            6,
            3,
            "review-required",
            [],
        )
    ]
    validation = evaluate_acceptance(
        config,
        metrics,
        _bench(metrics),
        stress,
        cross_border_stress_results=cross,
    )
    assert validation.passed is True
    assert validation.failure_reasons == []
    assert any("S20" in item for item in validation.needs_review)
    assert any("CB1" in item for item in validation.needs_review)
    assert any("prolonged liquidity" in item for item in validation.needs_review)
    assert all("requires review" not in r for r in validation.failure_reasons)
    assert validation.lockable is False
    assert any("CB1" in item for item in validation.material_needs_review)


def test_acceptance_fails_on_thesis_broken():
    config = _config()
    metrics = _metrics()
    stress = [StressResult("S14", "Quad hedge failure", -0.30, 0.20, False, classification="thesis-broken")]
    validation = evaluate_acceptance(config, metrics, _bench(metrics), stress, cross_border_stress_results=[])
    assert validation.passed is False
    assert any("S14" in r and "thesis-broken" in r for r in validation.failure_reasons)


def test_boundary_summary_lists_needs_review():
    validation = ValidationResult(
        config_id="cfg",
        passed=True,
        failure_reasons=[],
        metrics=_metrics(),
        benchmark_comparison={},
        stress_results=[],
        boundary_classifications={"macro": "normal"},
        needs_review=["Criterion 3: stress S20 requires review"],
    )
    text = format_boundary_summary(validation)
    assert "Needs Review" in text
    assert "S20" in text
