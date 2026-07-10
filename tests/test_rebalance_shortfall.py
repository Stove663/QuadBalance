"""Tests for rebalance sell shortfall propagation."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from quadbalance.config import StrategyConfig
from quadbalance.simulator import (
    _rebalance,
    _SimContext,
    simulate,
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
        enable_qdii_quota=False,
    )
    defaults.update(kwargs)
    return StrategyConfig(**defaults)


@pytest.fixture
def two_year_prices() -> pd.DataFrame:
    """Prices with strong stock rally to trigger annual rebalance."""
    dates = pd.bdate_range("2020-01-02", periods=520)
    n = len(dates)
    return pd.DataFrame(
        {
            "110020": [1.5 * (1.0008**i) for i in range(n)],
            "161125": [2.0] * n,
            "003358": [1.0] * n,
            "000216": [1.2] * n,
            "006874": [1.0] * n,
        },
        index=dates,
    )


def test_rebalance_metrics_populated(two_year_prices: pd.DataFrame):
    config = _base_config()
    result = simulate(two_year_prices, config, monthly_contribution=0.0)
    assert result.rebalance_metrics is not None
    assert result.rebalance_metrics.max_post_rebalance_deviation >= 0.0


@patch("quadbalance.simulator.redemption_fee_rate", return_value=0.01)
def test_sell_shortfall_logged_with_transaction_cost(mock_fee):
    """Full liquidation sell with fees produces shortfall events in rebalance."""
    dates = pd.bdate_range("2021-01-04", periods=2)
    prices = pd.DataFrame(
        {
            "110020": [10.0, 10.0],
            "161125": [2.0, 2.0],
            "003358": [1.0, 1.0],
            "000216": [1.0, 1.0],
            "006874": [1.0, 1.0],
        },
        index=dates,
    )
    config = StrategyConfig(
        allocation_name="50-25-0-25",
        stocks=0.5,
        bonds=0.25,
        gold=0.0,
        cash=0.25,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
        enable_qdii_quota=False,
    )
    shares = {
        "110020": 4000.0,
        "161125": 0.0,
        "003358": 2500.0,
        "000216": 2000.0,
        "006874": 2500.0,
    }
    ctx = _SimContext()
    _rebalance(shares, prices.iloc[1], config, ctx=ctx, dt=dates[1])

    assert ctx.rebalance_shortfalls
    assert any(e.symbol == "000216" for e in ctx.rebalance_shortfalls)
    assert all(e.shortfall_cny > 0 for e in ctx.rebalance_shortfalls)
    mock_fee.assert_called()


@patch("quadbalance.simulator.redemption_fee_rate", return_value=0.5)
def test_rebalance_buy_capped_when_sell_proceeds_insufficient(mock_fee):
    """High sell cost leaves insufficient cash pool for full underweight buys."""
    dates = pd.bdate_range("2021-01-04", periods=3)
    prices = pd.DataFrame(
        {
            "110020": [10.0, 10.0, 10.0],
            "161125": [2.0, 2.0, 2.0],
            "003358": [1.0, 1.0, 1.0],
            "000216": [1.0, 1.0, 1.0],
            "006874": [1.0, 1.0, 1.0],
        },
        index=dates,
    )
    config = _base_config()
    shares = {
        "110020": 8000.0,
        "161125": 0.0,
        "003358": 1000.0,
        "000216": 1000.0,
        "006874": 1000.0,
    }
    ctx = _SimContext()
    dt = dates[1]
    day_prices = prices.loc[dt]

    bonds_before = shares["003358"]
    _rebalance(shares, day_prices, config, ctx=ctx, dt=dt)
    bonds_after = shares["003358"]

    bonds_bought = bonds_after - bonds_before

    assert ctx.rebalance_shortfalls
    assert bonds_bought < 15_000
    mock_fee.assert_called()
