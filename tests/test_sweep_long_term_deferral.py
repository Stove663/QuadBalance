"""Sweep orchestration: defer LT1–LT3 until lock selection."""

from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from quadbalance.config import StrategyConfig
from quadbalance.long_term_stress import LongTermScenarioResult
from quadbalance.metrics import PerformanceMetrics
from quadbalance.simulator import SimulationResult
from quadbalance import sweep as sweep_mod
from quadbalance.validation import ValidationResult


def _config(name: str = "25-25-25-25") -> StrategyConfig:
    return StrategyConfig(
        allocation_name=name,
        stocks=0.25,
        bonds=0.25,
        gold=0.25,
        cash=0.25,
        bond_variant="B1",
        dca_method="proportional",
        rebalance_threshold=0.05,
    )


def _metrics(*, annualized_return: float = 0.10, real_ann: float = 0.08, mdd: float = -0.10) -> PerformanceMetrics:
    return PerformanceMetrics(
        annualized_return=annualized_return,
        annualized_volatility=0.2,
        max_drawdown=mdd,
        max_drawdown_peak="2020-01-01",
        max_drawdown_trough="2020-02-01",
        sharpe_ratio=0.5,
        positive_years_pct=1.0,
        rebalance_premium=0.01,
        worst_year_return=-0.05,
        annual_returns=pd.Series(dtype=float),
        max_drawdown_recovery_days=21,
        real_annualized_return=real_ann,
        real_terminal_wealth=1.5,
        worst_rolling_1y_return=0.01,
        worst_rolling_3y_return=0.02,
        worst_rolling_5y_return=0.03,
        worst_rolling_1y_real_return=0.0,
        worst_rolling_3y_real_return=0.01,
        worst_rolling_5y_real_return=0.02,
        longest_underwater_days=50,
        average_drawdown=-0.03,
        ulcer_index=0.04,
        pain_index=0.02,
        cdar_95=-0.08,
        drawdown_10pct_events=1,
        drawdown_15pct_events=0,
        drawdown_20pct_events=0,
    )


def _sim(config: StrategyConfig) -> SimulationResult:
    return SimulationResult(
        config_id=config.config_id,
        daily_values=pd.Series([1.0, 1.1], index=pd.to_datetime(["2020-01-01", "2020-01-02"])),
        annual_quadrant_returns=pd.DataFrame({"stocks": [0.1], "bonds": [0.02], "gold": [0.03], "cash": [0.01]}),
        effective_start="2020-01-01",
        effective_end="2020-01-02",
        instrument_starts={},
        qdii_metrics=None,
    )


def _lt_result(scenario_id: str = "LT1") -> LongTermScenarioResult:
    return LongTermScenarioResult(
        scenario_id=scenario_id,
        scenario_name=scenario_id,
        horizon_years=10,
        path_mode="smooth",
        nominal_annualized_return=0.02,
        real_annualized_return=0.0,
        real_terminal_wealth=1.0,
        max_drawdown=-0.2,
        real_max_drawdown=-0.2,
        longest_underwater_days=100,
        real_longest_underwater_days=100,
        real_recovery_days=None,
        worst_rolling_5y_real_return=-0.05,
        worst_rolling_10y_real_return=-0.08,
        worst_1m_return=-0.05,
        worst_q_return=-0.08,
        false_recoveries=0,
        purchasing_power_preserved=True,
        classification="normal",
    )


class _InlinePool:
    """ProcessPoolExecutor stand-in that runs tasks in-process."""

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


