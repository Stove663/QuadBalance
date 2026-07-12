"""Tests for reporting section helpers."""

from __future__ import annotations

import pandas as pd

from quadbalance.reporting_sections import (
    format_boundary_summary,
    format_lifecycle_summary,
    format_profile_suitability_summary,
    format_rebalance_execution_markdown,
    format_stress_summary_markdown,
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
