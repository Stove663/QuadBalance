"""Tests for investor profile threshold overrides."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from quadbalance.cli import main as cli_main
from quadbalance.config import StrategyConfig
from quadbalance.metrics import classify_suitability, compute_metrics
from quadbalance.profile_thresholds import (
    DEFAULT_INVESTOR_PROFILES,
    load_profile_thresholds,
    merge_profile_overrides,
    overridden_fields,
)
from quadbalance.simulator import simulate


def _config() -> StrategyConfig:
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


def _prices() -> pd.DataFrame:
    dates = pd.bdate_range("2019-01-01", periods=260)
    n = len(dates)
    return pd.DataFrame(
        {
            "110020": [1.5 * (1.0003**i) for i in range(n)],
            "161125": [2.0 * (1.0002**i) for i in range(n)],
            "003358": [1.0 * (1.0001**i) for i in range(n)],
            "000216": [1.2 * (1.00015**i) for i in range(n)],
            "006874": [1.0 * (1.00005**i) for i in range(n)],
        },
        index=dates,
    )


def test_merge_partial_override_keeps_defaults():
    merged = merge_profile_overrides({"accumulation": {"min_real_return": 0.05}})
    acc = next(p for p in merged if p.profile_id == "accumulation")
    base = next(p for p in DEFAULT_INVESTOR_PROFILES if p.profile_id == "accumulation")
    assert acc.min_real_return == 0.05
    assert acc.max_drawdown == base.max_drawdown
    assert overridden_fields(merged)["accumulation"] == ["min_real_return"]


def test_unknown_profile_id_fails_fast():
    with pytest.raises(ValueError, match="Unknown investor profile"):
        merge_profile_overrides({"not_a_profile": {"min_real_return": 0.01}})


def test_unknown_field_fails_fast():
    with pytest.raises(ValueError, match="Unknown threshold field"):
        merge_profile_overrides({"accumulation": {"not_a_field": 1}})


def test_load_profile_thresholds_from_json(tmp_path: Path):
    path = tmp_path / "thresholds.json"
    path.write_text(json.dumps({"balanced_core": {"max_drawdown": -0.10}}), encoding="utf-8")
    profiles = load_profile_thresholds(path)
    bal = next(p for p in profiles if p.profile_id == "balanced_core")
    assert bal.max_drawdown == -0.10


def test_stricter_drawdown_override_changes_classification():
    config = _config()
    prices = _prices()
    sim = simulate(prices, config)
    no_rebal = simulate(prices, config, enable_rebalance=False)
    metrics = compute_metrics(sim, config, prices, 0.02, no_rebal)

    baseline = classify_suitability(config, metrics, 1.0, 0.0)
    strict = merge_profile_overrides({"retirement_withdrawal": {"max_drawdown": -0.0001}})
    overridden = classify_suitability(config, metrics, 1.0, 0.0, investor_profiles=strict)

    # Synthetic upward path has shallow MDD; forcing near-zero max_drawdown should degrade retirement.
    assert overridden["retirement_withdrawal"].classification in {"caution", "unsuitable"}
    assert baseline["retirement_withdrawal"].classification in {"suitable", "caution", "unsuitable"}


def test_cli_accepts_profile_thresholds_argument(monkeypatch, tmp_path: Path):
    path = tmp_path / "t.json"
    path.write_text("{}", encoding="utf-8")
    captured = {}

    def fake_run_sweep(**kwargs):
        captured.update(kwargs)
        df = pd.DataFrame(
            {
                "validation_passed": [True],
                "annualized_return": [0.1],
                "max_drawdown": [-0.1],
                "config_id": ["x"],
            }
        )
        return df, None, None

    monkeypatch.setattr("quadbalance.cli.run_sweep", fake_run_sweep)
    monkeypatch.setattr("sys.argv", ["quadbalance", "--profile-thresholds", str(path)])
    cli_main()
    assert captured["profile_thresholds_path"] == path
