"""Integration: soft-pass sweep writes shortlist; pick+sign-off locks."""

from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path

import pandas as pd
import pytest

from quadbalance.config import StrategyConfig
from quadbalance.lock_integrity import compute_lockable
from quadbalance.long_term_stress import LongTermScenarioResult
from quadbalance.metrics import PerformanceMetrics
from quadbalance.simulator import QdiiExecutionMetrics, SimulationResult
from quadbalance import sweep as sweep_mod
from quadbalance.validation import ValidationResult


class _InlinePool:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def submit(self, fn, *args, **kwargs):
        fut: Future = Future()
        try:
            fut.set_result(fn(*args, **kwargs))
        except Exception as exc:  # pragma: no cover
            fut.set_exception(exc)
        return fut


def _config(name: str, bond: str = "B1", split: str = "40-60") -> StrategyConfig:
    stocks = 0.30 if name.startswith("30") else 0.25
    bonds = 0.20 if name.startswith("30") else 0.25
    return StrategyConfig(
        allocation_name=name,
        stocks=stocks,
        bonds=bonds,
        gold=0.25,
        cash=0.25,
        bond_variant=bond,  # type: ignore[arg-type]
        dca_method="underweight",
        rebalance_threshold=0.05,
        stock_sub_split=split,  # type: ignore[arg-type]
    )


def _metrics(annualized_return: float) -> PerformanceMetrics:
    return PerformanceMetrics(
        annualized_return=annualized_return,
        annualized_volatility=0.05,
        max_drawdown=-0.08,
        max_drawdown_peak="2020-01-01",
        max_drawdown_trough="2020-02-01",
        sharpe_ratio=1.0,
        positive_years_pct=1.0,
        rebalance_premium=0.0,
        worst_year_return=-0.02,
        annual_returns=pd.Series(dtype=float),
    )


def _sim(config: StrategyConfig, pending: int) -> SimulationResult:
    return SimulationResult(
        config_id=config.config_id,
        daily_values=pd.Series([1.0, 1.1], index=pd.to_datetime(["2020-01-01", "2020-01-02"])),
        annual_quadrant_returns=pd.DataFrame(
            {"stocks": [0.1], "bonds": [0.02], "gold": [0.03], "cash": [0.01]}
        ),
        effective_start="2020-01-01",
        effective_end="2020-01-02",
        instrument_starts={},
        qdii_metrics=QdiiExecutionMetrics(1.0, 0.0, 0.0, pending, 0.0),
    )


def _lt_ok(scenario_id: str = "LT1") -> LongTermScenarioResult:
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


MATERIAL = [
    "Criterion 3: cross-border stress CB1 requires review",
    "Criterion 3: path stress P1 requires review",
    "Criterion 3: stress S20 requires review",
    "Criterion 3: product-level risk requires review",
]


def test_soft_pass_sweep_writes_shortlist_without_lock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    configs = [
        _config("30-20-25-25", "B3"),
        _config("30-20-25-25", "B2"),
        _config("25-25-25-25", "B1"),
    ]
    pending = {"B3": 645, "B2": 607, "B1": 457}
    rets = {"B3": 0.1042, "B2": 0.1026, "B1": 0.0914}

    def fake_worker(payload):
        config = payload[2]
        metrics = _metrics(rets[config.bond_variant])
        validation = ValidationResult(
            config_id=config.config_id,
            passed=True,
            failure_reasons=[],
            metrics=metrics,
            benchmark_comparison={},
            stress_results=[],
            needs_review=list(MATERIAL),
            material_needs_review=list(MATERIAL),
            lockable=False,
        )
        row = {
            "config_id": config.config_id,
            "validation_stage": "deep-validated",
            "validation_passed": True,
            "lockable": False,
            "annualized_return": metrics.annualized_return,
            "material_needs_review": "; ".join(MATERIAL),
        }
        return row, validation, config, _sim(config, pending[config.bond_variant]), False

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
        "run_long_term_stress_tests",
        lambda config, prices: [_lt_ok("LT1"), _lt_ok("LT2"), _lt_ok("LT3")],
    )
    lock_calls: list[str] = []
    monkeypatch.setattr(
        sweep_mod,
        "_generate_lock_document",
        lambda config, sim, validation, path, intended_profile=None: lock_calls.append(config.config_id),
    )

    df, validation, locked = sweep_mod.run_sweep(tmp_path)

    assert locked is None
    assert validation is None
    assert lock_calls == []
    assert (tmp_path / "lock-shortlist.md").exists()
    assert (tmp_path / "lock-shortlist.json").exists()
    assert not (tmp_path / "strategy-lock.md").exists() or "locked" not in (
        (tmp_path / "strategy-lock.md").read_text(encoding="utf-8").lower()
        if (tmp_path / "strategy-lock.md").exists()
        else ""
    )
    text = (tmp_path / "lock-shortlist.md").read_text(encoding="utf-8")
    assert "primary" in text
    assert "B2_uw_5pct_s40-60" in text


def test_pick_shortlist_with_sign_off_writes_lock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    configs = [
        _config("30-20-25-25", "B3"),
        _config("30-20-25-25", "B2"),
        _config("25-25-25-25", "B1"),
    ]
    pending = {"B3": 645, "B2": 607, "B1": 457}
    rets = {"B3": 0.1042, "B2": 0.1026, "B1": 0.0914}

    def fake_worker(payload):
        config = payload[2]
        metrics = _metrics(rets[config.bond_variant])
        validation = ValidationResult(
            config_id=config.config_id,
            passed=True,
            failure_reasons=[],
            metrics=metrics,
            benchmark_comparison={},
            stress_results=[],
            needs_review=list(MATERIAL),
            material_needs_review=list(MATERIAL),
            lockable=False,
        )
        row = {
            "config_id": config.config_id,
            "validation_stage": "deep-validated",
            "validation_passed": True,
            "lockable": False,
            "annualized_return": metrics.annualized_return,
            "material_needs_review": "; ".join(MATERIAL),
        }
        return row, validation, config, _sim(config, pending[config.bond_variant]), False

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
        "run_long_term_stress_tests",
        lambda config, prices: [_lt_ok("LT1"), _lt_ok("LT2"), _lt_ok("LT3")],
    )
    monkeypatch.setattr(
        sweep_mod,
        "_generate_lock_document",
        lambda config, sim, validation, path, intended_profile=None: path.write_text(
            f"locked:{config.config_id}:lockable={validation.lockable}\n", encoding="utf-8"
        ),
    )
    monkeypatch.setattr(
        "quadbalance.artifacts.write_run_artifacts",
        lambda *a, **k: None,
    )

    pick = configs[1].config_id  # B2 primary
    df, validation, locked = sweep_mod.run_sweep(
        tmp_path,
        lock_config_id=pick,
        sign_off_reviewer="ricky",
        sign_off_rationale="accept shared CB/P1/S20/product for return preference",
    )

    assert locked is not None
    assert locked.config_id == pick
    assert validation is not None
    assert validation.lockable is True
    assert validation.sign_off is not None
    assert compute_lockable(True, list(MATERIAL), validation.sign_off)
    assert (tmp_path / "strategy-lock.md").read_text(encoding="utf-8").startswith(f"locked:{pick}")
    assert (tmp_path / "lock-shortlist.json").exists()
