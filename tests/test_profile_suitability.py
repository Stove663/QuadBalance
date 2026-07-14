"""Tests for investor profile suitability summaries."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from quadbalance.cli import main as cli_main
from quadbalance.config import StrategyConfig
from quadbalance.metrics import classify_suitability, compute_metrics
from quadbalance.reporting_sections import format_profile_suitability_summary, format_stress_summary_markdown
from quadbalance.simulator import simulate
from quadbalance.stress import run_stress_tests
from quadbalance.reporting import generate_lock_document
from quadbalance.validation import ValidationResult, evaluate_acceptance


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
            "110020": [1.5 * (1.0003 ** i) for i in range(n)],
            "161125": [2.0 * (1.0002 ** i) for i in range(n)],
            "003358": [1.0 * (1.0001 ** i) for i in range(n)],
            "000216": [1.2 * (1.00015 ** i) for i in range(n)],
            "006874": [1.0 * (1.00005 ** i) for i in range(n)],
        },
        index=dates,
    )


def _validation() -> tuple[StrategyConfig, pd.DataFrame, ValidationResult]:
    config = _config()
    prices = _prices()
    sim = simulate(prices, config)
    no_rebal = simulate(prices, config, enable_rebalance=False)
    metrics = compute_metrics(sim, config, prices, 0.02, no_rebal)
    stress, _ = run_stress_tests(config, sim, prices)
    validation = evaluate_acceptance(config, metrics, {"cash": metrics, "60_40": metrics}, stress)
    validation.profile_suitability = {
        p: {"classification": s.classification, "reasons": s.reasons}
        for p, s in classify_suitability(config, metrics, 1.0, 0.0).items()
    }
    return config, prices, validation


def test_classify_suitability_produces_default_profiles():
    config = _config()
    prices = _prices()
    sim = simulate(prices, config)
    no_rebal = simulate(prices, config, enable_rebalance=False)
    metrics = compute_metrics(sim, config, prices, 0.02, no_rebal)
    suitability = classify_suitability(config, metrics, 1.0, 0.0)

    assert set(suitability) == {
        "accumulation",
        "balanced_core",
        "pre_retirement_preservation",
        "retirement_withdrawal",
    }
    for item in suitability.values():
        assert item.reasons is not None
        assert item.drivers is not None
        assert item.warnings is not None
        assert item.governance_notes is not None


def test_classify_suitability_includes_governance_notes_for_qdii_friction():
    config = _config()
    prices = _prices()
    sim = simulate(prices, config)
    no_rebal = simulate(prices, config, enable_rebalance=False)
    metrics = compute_metrics(sim, config, prices, 0.02, no_rebal)
    suitability = classify_suitability(config, metrics, 0.6, -0.05, qdii_friction_months=12, qdii_recovery_months=24)

    assert any(suitability["accumulation"].warnings)
    assert suitability["accumulation"].governance_notes


def test_stress_scenarios_include_recession_and_stagflation():
    _, _, validation = _validation()
    stress_text = format_stress_summary_markdown(validation.stress_results)

    assert "A-share crash" in stress_text
    assert "Stock-bond dual kill" in stress_text


def test_profile_suitability_summary_includes_all_profiles():
    _, _, validation = _validation()
    text = format_profile_suitability_summary(validation)

    assert "## Investor Profile Suitability" in text
    assert "accumulation" in text
    assert "balanced_core" in text
    assert "pre_retirement_preservation" in text
    assert "retirement_withdrawal" in text


def test_lock_document_includes_profile_suitability(tmp_path: Path):
    config, _, validation = _validation()
    prices = _prices()
    sim = simulate(prices, config)
    _, s4_path = run_stress_tests(config, sim, prices)

    output = tmp_path / "strategy-lock.md"
    generate_lock_document(config, sim, validation, output, s4_path=s4_path)

    text = output.read_text(encoding="utf-8")
    assert "## Investor Profile Suitability" in text
    assert "Warnings" in text
    assert "Governance Notes" in text
    assert "accumulation" in text
    assert "balanced_core" in text
    assert "pre_retirement_preservation" in text
    assert "retirement_withdrawal" in text


def test_cli_accepts_intended_profile_argument(monkeypatch):
    captured = {}

    def fake_run_sweep(**kwargs):
        captured.update(kwargs)
        df = pd.DataFrame({"validation_passed": [True], "annualized_return": [0.1], "max_drawdown": [-0.1], "config_id": ["x"]})
        return df, None, None

    monkeypatch.setattr("quadbalance.cli.run_sweep", fake_run_sweep)
    monkeypatch.setattr("sys.argv", ["quadbalance", "--intended-profile", "accumulation"])
    cli_main()

    assert captured["intended_profile"] == "accumulation"
