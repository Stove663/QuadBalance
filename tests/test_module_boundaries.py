"""Tests for refactored module boundaries and constants."""

from __future__ import annotations

import pandas as pd

from quadbalance.asset_universe import ALL_SYMBOLS, BENCHMARK_BOND, BENCHMARK_CASH, BENCHMARK_CSI300, QDII_BACKUP_SYMBOLS
from quadbalance.config import StrategyConfig
from quadbalance.instrument_catalog import BACKTEST_PROXIES, qdii_pool_codes
from quadbalance.portfolio_templates import ALLOCATION_VARIANTS
from quadbalance.reporting_sections import format_s4_path_markdown
from quadbalance.sweep_constants import DEFAULT_INFLATION_ANN, STRATEGY_LOCK_FILENAME, SWEEP_RESULTS_FILENAME
from quadbalance.sweep_space import generate_sweep_configs, SWEEP_BOND_VARIANTS, SWEEP_DCA_METHODS, SWEEP_REBALANCE_THRESHOLDS
from quadbalance.stress import S4PathResult


def test_asset_universe_symbols_and_benchmarks():
    assert BENCHMARK_CSI300 == "110020"
    assert BENCHMARK_BOND == "003358"
    assert BENCHMARK_CASH == "006874"
    assert "110020" in ALL_SYMBOLS
    assert "003358" in ALL_SYMBOLS
    for sym in QDII_BACKUP_SYMBOLS:
        assert sym not in ALL_SYMBOLS


def test_instrument_catalog_qdii_pool_codes_are_ranked():
    assert qdii_pool_codes() == ["161125", "050025", "006075"]
    assert set(BACKTEST_PROXIES) == {"006874", "161125", "003358", "003327", "000216"}


def test_portfolio_templates_cover_expected_allocations():
    assert len(ALLOCATION_VARIANTS) >= 8
    assert ALLOCATION_VARIANTS["25-25-25-25"] == (0.25, 0.25, 0.25, 0.25)


def test_sweep_space_generates_expected_cartesian_product():
    configs = generate_sweep_configs()
    assert len(SWEEP_BOND_VARIANTS) == 3
    assert len(SWEEP_DCA_METHODS) == 2
    assert len(SWEEP_REBALANCE_THRESHOLDS) == 2
    assert len(configs) == len(ALLOCATION_VARIANTS) * len(SWEEP_BOND_VARIANTS) * len(SWEEP_DCA_METHODS) * len(SWEEP_REBALANCE_THRESHOLDS)


def test_sweep_constants_are_stable():
    assert DEFAULT_INFLATION_ANN == 0.03
    assert SWEEP_RESULTS_FILENAME.endswith(".csv")
    assert STRATEGY_LOCK_FILENAME.endswith(".md")


def test_format_s4_path_markdown_contains_key_fields():
    s4 = S4PathResult(
        window_years=[2020, 2021, 2022, 2023, 2024],
        cumulative_return=0.12,
        worst_year_return=-0.05,
        window_annualized_return=0.023,
        passed=True,
    )
    text = format_s4_path_markdown(s4)
    assert "S4 Five-Year Path" in text
    assert "2020, 2021, 2022, 2023, 2024" in text
    assert "12.00%" in text


def test_strategy_config_fills_default_qdii_caps():
    cfg = StrategyConfig(
        allocation_name="25-25-25-25",
        stocks=0.25,
        bonds=0.25,
        gold=0.25,
        cash=0.25,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
    )
    assert set(cfg.qdii_daily_caps) == set(qdii_pool_codes())
    assert all(v > 0 for v in cfg.qdii_daily_caps.values())
