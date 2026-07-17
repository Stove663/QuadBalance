"""Tests for reporting section helpers."""

from __future__ import annotations

import pandas as pd

from quadbalance.reporting_sections import (
    format_boundary_summary,
    format_lifecycle_summary,
    format_profile_suitability_summary,
    format_rebalance_execution_markdown,
    format_stress_summary_markdown,
    format_uncovered_risk_summary,
)
from quadbalance.simulator import LifecycleResult, RebalanceExecutionMetrics, SimulationResult
from quadbalance.stress import StressResult
from quadbalance.validation import ValidationResult
from quadbalance.metrics import PerformanceMetrics


def _metrics() -> PerformanceMetrics:
    return PerformanceMetrics(
        annualized_return=0.1,
        annualized_volatility=0.2,
        max_drawdown=-0.1,
        max_drawdown_peak="2020-01-01",
        max_drawdown_trough="2020-02-01",
        sharpe_ratio=0.5,
        positive_years_pct=1.0,
        rebalance_premium=0.01,
        worst_year_return=-0.05,
        annual_returns=pd.Series(dtype=float),
        max_drawdown_recovery_days=21,
        real_annualized_return=0.08,
        real_terminal_wealth=100.0,
        worst_rolling_3y_real_return=0.02,
        worst_rolling_5y_real_return=0.02,
        longest_underwater_days=50,
        average_drawdown=-0.03,
        ulcer_index=0.04,
        pain_index=0.02,
        cdar_95=-0.08,
        drawdown_10pct_events=1,
        drawdown_15pct_events=0,
        drawdown_20pct_events=0,
    )


def test_format_rebalance_execution_markdown_handles_present_metrics():
    sim = SimulationResult(
        config_id="cfg",
        daily_values=pd.Series([1.0, 1.1], index=pd.to_datetime(["2020-01-01", "2020-01-02"])),
        annual_quadrant_returns=pd.DataFrame(),
        effective_start="2020-01-01",
        effective_end="2020-01-02",
        instrument_starts={},
        rebalance_events=[],
        pending_cash_series=pd.Series(dtype=float),
        backup_events=[],
        qdii_metrics=None,
        rebalance_shortfalls=[],
        rebalance_metrics=RebalanceExecutionMetrics(2, 100.0, 50.0, 0.03),
    )
    text = format_rebalance_execution_markdown(sim)
    assert "Sell shortfall events" in text
    assert "100 CNY" in text


def test_format_boundary_summary_lists_classifications():
    validation = ValidationResult(
        config_id="cfg",
        passed=True,
        failure_reasons=[],
        metrics=_metrics(),
        benchmark_comparison={},
        stress_results=[],
        boundary_classifications={"macro": "review-required", "behavioral": "normal"},
    )
    text = format_boundary_summary(validation)
    assert "macro" in text
    assert "review-required" in text


def test_format_lifecycle_summary_renders_rows():
    text = format_lifecycle_summary([
        LifecycleResult("s1", 100.0, 90.0, -0.2, False, 20),
        LifecycleResult("s2", 80.0, 70.0, -0.3, True, 40),
    ])
    assert "s1" in text and "s2" in text
    assert "✓" in text and "✗" in text


def test_format_profile_suitability_summary_renders_entries():
    validation = ValidationResult(
        config_id="cfg",
        passed=True,
        failure_reasons=[],
        metrics=_metrics(),
        benchmark_comparison={},
        stress_results=[],
        profile_suitability={"accumulation": {"classification": "suitable", "reasons": ["ok"]}},
    )
    text = format_profile_suitability_summary(validation)
    assert "accumulation" in text
    assert "suitable" in text


def test_format_stress_summary_markdown_renders_table():
    text = format_stress_summary_markdown([
        StressResult("S1", "Crash", -0.12, 0.4, False),
        StressResult("S2", "Recovery", 0.05, 0.2, True),
    ])
    assert "Crash" in text
    assert "Recovery" in text


def test_format_uncovered_risk_summary_lists_key_themes():
    validation = ValidationResult(
        config_id="cfg",
        passed=True,
        failure_reasons=[],
        metrics=PerformanceMetrics(
            annualized_return=0.1,
            annualized_volatility=0.2,
            max_drawdown=-0.24,
            max_drawdown_peak="2020-01-01",
            max_drawdown_trough="2020-02-01",
            sharpe_ratio=0.5,
            positive_years_pct=1.0,
            rebalance_premium=0.01,
            worst_year_return=-0.05,
            annual_returns=pd.Series(dtype=float),
            max_drawdown_recovery_days=21,
            real_annualized_return=0.08,
            real_terminal_wealth=100.0,
            worst_rolling_3y_real_return=0.02,
            worst_rolling_5y_real_return=-0.03,
            longest_underwater_days=400,
            average_drawdown=-0.03,
            ulcer_index=0.04,
            pain_index=0.02,
            cdar_95=-0.08,
            drawdown_10pct_events=1,
            drawdown_15pct_events=0,
            drawdown_20pct_events=0,
        ),
        benchmark_comparison={},
        stress_results=[StressResult("S13", "Persistent correlation/liquidity stress", -0.2, 0.2, False)],
        boundary_classifications={},
        lifecycle_results=[],
        long_term_results=[],
        profile_suitability={},
        robustness=None,
        path_stress_results=[type("P", (), {"classification": "review-required"})()],
        behavior_stress_results=[type("B", (), {"triggered": True})()],
        cross_border_stress_results=[type("C", (), {"classification": "review-required"})()],
        product_risk=None,
    )
    text = format_uncovered_risk_summary(validation)
    assert "深回撤" in text
    assert "真实购买力" in text
    assert "路径依赖" in text
