"""Regression tests for remaining metric/unit and lock-veto bugs."""

from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path

import pandas as pd
import pytest

from quadbalance.config import StrategyConfig
from quadbalance.metrics import _max_drawdown_recovery_days, compute_metrics
from quadbalance.simulator import simulate
from quadbalance.validation import ValidationResult


def test_max_drawdown_recovery_counts_trading_days_not_calendar():
    # Fri peak -> Mon trough recovery spans calendar weekend but trading-index delta is 3.
    idx = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"])
    values = pd.Series([100.0, 80.0, 90.0, 100.0], index=idx)
    assert _max_drawdown_recovery_days(values) == 3


def test_drawdown_metrics_use_twr_index_under_dca():
    dates = pd.bdate_range("2020-01-02", periods=60)
    prices = pd.DataFrame(
        {s: [1.0] * 60 for s in ["110020", "161125", "003358", "000216", "006874"]},
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
    sim = simulate(prices, config, base_capital=100_000.0, monthly_contribution=10_000.0)
    metrics = compute_metrics(sim, config, prices, risk_free_annual=0.02)
    assert metrics.max_drawdown == pytest.approx(0.0, abs=0.005)


def test_price_matrix_ffill_respects_staleness_limit(monkeypatch: pytest.MonkeyPatch):
    from quadbalance import data as data_mod

    idx = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-20", "2020-01-21"])
    series = {
        "110020": pd.Series([1.0, 1.1, 1.2, 1.3], index=idx),
        "161125": pd.Series([2.0, float("nan"), float("nan"), 2.1], index=idx),
        "003358": pd.Series([1.0, 1.0, 1.0, 1.0], index=idx),
        "000216": pd.Series([1.0, 1.0, 1.0, 1.0], index=idx),
        "006874": pd.Series([1.0, 1.0, 1.0, 1.0], index=idx),
    }

    def fake_load(symbol, use_cache=True):
        return series[symbol], None

    monkeypatch.setattr(data_mod, "load_backtest_prices", fake_load)
    monkeypatch.setattr(data_mod, "PRICE_MATRIX_SYMBOLS", tuple(series.keys()))
    prices, _meta = data_mod.load_price_matrix_with_meta(
        symbols=list(series.keys()), start="2020-01-01", use_cache=False
    )
    assert pd.Timestamp("2020-01-20") not in prices.index


class _InlinePool:
    def __init__(self, max_workers: int | None = None):
        self.max_workers = max_workers

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def submit(self, fn, *args, **kwargs):
        fut: Future = Future()
        try:
            fut.set_result(fn(*args, **kwargs))
        except Exception as exc:  # noqa: BLE001
            fut.set_exception(exc)
        return fut


def test_lock_vetoed_when_long_term_thesis_broken(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    import quadbalance.artifacts as artifacts_mod
    import quadbalance.sweep as sweep_mod
    from quadbalance.long_term_stress import LongTermScenarioResult
    from quadbalance.metrics import PerformanceMetrics
    from quadbalance.simulator import SimulationResult

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

    def fake_worker(payload):
        cfg = payload[2]
        metrics = PerformanceMetrics(
            annualized_return=0.08,
            annualized_volatility=0.1,
            max_drawdown=-0.1,
            max_drawdown_peak="2020-01-01",
            max_drawdown_trough="2020-02-01",
            sharpe_ratio=0.5,
            positive_years_pct=1.0,
            rebalance_premium=0.0,
            worst_year_return=-0.05,
            annual_returns=pd.Series(dtype=float),
            max_drawdown_recovery_days=21,
            real_annualized_return=0.05,
            real_terminal_wealth=1.1,
        )
        validation = ValidationResult(cfg.config_id, True, [], metrics, {}, [])
        sim = SimulationResult(
            config_id=cfg.config_id,
            daily_values=pd.Series([1.0, 1.1], index=pd.to_datetime(["2020-01-01", "2020-01-02"])),
            annual_quadrant_returns=pd.DataFrame(),
            effective_start="2020-01-01",
            effective_end="2020-01-02",
            instrument_starts={},
        )
        row = {
            "config_id": cfg.config_id,
            "validation_stage": "deep-validated",
            "validation_passed": True,
            "annualized_return": 0.08,
        }
        return row, validation, cfg, sim, False

    broken = LongTermScenarioResult(
        "LT1",
        "broken",
        10,
        "smooth",
        -0.05,
        -0.08,
        0.7,
        -0.25,
        -0.3,
        100,
        200,
        None,
        -0.2,
        -0.2,
        -0.1,
        -0.15,
        0,
        classification="thesis-broken",
        threshold_reasons=["broken"],
    )

    monkeypatch.setattr(sweep_mod, "generate_sweep_configs", lambda: [config])
    monkeypatch.setattr(sweep_mod, "collect_required_symbols", lambda _c: ["x"])
    monkeypatch.setattr(
        sweep_mod,
        "load_market_data",
        lambda **k: (pd.DataFrame({"x": [1.0]}, index=pd.to_datetime(["2020-01-01"])), {}, None),
    )
    monkeypatch.setattr(sweep_mod, "run_benchmarks", lambda *a, **k: {})
    monkeypatch.setattr(sweep_mod, "cash_risk_free_rate", lambda *a, **k: 0.02)
    monkeypatch.setattr(sweep_mod, "ProcessPoolExecutor", _InlinePool)
    monkeypatch.setattr(sweep_mod, "_run_one_config_payload", fake_worker)
    monkeypatch.setattr(sweep_mod, "run_long_term_stress_tests", lambda *a, **k: [broken])
    monkeypatch.setattr(
        sweep_mod,
        "_generate_lock_document",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not lock")),
    )
    monkeypatch.setattr(artifacts_mod, "write_run_artifacts", lambda *a, **k: None)

    _df, validation, locked = sweep_mod.run_sweep(tmp_path)
    assert locked is None
    assert validation is None
