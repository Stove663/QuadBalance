"""Criterion 3 calibration: annualized S7 impact, shallow unrecovered DD, CB3 outcomes."""

from __future__ import annotations

import pandas as pd
import pytest

from quadbalance.config import StrategyConfig
from quadbalance.cross_border_stress import CrossBorderStressResult, _classify
from quadbalance.metrics import PerformanceMetrics
from quadbalance.stress import _annualized_twr_impact
from quadbalance.validation import evaluate_acceptance


def _metrics(**overrides) -> PerformanceMetrics:
    base = dict(
        annualized_return=0.08,
        annualized_volatility=0.1,
        max_drawdown=-0.08,
        max_drawdown_peak="2020-01-01",
        max_drawdown_trough="2020-06-01",
        sharpe_ratio=0.5,
        positive_years_pct=1.0,
        rebalance_premium=0.0,
        worst_year_return=-0.05,
        annual_returns=pd.Series(dtype=float),
        max_drawdown_recovery_days=None,
        real_annualized_return=0.05,
        real_terminal_wealth=1.1,
    )
    base.update(overrides)
    return PerformanceMetrics(**base)


def test_annualized_twr_impact_scales_with_horizon():
    # ~8y: cumulative -32% is only a few pp annualized.
    impact = _annualized_twr_impact(baseline_total=0.918, stressed_total=0.594, years=8.0)
    assert impact == pytest.approx(-0.025, abs=0.005)
    assert impact > -0.08  # would not be thesis-broken under S7 fail floor


def test_shallow_unrecovered_drawdown_is_review_not_fail():
    from quadbalance.benchmarks import BenchmarkResult

    cash = BenchmarkResult("cash", 0.02, -0.01, pd.Series(dtype=float))
    sixty = BenchmarkResult("60_40", 0.06, -0.15, pd.Series(dtype=float))
    config = StrategyConfig(
        allocation_name="25-25-25-25",
        stocks=0.25,
        bonds=0.25,
        gold=0.25,
        cash=0.25,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
    )
    metrics = _metrics(max_drawdown=-0.08, max_drawdown_recovery_days=None, annualized_return=0.08)
    result = evaluate_acceptance(config, metrics, {"cash": cash, "60_40": sixty, "csi300": sixty}, [])
    assert not any("never recovered" in r for r in result.failure_reasons)
    assert any("not fully recovered" in r for r in result.needs_review)


def test_deep_unrecovered_drawdown_still_fails():
    from quadbalance.benchmarks import BenchmarkResult

    cash = BenchmarkResult("cash", 0.02, -0.01, pd.Series(dtype=float))
    sixty = BenchmarkResult("60_40", 0.06, -0.15, pd.Series(dtype=float))
    config = StrategyConfig(
        allocation_name="25-25-25-25",
        stocks=0.25,
        bonds=0.25,
        gold=0.25,
        cash=0.25,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
    )
    metrics = _metrics(max_drawdown=-0.18, max_drawdown_recovery_days=None, annualized_return=0.08)
    result = evaluate_acceptance(config, metrics, {"cash": cash, "60_40": sixty, "csi300": sixty}, [])
    assert any("never recovered" in r for r in result.failure_reasons)


def test_cb3_frozen_weight_alone_is_review_not_thesis_broken():
    result = CrossBorderStressResult(
        "CB3",
        "severe",
        portfolio_return=-0.12,
        liquid_portfolio_return=-0.05,
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
    assert classified.frozen_asset_weight >= 0.30