def test_run_one_config_deep_path_skips_long_term(monkeypatch: pytest.MonkeyPatch):
    config = _config()
    prices = pd.DataFrame({"x": [1.0, 1.1]}, index=pd.to_datetime(["2020-01-01", "2020-01-02"]))
    lt_calls: list[object] = []

    monkeypatch.setattr(sweep_mod, "simulate", lambda *a, **k: _sim(config))
    monkeypatch.setattr(sweep_mod, "compute_metrics", lambda *a, **k: _metrics())
    monkeypatch.setattr(sweep_mod, "benchmark_comparison", lambda *a, **k: {})
    monkeypatch.setattr(sweep_mod, "_build_profile_suitability", lambda *a, **k: {})
    monkeypatch.setattr(sweep_mod, "run_stress_tests", lambda *a, **k: ([], None))
    monkeypatch.setattr(sweep_mod, "run_path_stress_tests", lambda *a, **k: [])
    monkeypatch.setattr(sweep_mod, "run_behavior_stress_tests", lambda *a, **k: [])
    monkeypatch.setattr(sweep_mod, "run_cross_border_stress_tests", lambda *a, **k: [])
    monkeypatch.setattr(sweep_mod, "assess_product_risk", lambda *a, **k: None)
    monkeypatch.setattr(
        sweep_mod,
        "evaluate_acceptance",
        lambda **kwargs: ValidationResult(
            config_id=config.config_id,
            passed=True,
            failure_reasons=[],
            metrics=_metrics(),
            benchmark_comparison={},
            stress_results=[],
        ),
    )
    monkeypatch.setattr(
        sweep_mod,
        "run_long_term_stress_tests",
        lambda *a, **k: lt_calls.append(a) or [_lt_result()],
    )

    row, validation, *_rest = sweep_mod._run_one_config(
        1, 1, config, prices, {}, {}, 0.02, None
    )

    assert lt_calls == []
    assert validation.long_term_results == []
    assert row["validation_stage"] == "deep-validated"


def test_run_one_config_screened_out_skips_stress_and_long_term(monkeypatch: pytest.MonkeyPatch):
    config = _config()
    prices = pd.DataFrame({"x": [1.0, 1.1]}, index=pd.to_datetime(["2020-01-01", "2020-01-02"]))
    stress_calls: list[object] = []
    lt_calls: list[object] = []

    monkeypatch.setattr(sweep_mod, "simulate", lambda *a, **k: _sim(config))
    monkeypatch.setattr(
        sweep_mod,
        "compute_metrics",
        lambda *a, **k: _metrics(real_ann=-0.01, mdd=-0.30),
    )
    monkeypatch.setattr(sweep_mod, "benchmark_comparison", lambda *a, **k: {})
    monkeypatch.setattr(sweep_mod, "_build_profile_suitability", lambda *a, **k: {})
    monkeypatch.setattr(
        sweep_mod,
        "run_stress_tests",
        lambda *a, **k: stress_calls.append(True) or ([], None),
    )
    monkeypatch.setattr(
        sweep_mod,
        "run_long_term_stress_tests",
        lambda *a, **k: lt_calls.append(True) or [],
    )

    row, validation, *_rest = sweep_mod._run_one_config(
        1, 1, config, prices, {}, {}, 0.02, None
    )

    assert stress_calls == []
    assert lt_calls == []
    assert validation.passed is False
    assert row["validation_stage"] == "screened-out"


