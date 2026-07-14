"""Tests for deterministic multi-key strategy lock selection."""

from __future__ import annotations

import pandas as pd

from quadbalance.config import StrategyConfig
from quadbalance.metrics import PerformanceMetrics
from quadbalance.simulator import QdiiExecutionMetrics, SimulationResult
from quadbalance.sweep import prefer_lock_candidate
from quadbalance.validation import ValidationResult


def _metrics(**kwargs) -> PerformanceMetrics:
    defaults = dict(
        annualized_return=0.08,
        annualized_volatility=0.10,
        max_drawdown=-0.12,
        max_drawdown_peak="2020-01-01",
        max_drawdown_trough="2020-03-01",
        sharpe_ratio=0.5,
        positive_years_pct=0.8,
        rebalance_premium=0.0,
        worst_year_return=-0.05,
        annual_returns=pd.Series(dtype=float),
    )
    defaults.update(kwargs)
    return PerformanceMetrics(**defaults)


def _bundle(
    config_id_suffix: str,
    *,
    annualized_return: float = 0.08,
    max_drawdown: float = -0.12,
    qdii_fill: float = 0.95,
    classification: str = "caution",
    stock_sub_split: str = "60-40",
) -> tuple:
    config = StrategyConfig(
        allocation_name="25-25-25-25",
        stocks=0.25,
        bonds=0.25,
        gold=0.25,
        cash=0.25,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
        stock_sub_split=stock_sub_split,  # type: ignore[arg-type]
    )
    # Force distinct config_id suffixes via allocation_name hack when needed
    if config_id_suffix:
        object.__setattr__(config, "allocation_name", config_id_suffix)

    validation = ValidationResult(
        config_id=config.config_id,
        passed=True,
        failure_reasons=[],
        metrics=_metrics(annualized_return=annualized_return, max_drawdown=max_drawdown),
        benchmark_comparison={},
        stress_results=[],
        profile_suitability={"accumulation": {"classification": classification, "reasons": []}},
    )
    result = SimulationResult(
        config_id=config.config_id,
        daily_values=pd.Series([1.0, 1.1]),
        annual_quadrant_returns=pd.DataFrame(),
        effective_start="2019-01-01",
        effective_end="2020-01-01",
        instrument_starts={},
        qdii_metrics=QdiiExecutionMetrics(qdii_fill, 0.0, 0.0, 0, 0.0),
    )
    return validation, config, result


def test_intended_profile_prefers_higher_suitability():
    current = _bundle("aaa", classification="caution", annualized_return=0.12)
    candidate = _bundle("bbb", classification="suitable", annualized_return=0.05)
    chosen = prefer_lock_candidate(current, candidate, "accumulation")
    assert chosen[1].allocation_name == "bbb"


def test_return_breaks_tie_when_suitability_equal():
    current = _bundle("aaa", classification="suitable", annualized_return=0.08)
    candidate = _bundle("bbb", classification="suitable", annualized_return=0.10)
    chosen = prefer_lock_candidate(current, candidate, "accumulation")
    assert chosen[1].allocation_name == "bbb"


def test_lower_abs_mdd_breaks_tie():
    current = _bundle("aaa", classification="suitable", annualized_return=0.10, max_drawdown=-0.20)
    candidate = _bundle("bbb", classification="suitable", annualized_return=0.10, max_drawdown=-0.10)
    chosen = prefer_lock_candidate(current, candidate, "accumulation")
    assert chosen[1].allocation_name == "bbb"


def test_higher_qdii_fill_breaks_tie():
    current = _bundle("aaa", classification="suitable", annualized_return=0.10, max_drawdown=-0.10, qdii_fill=0.80)
    candidate = _bundle("bbb", classification="suitable", annualized_return=0.10, max_drawdown=-0.10, qdii_fill=0.99)
    chosen = prefer_lock_candidate(current, candidate, "accumulation")
    assert chosen[1].allocation_name == "bbb"


def test_lexicographic_config_id_final_tiebreak():
    current = _bundle("zzz", classification="suitable", annualized_return=0.10, max_drawdown=-0.10, qdii_fill=1.0)
    candidate = _bundle("aaa", classification="suitable", annualized_return=0.10, max_drawdown=-0.10, qdii_fill=1.0)
    chosen = prefer_lock_candidate(current, candidate, "accumulation")
    assert chosen[1].allocation_name == "aaa"


def test_no_intended_profile_skips_suitability_rank():
    # Candidate has worse suitability but better return — without intended profile, return wins.
    current = _bundle("aaa", classification="suitable", annualized_return=0.05)
    candidate = _bundle("bbb", classification="unsuitable", annualized_return=0.12)
    chosen = prefer_lock_candidate(current, candidate, None)
    assert chosen[1].allocation_name == "bbb"
