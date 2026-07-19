"""Regression tests for pending-cash accounting and related stress/lifecycle bugs."""

from __future__ import annotations

import pandas as pd
import pytest

from quadbalance.config import StrategyConfig
from quadbalance.long_term_stress import SCENARIOS, build_synthetic_prices
from quadbalance.simulator import (
    _SimContext,
    _handle_qdii_unfilled,
    _portfolio_value,
    simulate,
    simulate_lifecycle,
)
from quadbalance.sweep import assess_product_risk, run_behavior_stress_tests, run_path_stress_tests


def test_qdii_unfilled_is_not_double_counted_in_nav():
    shares = {"006874": 0.0, "161125": 0.0}
    prices = pd.Series({"006874": 1.0, "161125": 2.0})
    ctx = _SimContext()
    _handle_qdii_unfilled(shares, 1_000.0, prices, ctx, pd.Timestamp("2020-01-02"))
    # Unfilled cash is parked in the cash sleeve; backlog is a label only — do not add both.
    assert shares["006874"] == pytest.approx(1_000.0)
    assert ctx.qdii_backlog == pytest.approx(1_000.0)
    assert _portfolio_value(shares, prices) == pytest.approx(1_000.0)
    assert _portfolio_value(shares, prices, ctx.qdii_backlog) == pytest.approx(2_000.0)  # wrong if used for NAV


def test_simulate_nav_not_inflated_by_pending_backlog():
    dates = pd.bdate_range("2020-01-02", periods=3)
    prices = pd.DataFrame(
        {
            "110020": [1.0] * 3,
            "161125": [2.0] * 3,
            "003358": [1.0] * 3,
            "000216": [1.0] * 3,
            "006874": [1.0] * 3,
        },
        index=dates,
    )
    backup = {
        "050025": pd.Series([2.0] * 3, index=dates),
        "006075": pd.Series([2.0] * 3, index=dates),
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
    result = simulate(prices, config, backup_prices=backup, base_capital=100_000.0, monthly_contribution=0.0)
    assert result.pending_cash_series.iloc[0] == pytest.approx(9_700.0)
    # After fees, NAV should stay near 100k — not ~110k from double-counting pending.
    assert result.daily_values.iloc[0] == pytest.approx(100_000.0, rel=0.02)


def test_sweep_helpers_are_not_noops():
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
    path = run_path_stress_tests(config)
    assert len(path) >= 1
    assert path[0].scenario_id.startswith("P")

    dates = pd.bdate_range("2020-01-02", periods=30)
    prices = pd.DataFrame(
        {s: [1.0 + 0.001 * i for i in range(30)] for s in ["110020", "161125", "003358", "000216", "006874"]},
        index=dates,
    )
    sim = simulate(prices, config, base_capital=10_000.0, monthly_contribution=0.0)
    from quadbalance.metrics import compute_metrics

    metrics = compute_metrics(sim, config, prices, risk_free_annual=0.02)
    behavior = run_behavior_stress_tests(sim, metrics)
    assert len(behavior) >= 1

    product = assess_product_risk(config)
    assert product is not None
    assert product.weighted_score > 0


def test_long_term_synthetic_maps_fund_codes_to_quadrants():
    idx = pd.bdate_range("2020-01-02", periods=5)
    prices = pd.DataFrame(
        {"110020": 1.0, "161125": 1.0, "003358": 1.0, "000216": 1.0, "006874": 1.0},
        index=idx,
    )
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
    # Single-phase scenario for clear CAGR separation.
    from quadbalance.long_term_stress import LongTermPhase, LongTermScenario

    scenario = LongTermScenario(
        "T",
        "test",
        2,
        (LongTermPhase(2, -0.10, 0.05, 0.08, 0.02, 0.03, "phase"),),
    )
    syn = build_synthetic_prices(prices, scenario, config=config)
    years = len(syn) / 252

    def cagr(col: str) -> float:
        return float(syn[col].iloc[-1] ** (1 / years) - 1)

    assert cagr("110020") == pytest.approx(-0.10, abs=0.005)
    assert cagr("003358") == pytest.approx(0.05, abs=0.005)
    assert cagr("000216") == pytest.approx(0.08, abs=0.005)
    assert cagr("006874") == pytest.approx(0.02, abs=0.005)


def test_lifecycle_interruption_keeps_holdings_instead_of_zeroing():
    dates = pd.bdate_range("2020-01-02", periods=80)
    n = len(dates)
    prices = pd.DataFrame(
        {
            "110020": [1.0 * (1.0002**i) for i in range(n)],
            "161125": [1.0 * (1.0002**i) for i in range(n)],
            "003358": [1.0] * n,
            "000216": [1.0] * n,
            "006874": [1.0] * n,
        },
        index=dates,
    )
    config = StrategyConfig(
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
    interrupted = simulate_lifecycle(prices, config, "dca_interrupt", interrupt_months=2)
    # Must remain invested — not wiped to zero during pause months.
    assert not interrupted.depleted
    assert interrupted.terminal_value > 1_000.0
    assert interrupted.contribution_missed > 0
    assert any(e.event_type == "contribution_pause" for e in interrupted.events)
