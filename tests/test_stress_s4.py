"""Tests for S4 five-year bond cap stress test."""

from __future__ import annotations

import pandas as pd

from quadbalance.config import StrategyConfig
from quadbalance.stress import cap_bond_annual_returns, get_s4_window_years


def _bond_config() -> StrategyConfig:
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


def test_cap_bond_annual_returns_limits_each_year():
    dates = pd.bdate_range("2020-01-02", "2024-12-31")
    n = len(dates)
    prices = pd.DataFrame(
        {
            "110020": [1.5] * n,
            "161125": [2.0] * n,
            "003358": [1.0 * (1.0004 ** i) for i in range(n)],
            "000216": [1.2] * n,
            "006874": [1.0] * n,
        },
        index=dates,
    )
    config = _bond_config()
    window = get_s4_window_years(prices, 5)
    capped = cap_bond_annual_returns(prices, config, window, cap_rate=0.02)

    for year in window:
        year_prices = capped.loc[capped.index.year == year, "003358"]
        if len(year_prices) < 2:
            continue
        ann = year_prices.iloc[-1] / year_prices.iloc[0] - 1.0
        assert ann <= 0.02 + 1e-9
