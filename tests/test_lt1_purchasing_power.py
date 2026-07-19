"""LT1 calibrated so gold tracks CPI — executable purchasing-power stress."""

from __future__ import annotations

import pandas as pd
import pytest

from quadbalance.asset_universe import QDII_BACKUP_SYMBOLS
from quadbalance.config import StrategyConfig
from quadbalance.data import load_market_data
from quadbalance.long_term_stress import SCENARIOS, run_long_term_scenario


def _lt1():
    return next(s for s in SCENARIOS if s.scenario_id == "LT1")


def test_lt1_gold_nominal_tracks_phase_cpi():
    for phase in _lt1().phases:
        assert phase.gold_return == pytest.approx(phase.cpi)
        # Short cash lags CPI mildly (executable floating-rate proxy), not deeply negative real.
        assert phase.cash_return == pytest.approx(phase.cpi - 0.02)
        assert phase.cash_return > 0


def test_lt1_all_gold_preserves_purchasing_power():
    cfg = StrategyConfig(
        allocation_name="all-gold",
        stocks=0.0,
        bonds=0.0,
        gold=1.0,
        cash=0.0,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
    )
    prices, _, _ = _prices_for(cfg)
    result = run_long_term_scenario(prices, cfg, _lt1())
    assert result.classification == "normal"
    assert result.real_terminal_wealth >= 0.90
    assert result.real_annualized_return >= 0.0


def test_lt1_permanent_portfolio_not_thesis_broken():
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
    prices, _, _ = _prices_for(cfg)
    result = run_long_term_scenario(prices, cfg, _lt1())
    assert result.classification == "review-required"
    assert result.real_terminal_wealth >= 0.55


def test_lt1_sixty_forty_still_thesis_broken():
    cfg = StrategyConfig(
        allocation_name="60-40",
        stocks=0.60,
        bonds=0.40,
        gold=0.0,
        cash=0.0,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
    )
    prices, _, _ = _prices_for(cfg)
    result = run_long_term_scenario(prices, cfg, _lt1())
    assert result.classification == "thesis-broken"


def _prices_for(cfg: StrategyConfig):
    syms = sorted(cfg.simulation_symbols())
    backup = sorted(set(QDII_BACKUP_SYMBOLS) | {s for s in cfg.simulation_symbols() if cfg.is_qdii_symbol(s)})
    return load_market_data(symbols=syms, backup_symbols=tuple(backup), use_cache=True)
