"""Tests for QuadBalance backtest engine."""

from __future__ import annotations

import pandas as pd
import pytest

from quadbalance.config import StrategyConfig
from quadbalance.simulator import simulate
from quadbalance.sweep_space import generate_sweep_configs


@pytest.fixture
def synthetic_prices() -> pd.DataFrame:
    """Synthetic price data for unit tests."""
    dates = pd.bdate_range("2019-04-01", periods=500)
    n = 500
    data = {
        "110020": [1.5 * (1.0003**i) for i in range(n)],
        "050025": [2.0 * (1.0002**i) for i in range(n)],
        "161125": [2.0 * (1.0002**i) for i in range(n)],
        "006075": [2.0 * (1.0002**i) for i in range(n)],
        "003358": [1.0 * (1.0001**i) for i in range(n)],
        "003327": [1.0 * (1.0001**i) for i in range(n)],
        "000216": [1.2 * (1.00015**i) for i in range(n)],
        "006874": [1.0 * (1.00005**i) for i in range(n)],
    }
    return pd.DataFrame(data, index=dates)


def test_generate_sweep_count():
    configs = generate_sweep_configs()
    assert len(configs) == 11 * 3 * 2 * 2  # 132 configurations


def test_simulate_runs(synthetic_prices: pd.DataFrame):
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
    result = simulate(synthetic_prices, config)
    assert len(result.daily_values) > 0
    assert result.daily_values.iloc[-1] > result.daily_values.iloc[0]


def test_instrument_weights_sum_to_one():
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
    weights = config.instrument_weights()
    assert abs(sum(weights.values()) - 1.0) < 1e-9