def test_run_sweep_runs_long_term_once_for_locked_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    configs = [_config("25-25-25-25"), _config("20-30-25-25")]
    lt_config_ids: list[str] = []
    lock_calls: list[object] = []

    def fake_worker(payload):
        idx, total, config, *_rest = payload
        metrics = _metrics(annualized_return=0.12 if "25-25" in config.allocation_name else 0.09)
        validation = ValidationResult(
            config_id=config.config_id,
            passed=True,
            failure_reasons=[],
            metrics=metrics,
            benchmark_comparison={},
            stress_results=[],
            long_term_results=[],
        )
        row = {
            "config_id": config.config_id,
            "validation_stage": "deep-validated",
            "validation_passed": True,
            "annualized_return": metrics.annualized_return,
        }
        return row, validation, config, _sim(config), False

    monkeypatch.setattr(sweep_mod, "generate_sweep_configs", lambda: configs)
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
    monkeypatch.setattr(
        sweep_mod,
        "prefer_lock_candidate",
        lambda current, candidate, intended_profile=None: candidate if current is None else current,
    )

    def fake_lt(config, prices):
        lt_config_ids.append(config.config_id)
        return [_lt_result("LT1"), _lt_result("LT2"), _lt_result("LT3")]

    monkeypatch.setattr(sweep_mod, "run_long_term_stress_tests", fake_lt)
    monkeypatch.setattr(
        sweep_mod,
        "_generate_lock_document",
        lambda config, sim, validation, path, intended_profile=None: lock_calls.append(
            (config.config_id, [r.scenario_id for r in validation.long_term_results])
        ),
    )

    df, validation, locked = sweep_mod.run_sweep(tmp_path)

    assert locked is not None
    assert len(lt_config_ids) == 1
    assert lt_config_ids[0] == locked.config_id
    assert validation is not None
    assert len(validation.long_term_results) == 3
    assert lock_calls == [(locked.config_id, ["LT1", "LT2", "LT3"])]
    assert set(df["validation_stage"]) == {"deep-validated"}


def test_run_sweep_skips_long_term_when_no_lock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    config = _config()
    lt_calls: list[object] = []

    def fake_worker(payload):
        cfg = payload[2]
        metrics = _metrics()
        validation = ValidationResult(
            config_id=cfg.config_id,
            passed=False,
            failure_reasons=["fail"],
            metrics=metrics,
            benchmark_comparison={},
            stress_results=[],
        )
        row = {
            "config_id": cfg.config_id,
            "validation_stage": "deep-validated",
            "validation_passed": False,
            "annualized_return": metrics.annualized_return,
        }
        return row, validation, cfg, _sim(cfg), False

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
    monkeypatch.setattr(
        sweep_mod,
        "run_long_term_stress_tests",
        lambda *a, **k: lt_calls.append(True) or [],
    )

    df, validation, locked = sweep_mod.run_sweep(tmp_path)

    assert locked is None
    assert validation is None
    assert lt_calls == []
    assert len(df) == 1


def test_prefer_lock_candidate_ignores_long_term_results():
    """Lock ranking keys do not consult long_term_results."""
    low = {
        "annualized_return": 0.08,
        "max_drawdown": -0.10,
        "qdii_fill_rate": 1.0,
        "config_id": "low",
        "long_term_results": [_lt_result()],
        "_raw": SimpleNamespace(config_id="low"),
    }
    high = {
        "annualized_return": 0.12,
        "max_drawdown": -0.12,
        "qdii_fill_rate": 0.9,
        "config_id": "high",
        "long_term_results": [],
        "_raw": SimpleNamespace(config_id="high"),
    }
    chosen = sweep_mod.prefer_lock_candidate(low, high, intended_profile=None)
    assert chosen.config_id == "high"


def test_worker_cap_uses_cpu_with_ceiling(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    seen: list[int | None] = []

    class CapturingPool(_InlinePool):
        def __init__(self, max_workers: int | None = None):
            seen.append(max_workers)
            super().__init__(max_workers)

    monkeypatch.setattr(sweep_mod.os, "cpu_count", lambda: 16)
    monkeypatch.setattr(sweep_mod, "ProcessPoolExecutor", CapturingPool)
    monkeypatch.setattr(sweep_mod, "generate_sweep_configs", lambda: [])
    monkeypatch.setattr(sweep_mod, "collect_required_symbols", lambda _c: [])
    monkeypatch.setattr(
        sweep_mod,
        "load_market_data",
        lambda **k: (pd.DataFrame(), {}, None),
    )
    monkeypatch.setattr(sweep_mod, "run_benchmarks", lambda *a, **k: {})
    monkeypatch.setattr(sweep_mod, "cash_risk_free_rate", lambda *a, **k: 0.02)

    sweep_mod.run_sweep(tmp_path)
    assert seen == [8]
