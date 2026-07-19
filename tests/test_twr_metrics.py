"""Time-weighted return metrics must strip DCA cashflows."""

from __future__ import annotations

import pandas as pd
import pytest

from quadbalance.asset_universe import BASE_CAPITAL, MONTHLY_CONTRIBUTION
from quadbalance.benchmarks import run_benchmarks
from quadbalance.config import StrategyConfig
from quadbalance.metrics import compute_metrics, time_weighted_daily_returns
from quadbalance.simulator import simulate


@pytest.fixture
def rising_prices() -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-02", periods=520)
    n = len(dates)
    # Mild equity drift, flat bond/gold/cash → portfolio TWR should stay mid-single-digit.
    return pd.DataFrame(
        {
            "110020": [1.0 * (1.0003**i) for i in range(n)],
            "161125": [1.0 * (1.0003**i) for i in range(n)],
            "003358": [1.0] * n,
            "000216": [1.0] * n,
            "006874": [1.0] * n,
        },
        index=dates,
    )


def _config() -> StrategyConfig:
    return StrategyConfig(
        allocation_name="20-30-20-30",
        stocks=0.20,
        bonds=0.30,
        gold=0.20,
        cash=0.30,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
        stock_sub_split="40-60",
        enable_qdii_quota=False,
    )


def test_dca_annualized_return_uses_twr_not_terminal_over_initial(rising_prices: pd.DataFrame):
    config = _config()
    result = simulate(rising_prices, config)
    metrics = compute_metrics(result, config, rising_prices, risk_free_annual=0.02)

    years = len(result.daily_values) / 252
    bogus = (result.daily_values.iloc[-1] / result.daily_values.iloc[0]) ** (1 / years) - 1

    assert bogus > 0.10  # Vn/V0 is inflated by monthly contributions
    assert metrics.annualized_return == pytest.approx(
        _manual_twr_cagr(result),
        abs=1e-9,
    )
    assert metrics.annualized_return < bogus - 0.03
    assert metrics.annualized_return < 0.10


def test_twr_daily_returns_strip_contribution_jumps():
    idx = pd.bdate_range("2020-01-02", periods=5)
    # Flat prices: 100 -> 100; on day 2 add 50 so value becomes 150 with 0% market return.
    values = pd.Series([100.0, 100.0, 150.0, 150.0, 150.0], index=idx)
    cashflows = pd.Series([100.0, 0.0, 50.0, 0.0, 0.0], index=idx)
    rets = time_weighted_daily_returns(values, cashflows)
    assert rets.iloc[0] == pytest.approx(0.0)
    assert rets.iloc[1] == pytest.approx(0.0)  # (150-50)/100 - 1
    assert float((1 + rets).prod() - 1) == pytest.approx(0.0)


def test_benchmarks_use_twr_compatible_annualized_return(rising_prices: pd.DataFrame):
    benches = run_benchmarks(rising_prices)
    cash = benches["cash"]
    years = len(cash.daily_values) / 252
    bogus = (cash.daily_values.iloc[-1] / cash.daily_values.iloc[0]) ** (1 / years) - 1
    # Cash NAV is nearly flat; TWR should be ~0, not contribution-inflated.
    assert cash.annualized_return < 0.02
    assert cash.annualized_return < bogus - 0.05


def _manual_twr_cagr(result) -> float:
    daily = result.daily_values
    cf = pd.Series(0.0, index=daily.index)
    for event in result.events:
        if event.event_type in {"base_position", "contribution"} and event.cash_amount:
            dt = pd.Timestamp(event.date)
            if dt in cf.index:
                cf.loc[dt] += float(event.cash_amount)
    rets = time_weighted_daily_returns(daily, cf)
    years = len(rets) / 252
    return float((1 + rets).prod() ** (1 / years) - 1) if years > 0 else 0.0
