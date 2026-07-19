"""Regression tests for portfolio validation hard-flaw fixes."""

from __future__ import annotations

import pandas as pd
import pytest

from quadbalance.asset_universe import QDII_BACKUP_SYMBOLS
from quadbalance.behavior_stress import run_behavior_stress_tests
from quadbalance.config import StrategyConfig
from quadbalance.fees import SHORT_HOLD_DAYS, redemption_fee_rate, short_hold_redemption_rate
from quadbalance.lock_integrity import HumanSignOff, compute_lockable, qdii_quality_reviews
from quadbalance.lock_selection import prefer_lock_candidate
from quadbalance.long_term_stress import LongTermScenarioResult
from quadbalance.metrics import PerformanceMetrics
from quadbalance.path_stress import PathStressResult
from quadbalance.simulator import SimulationResult, _SimContext, _buy, _sell, _settle_prior_day
from quadbalance.sweep import collect_required_symbols
from quadbalance.validation import ValidationResult, apply_long_term_lock_vetoes


def _config(**kwargs) -> StrategyConfig:
    base = dict(
        allocation_name="25-25-25-25",
        stocks=0.25,
        bonds=0.25,
        gold=0.25,
        cash=0.25,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
    )
    base.update(kwargs)
    return StrategyConfig(**base)


def _metrics(**overrides) -> PerformanceMetrics:
    data = dict(
        annualized_return=0.10,
        annualized_volatility=0.12,
        max_drawdown=-0.08,
        max_drawdown_peak="2020-01-01",
        max_drawdown_trough="2020-03-01",
        sharpe_ratio=0.8,
        positive_years_pct=0.8,
        rebalance_premium=0.01,
        worst_year_return=-0.08,
        annual_returns=pd.Series(dtype=float),
        max_drawdown_recovery_days=40,
        real_annualized_return=0.07,
        real_terminal_wealth=1.2,
        worst_rolling_3y_real_return=0.02,
        worst_rolling_5y_real_return=0.01,
        longest_underwater_days=80,
    )
    data.update(overrides)
    return PerformanceMetrics(**data)


def test_collect_required_symbols_excludes_qdii_backups():
    configs = [_config(enable_qdii_quota=True)]
    symbols = collect_required_symbols(configs)
    for sym in QDII_BACKUP_SYMBOLS:
        assert sym not in symbols


def test_alignment_rejects_backup_contamination():
    from quadbalance.data import load_price_matrix_with_meta

    with pytest.raises(ValueError, match="QDII backups"):
        load_price_matrix_with_meta(symbols=["110020", "006075"], use_cache=True)


def test_price_matrix_effective_start_not_2018():
    from quadbalance.data import load_price_matrix_with_meta

    prices, _ = load_price_matrix_with_meta(use_cache=True)
    assert prices.index[0] <= pd.Timestamp("2013-08-01")
    assert prices.index[0].strftime("%Y-%m-%d") != "2018-06-08"


def test_qdii_quality_reviews_pending_and_gap():
    reviews = qdii_quality_reviews(
        pending_cash_days=300,
        qdii_friction_months=14,
        avg_qdii_weight_gap=-0.03,
        max_post_rebalance_deviation=0.08,
        rebalance_threshold=0.05,
    )
    assert any("pending-cash" in r for r in reviews)
    assert any("weight gap" in r for r in reviews)
    assert any("post-rebalance" in r for r in reviews)


def test_lockable_requires_sign_off_for_material_reviews():
    needs = ["Criterion 3: cross-border stress CB1 requires review"]
    assert compute_lockable(True, needs, None) is False
    sign = HumanSignOff("alice", "accepted CB friction", tuple(needs))
    assert compute_lockable(True, needs, sign) is True


