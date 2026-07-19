"""Portfolio NAV must not drop phantom holdings when backup NAVs skip a day."""

from __future__ import annotations

import pandas as pd

from quadbalance.config import StrategyConfig
from quadbalance.simulator import _merge_day_prices, simulate


def test_merge_day_prices_forward_fills_missing_backup_nav():
    core = pd.Series({"110020": 1.0, "161125": 2.0, "003358": 1.0, "000216": 1.0, "006874": 1.0})
    backup = {
        "050025": pd.Series(
            [2.5, 2.6],
            index=pd.to_datetime(["2020-01-02", "2020-01-06"]),
        )
    }
    # Trading day with no backup print should still carry prior NAV.
    merged = _merge_day_prices(core, backup, pd.Timestamp("2020-01-03"))
    assert "050025" in merged.index
    assert float(merged["050025"]) == 2.5


def test_portfolio_nav_does_not_gap_when_backup_nav_missing():
    dates = pd.bdate_range("2020-01-02", periods=10)
    prices = pd.DataFrame(
        {
            "110020": [1.0] * 10,
            "161125": [2.0] * 10,
            "003358": [1.0] * 10,
            "000216": [1.0] * 10,
            "006874": [1.0] * 10,
        },
        index=dates,
    )
    # Backup publishes only on first and last day; mid days must ffill.
    backup = {
        "050025": pd.Series([3.0, 3.1], index=[dates[0], dates[-1]]),
        "006075": pd.Series([4.0, 4.1], index=[dates[0], dates[-1]]),
    }
    config = StrategyConfig(
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
    result = simulate(prices, config, backup_prices=backup, base_capital=100_000, monthly_contribution=0.0)
    rets = result.daily_values.pct_change().dropna()
    assert float(rets.abs().max()) < 0.02
