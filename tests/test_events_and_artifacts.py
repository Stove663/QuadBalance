"""Tests for simulation events and run artifact bundles."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from quadbalance.artifacts import SCHEMA_VERSION, write_run_artifacts
from quadbalance.config import StrategyConfig
from quadbalance.metrics import compute_metrics
from quadbalance.orchestration_helpers import build_profile_suitability
from quadbalance.profile_thresholds import DEFAULT_INVESTOR_PROFILES
from quadbalance.simulator import simulate, simulate_lifecycle
from quadbalance.stress import run_stress_tests
from quadbalance.validation import evaluate_acceptance


def _config(**kwargs) -> StrategyConfig:
    defaults = dict(
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
    defaults.update(kwargs)
    return StrategyConfig(**defaults)


def _prices(n: int = 320) -> pd.DataFrame:
    dates = pd.bdate_range("2019-01-01", periods=n)
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


def test_simulate_emits_ordered_core_events():
    config = _config()
    result = simulate(_prices(), config)
    types = [e.event_type for e in result.events]
    assert "base_position" in types
    assert "contribution" in types
    assert types[0] == "base_position"
    dates = [e.date for e in result.events]
    assert dates == sorted(dates)


def test_lifecycle_emits_withdrawal_and_liquidity_events():
    config = _config()
    prices = _prices()
    liquidity = simulate_lifecycle(prices, config, "one_time_liquidity_20pct")
    withdrawal = simulate_lifecycle(
        prices, config, "withdrawal_4pct", withdrawal_rate=0.04, withdrawal_mode="annual"
    )
    assert any(e.event_type == "liquidity" for e in liquidity.events)
    assert any(e.event_type == "withdrawal" for e in withdrawal.events)


def test_write_run_artifacts_bundle(tmp_path: Path):
    config = _config()
    prices = _prices()
    sim = simulate(prices, config)
    no_rebal = simulate(prices, config, enable_rebalance=False)
    metrics = compute_metrics(sim, config, prices, 0.02, no_rebal)
    stress, _ = run_stress_tests(config, sim, prices)
    validation = evaluate_acceptance(config, metrics, {"cash": metrics, "60_40": metrics}, stress)
    validation.profile_suitability = build_profile_suitability(config, metrics, sim, None)
    validation.lifecycle_results = [
        simulate_lifecycle(prices, config, "withdrawal_4pct", withdrawal_rate=0.04, withdrawal_mode="annual")
    ]

    artifacts_dir = write_run_artifacts(
        tmp_path, config, sim, validation, DEFAULT_INVESTOR_PROFILES, validation.lifecycle_results
    )

    manifest_path = artifacts_dir / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest["config_id"] == config.config_id
    for key in ("config", "events", "metrics", "suitability", "equity_curve"):
        assert key in manifest["artifact_paths"]

    for name in ("config.json", "events.json", "metrics.json", "suitability.json"):
        path = artifacts_dir / name
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == SCHEMA_VERSION

    suitability_payload = json.loads((artifacts_dir / "suitability.json").read_text(encoding="utf-8"))
    for profile_id, payload in validation.profile_suitability.items():
        assert suitability_payload["profiles"][profile_id]["classification"] == payload["classification"]

    config_payload = json.loads((artifacts_dir / "config.json").read_text(encoding="utf-8"))
    assert config_payload["stock_sub_split"] == config.stock_sub_split