def test_prefer_lockable_and_stock_split_risk_budget():
    soft = {
        "annualized_return": 0.09,
        "max_drawdown": -0.10,
        "qdii_fill_rate": 1.0,
        "config_id": "a_40-60",
        "lockable": False,
        "stock_sub_split": "40-60",
        "material_cb_reviews": 2,
    }
    lockable_60 = {
        "annualized_return": 0.088,
        "max_drawdown": -0.10,
        "qdii_fill_rate": 1.0,
        "config_id": "b_60-40",
        "lockable": True,
        "stock_sub_split": "60-40",
        "material_cb_reviews": 0,
    }
    chosen = prefer_lock_candidate(soft, lockable_60)
    assert chosen["config_id"] == "b_60-40"

    a = {
        "annualized_return": 0.080,
        "max_drawdown": -0.10,
        "qdii_fill_rate": 1.0,
        "config_id": "c_40-60",
        "lockable": True,
        "stock_sub_split": "40-60",
        "material_cb_reviews": 1,
    }
    b = {
        "annualized_return": 0.083,
        "max_drawdown": -0.10,
        "qdii_fill_rate": 1.0,
        "config_id": "d_60-40",
        "lockable": True,
        "stock_sub_split": "60-40",
        "material_cb_reviews": 0,
    }
    chosen2 = prefer_lock_candidate(a, b)
    assert chosen2["stock_sub_split"] == "60-40"


def test_seq_inflation_veto_via_apply():
    lt = LongTermScenarioResult(
        "LT1",
        "stagflation",
        10,
        "smooth",
        0.02,
        -0.01,
        0.95,
        -0.05,
        -0.05,
        10,
        10,
        None,
        -0.02,
        0.0,
        -0.01,
        -0.02,
        0,
        purchasing_power_preserved=False,
        classification="normal",
        threshold_reasons=[],
        withdrawal_4pct_depleted=False,
        withdrawal_4pct_terminal_wealth=1.0,
        sequence_risk_results=[{"scenario_id": "seq_inflation", "classification": "thesis-broken", "reasons": []}],
    )
    validation = ValidationResult(
        "cfg",
        True,
        [],
        _metrics(),
        {},
        [],
        lockable=True,
    )
    validation.long_term_results = [lt]
    apply_long_term_lock_vetoes(validation)
    assert validation.lockable is False
    assert any("seq_inflation" in item for item in validation.needs_review)
    assert validation.long_term_results[0].classification == "review-required"


def test_behavior_stress_fed_triggers_on_proxy():
    idx = pd.bdate_range("2020-01-01", periods=60)
    values = pd.Series([1.0 + 0.001 * i for i in range(60)], index=idx)
    sim = SimulationResult(
        "cfg",
        values,
        pd.DataFrame(),
        "2020-01-01",
        "2020-03-01",
        {},
    )
    metrics = _metrics(max_drawdown=-0.05, longest_underwater_days=10)
    path = [
        PathStressResult(
            "P1",
            "cascade",
            -0.12,
            -0.22,
            12,
            3,
            1,
            "review-required",
            [],
        )
    ]
    results = run_behavior_stress_tests(sim, metrics, path_results=path, stress_results=[])
    hist = [r for r in results if r.evaluation_mode == "historical"]
    fed = [r for r in results if r.evaluation_mode == "stress-fed"]
    assert hist and not any(r.triggered for r in hist)
    assert fed and any(r.triggered for r in fed)


def test_short_hold_redemption_and_seasoned():
    assert redemption_fee_rate("110020") > 0
    assert redemption_fee_rate("006874") == 0.0
    assert short_hold_redemption_rate("110020", 3) > 0
    assert short_hold_redemption_rate("110020", SHORT_HOLD_DAYS) == 0.0


def test_t1_buy_not_sellable_same_day():
    shares: dict[str, float] = {}
    ctx = _SimContext()
    dt0 = pd.Timestamp("2020-01-02")
    _buy(shares, "110020", 10_000.0, 1.0, ctx=ctx, dt=dt0)
    assert shares.get("110020", 0.0) == 0.0
    assert ctx.pending_settle_shares["110020"] > 0
    shortfall = _sell(shares, "110020", 5_000.0, 1.0, ctx=ctx, dt=dt0)
    assert shortfall == pytest.approx(5_000.0)

    prices = pd.Series({"110020": 1.0, "006874": 1.0})
    dt1 = pd.Timestamp("2020-01-03")
    _settle_prior_day(shares, ctx, prices)
    assert shares["110020"] > 0
    shortfall2 = _sell(shares, "110020", 1_000.0, 1.0, ctx=ctx, dt=dt1)
    assert shortfall2 < 1_000.0
    assert ctx.unsettled_cash > 0
