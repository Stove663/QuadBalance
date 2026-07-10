"""Tests for QDII daily quota simulation."""

from __future__ import annotations

import pandas as pd
import pytest

from quadbalance.config import QDII_BACKUP_SYMBOLS, StrategyConfig
from quadbalance.simulator import simulate

_BACKUP_COLS = set(QDII_BACKUP_SYMBOLS)


def _split_prices(prices: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    backup_prices = {col: prices[col] for col in prices.columns if col in _BACKUP_COLS}
    core = prices.drop(columns=[c for c in prices.columns if c in _BACKUP_COLS])
    return core, backup_prices


@pytest.fixture
def short_prices() -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-02", periods=5)
    n = 5
    return pd.DataFrame(
        {
            "110020": [1.5] * n,
            "161125": [2.0] * n,
            "050025": [2.0] * n,
            "006075": [2.0] * n,
            "003358": [1.0] * n,
            "000216": [1.2] * n,
            "006874": [1.0] * n,
        },
        index=dates,
    )


def _base_config(**kwargs) -> StrategyConfig:
    defaults = dict(
        allocation_name="25-25-25-25",
        stocks=0.25,
        bonds=0.25,
        gold=0.25,
        cash=0.25,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
        enable_qdii_quota=True,
        qdii_daily_caps={"161125": 100.0, "050025": 100.0, "006075": 100.0},
    )
    defaults.update(kwargs)
    return StrategyConfig(**defaults)


def _run(short_prices: pd.DataFrame, config: StrategyConfig, **kwargs):
    core, backup_prices = _split_prices(short_prices)
    return simulate(core, config, backup_prices=backup_prices, **kwargs)


def test_dca_exceeds_daily_cap_creates_pending_cash(short_prices: pd.DataFrame):
    config = _base_config()
    result = _run(short_prices, config, base_capital=100_000.0, monthly_contribution=0.0)
    # QDII intent 10,000; 300/day across primary + backups (100 each)
    assert result.pending_cash_series.iloc[0] == pytest.approx(9_700.0)
    assert result.qdii_metrics is not None
    assert result.qdii_metrics.qdii_fill_rate < 0.2


def test_quota_resets_next_day_and_fills_pending(short_prices: pd.DataFrame):
    config = _base_config()
    result = _run(short_prices, config, base_capital=100_000.0, monthly_contribution=0.0)
    assert result.pending_cash_series.iloc[0] == pytest.approx(9_700.0)
    assert result.pending_cash_series.iloc[1] == pytest.approx(9_400.0)


def test_primary_exhausted_routes_to_backup(short_prices: pd.DataFrame):
    config = _base_config(
        qdii_daily_caps={"161125": 0.0, "050025": 500.0, "006075": 100.0},
    )
    result = _run(short_prices, config, base_capital=50_000.0, monthly_contribution=0.0)
    # QDII intent 5,000; primary blocked; backup takes up to 500/day
    assert any("161125→050025" in e for e in result.backup_events)
    assert result.qdii_metrics is not None
    assert result.qdii_metrics.qdii_fill_rate > 0.05


def test_portfolio_value_includes_pending_cash(short_prices: pd.DataFrame):
    config = _base_config()
    result = _run(short_prices, config, base_capital=100_000.0, monthly_contribution=0.0)
    assert result.pending_cash_series.iloc[0] == pytest.approx(9_700.0)
    assert result.daily_values.iloc[0] > 0
