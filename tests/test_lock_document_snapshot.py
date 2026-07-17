"""Snapshot-style tests for strategy lock document sections."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from quadbalance.config import StrategyConfig
from quadbalance.metrics import PerformanceMetrics
from quadbalance.reporting import generate_lock_document
from quadbalance.simulator import SimulationResult
from quadbalance.validation import ValidationResult


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
        worst_rolling_1y_return=0.01,
        worst_rolling_3y_return=0.02,
        worst_rolling_5y_return=0.03,
        worst_rolling_1y_real_return=0.0,
        worst_rolling_3y_real_return=0.01,
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


def test_lock_document_includes_uncovered_risk_summary(tmp_path: Path):
    config = _config()
    sim = SimulationResult(
        config_id=config.config_id,
        daily_values=pd.Series([1.0, 1.1], index=pd.to_datetime(["2020-01-01", "2020-01-02"])),
        annual_quadrant_returns=pd.DataFrame(),
        effective_start="2020-01-01",
        effective_end="2020-01-02",
        instrument_starts={},
        qdii_metrics=None,
    )
    validation = ValidationResult(
        config_id=config.config_id,
        passed=True,
        failure_reasons=[],
        metrics=_metrics(),
        benchmark_comparison={},
        stress_results=[],
        boundary_classifications={},
        lifecycle_results=[],
        long_term_results=[],
        profile_suitability={},
        robustness=None,
        path_stress_results=[],
        behavior_stress_results=[],
        cross_border_stress_results=[],
        product_risk=None,
    )
    out = tmp_path / "strategy-lock.md"
    generate_lock_document(config, sim, validation, out)
    text = out.read_text(encoding="utf-8")
    assert "## Uncovered Risk Summary" in text
    assert "## Risk Overview Panel" in text
    assert "## Stress Test Summary" in text
