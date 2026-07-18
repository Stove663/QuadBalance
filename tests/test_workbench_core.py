"""Tests for lock registry, ledger, guidance, paths, and equity artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from quadbalance.artifacts import SCHEMA_VERSION, write_run_artifacts
from quadbalance.config import StrategyConfig
from quadbalance.ledger import LedgerError, add_entry, reconstruct, soft_delete_entry
from quadbalance.lock_registry import activate_lock, get_active_lock, list_locks
from quadbalance.metrics import classify_suitability, compute_metrics
from quadbalance.paths import allocate_run_dir
from quadbalance.profile_thresholds import DEFAULT_INVESTOR_PROFILES
from quadbalance.rebalance_guidance import compute_guidance, material_idle_cash
from quadbalance.simulator import simulate
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


def test_allocate_run_dir_unique(tmp_path: Path):
    a = allocate_run_dir(tmp_path)
    b = allocate_run_dir(tmp_path)
    assert a != b
    assert a.is_dir() and b.is_dir()


def test_equity_curve_artifact_written(tmp_path: Path):
    config = _config()
    prices = _prices()
    sim = simulate(prices, config)
    metrics = compute_metrics(sim, config, prices, 0.02)
    stress, _ = run_stress_tests(config, sim, prices)
    validation = evaluate_acceptance(config, metrics, {"cash": metrics, "60_40": metrics}, stress)
    suitability = classify_suitability(config, metrics, 1.0, 0.0)
    validation.profile_suitability = {
        k: {"classification": v.classification, "reasons": v.reasons} for k, v in suitability.items()
    }
    artifacts_dir = write_run_artifacts(tmp_path, config, sim, validation, DEFAULT_INVESTOR_PROFILES)
    eq = json.loads((artifacts_dir / "equity_curve.json").read_text(encoding="utf-8"))
    assert eq["schema_version"] == SCHEMA_VERSION
    assert len(eq["dates"]) == len(eq["equity"]) == len(eq["drawdown"])
    assert len(eq["equity"]) > 10


def test_lock_registry_relock_and_reject_failed(tmp_path: Path):
    db = tmp_path / "t.db"
    config_a = _config(allocation_name="25-25-25-25")
    config_b = _config(allocation_name="20-30-25-25", stocks=0.2, bonds=0.3)
    lock_a = activate_lock(config=config_a, run_dir=tmp_path / "run_a", validation_passed=True, db_path=db)
    assert get_active_lock(db).config_id == lock_a.config_id
    lock_b = activate_lock(config=config_b, run_dir=tmp_path / "run_b", validation_passed=True, db_path=db)
    assert get_active_lock(db).config_id == lock_b.config_id
    locks = list_locks(db)
    assert len(locks) == 2
    assert sum(1 for L in locks if L.is_active) == 1
    assert any(not L.is_active and L.config_id == lock_a.config_id for L in locks)
    with pytest.raises(ValueError):
        activate_lock(config=config_a, run_dir=tmp_path / "x", validation_passed=False, db_path=db)


def test_ledger_opening_buy_sell_guards(tmp_path: Path):
    db = tmp_path / "l.db"
    add_entry(entry_date="2024-01-01", entry_type="opening", symbol="110020", shares=1000, enforce_guards=False, db_path=db)
    add_entry(entry_date="2024-01-01", entry_type="opening", amount=5000, enforce_guards=False, db_path=db)
    state = reconstruct(db)
    assert state.shares["110020"] == 1000
    assert state.settlement_cash == 5000
    add_entry(entry_date="2024-01-02", entry_type="buy", symbol="000216", amount=1000, shares=100, db_path=db)
    state = reconstruct(db)
    assert state.settlement_cash == 4000
    assert state.shares["000216"] == 100
    with pytest.raises(LedgerError):
        add_entry(entry_date="2024-01-03", entry_type="sell", symbol="110020", shares=2000, amount=1, db_path=db)
    with pytest.raises(LedgerError):
        add_entry(entry_date="2024-01-03", entry_type="buy", symbol="000216", amount=99999, shares=1, db_path=db)
    e = add_entry(entry_date="2024-01-04", entry_type="sell", symbol="110020", shares=200, amount=300, db_path=db)
    soft_delete_entry(e.id, db_path=db)
    state = reconstruct(db)
    assert state.shares["110020"] == 1000


def test_corporate_action_idempotent(tmp_path: Path):
    db = tmp_path / "c.db"
    add_entry(entry_date="2024-01-01", entry_type="opening", symbol="110020", shares=100, enforce_guards=False, db_path=db)
    from quadbalance.ledger import add_entry as _add

    _add(
        entry_date="2024-06-01",
        entry_type="corporate_action",
        symbol="110020",
        shares=100,
        amount=0,
        action_kind="split",
        effective_date="2024-06-01",
        source="system",
        enforce_guards=False,
        db_path=db,
    )
    from quadbalance.ledger import find_corporate_action

    assert find_corporate_action(symbol="110020", action_kind="split", effective_date="2024-06-01", db_path=db)
    # second insert blocked by find — simulate sync skip
    existing = find_corporate_action(symbol="110020", action_kind="split", effective_date="2024-06-01", db_path=db)
    assert existing is not None
    state = reconstruct(db)
    assert state.shares["110020"] == 200


def test_guidance_threshold_and_idle_cash():
    from quadbalance.lock_registry import StrategyLock

    snap = {
        "quadrant_weights": {"stocks": 0.25, "bonds": 0.25, "gold": 0.25, "cash": 0.25},
        "instrument_weights": {
            "110020": 0.15,
            "161125": 0.10,
            "003358": 0.25,
            "000216": 0.25,
            "006874": 0.25,
        },
        "rebalance_threshold": 0.05,
        "config": {},
    }
    lock = StrategyLock(1, "t", "id", "/tmp", None, snap, True, True)
    # Balanced within threshold, tiny cash
    prices = {"110020": 1, "161125": 1, "003358": 1, "000216": 1, "006874": 1}
    shares = {"110020": 15, "161125": 10, "003358": 25, "000216": 25, "006874": 25}
    g = compute_guidance(lock=lock, shares=shares, settlement_cash=10, prices=prices)
    assert g.alert is False
    assert material_idle_cash(10, 100) is False
    # Material idle cash, underweight cash sleeve
    shares2 = {"110020": 25, "161125": 15, "003358": 25, "000216": 25, "006874": 5}
    g2 = compute_guidance(lock=lock, shares=shares2, settlement_cash=5000, prices=prices)
    assert g2.alert is True
    assert any(L.symbol == "006874" and L.side == "buy" for L in g2.legs)
    # Large stock overweight
    shares3 = {"110020": 50, "161125": 30, "003358": 5, "000216": 5, "006874": 5}
    g3 = compute_guidance(lock=lock, shares=shares3, settlement_cash=0, prices=prices)
    assert g3.alert is True
    assert any(L.side == "sell" for L in g3.legs)
