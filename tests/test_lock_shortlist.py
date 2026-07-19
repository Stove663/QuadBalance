"""Tests for return-seeking lock shortlist builder and artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from quadbalance.config import StrategyConfig
from quadbalance.lock_shortlist import (
    build_return_seeking_shortlist,
    shortlist_public_payload,
    write_lock_shortlist_artifacts,
)
from quadbalance.metrics import PerformanceMetrics
from quadbalance.simulator import QdiiExecutionMetrics, SimulationResult
from quadbalance.validation import ValidationResult


SHARED = [
    "Criterion 3: cross-border stress CB1 requires review",
    "Criterion 3: path stress P1 requires review",
    "Criterion 3: stress S20 requires review",
    "Criterion 3: product-level risk requires review",
]


def _metrics(annualized_return: float, max_drawdown: float = -0.08) -> PerformanceMetrics:
    return PerformanceMetrics(
        annualized_return=annualized_return,
        annualized_volatility=0.05,
        max_drawdown=max_drawdown,
        max_drawdown_peak="2026-01-01",
        max_drawdown_trough="2026-03-01",
        sharpe_ratio=1.0,
        positive_years_pct=0.8,
        rebalance_premium=0.0,
        worst_year_return=-0.02,
        annual_returns=pd.Series(dtype=float),
    )


def _soft_bundle(
    *,
    allocation_name: str,
    bond_variant: str,
    stock_sub_split: str,
    annualized_return: float,
    pending_cash_days: int,
    extra_reviews: list[str] | None = None,
) -> dict:
    config = StrategyConfig(
        allocation_name=allocation_name,
        stocks=0.30 if allocation_name.startswith("30") else 0.25,
        bonds=0.20 if allocation_name.startswith("30") else 0.25,
        gold=0.25,
        cash=0.25,
        bond_variant=bond_variant,  # type: ignore[arg-type]
        dca_method="underweight",
        rebalance_threshold=0.05,
        stock_sub_split=stock_sub_split,  # type: ignore[arg-type]
    )
    needs = list(SHARED) + list(extra_reviews or [])
    validation = ValidationResult(
        config_id=config.config_id,
        passed=True,
        failure_reasons=[],
        metrics=_metrics(annualized_return),
        benchmark_comparison={},
        stress_results=[],
        needs_review=needs,
        material_needs_review=needs,
        lockable=False,
    )
    sim = SimulationResult(
        config_id=config.config_id,
        daily_values=pd.Series([1.0, 1.1]),
        annual_quadrant_returns=pd.DataFrame(),
        effective_start="2013-08-01",
        effective_end="2026-07-01",
        instrument_starts={},
        qdii_metrics=QdiiExecutionMetrics(1.0, 0.0, 0.0, pending_cash_days, 0.0),
    )
    return {
        "validation": validation,
        "config": config,
        "sim_result": sim,
        "annualized_return": annualized_return,
        "max_drawdown": -0.08,
        "pending_cash_days": pending_cash_days,
        "config_id": config.config_id,
        "allocation_name": allocation_name,
        "stock_sub_split": stock_sub_split,
        "lockable": False,
        "material_needs_review": needs,
    }


def test_shortlist_primary_prefers_lower_pending_in_return_band():
    pool = [
        _soft_bundle(
            allocation_name="30-20-25-25",
            bond_variant="B3",
            stock_sub_split="40-60",
            annualized_return=0.1042,
            pending_cash_days=645,
        ),
        _soft_bundle(
            allocation_name="30-20-25-25",
            bond_variant="B2",
            stock_sub_split="40-60",
            annualized_return=0.1026,
            pending_cash_days=607,
        ),
        _soft_bundle(
            allocation_name="25-25-25-25",
            bond_variant="B1",
            stock_sub_split="40-60",
            annualized_return=0.0914,
            pending_cash_days=457,
        ),
    ]
    shortlist = build_return_seeking_shortlist(pool)
    roles = {r["role"]: r for r in shortlist["roles"]}
    assert "primary" in roles
    assert roles["primary"]["config_id"].endswith("B2_uw_5pct_s40-60")
    assert roles["primary"]["pending_cash_days"] == 607
    assert roles["max_return_contrast"]["config_id"].endswith("B3_uw_5pct_s40-60")
    assert roles["step_down"]["allocation_name"] == "25-25-25-25"
    assert roles["primary"]["lockable"] is False


def test_shortlist_omits_contrast_when_identical_to_primary():
    only = _soft_bundle(
        allocation_name="30-20-25-25",
        bond_variant="B1",
        stock_sub_split="40-60",
        annualized_return=0.10,
        pending_cash_days=400,
    )
    step = _soft_bundle(
        allocation_name="25-25-25-25",
        bond_variant="B1",
        stock_sub_split="40-60",
        annualized_return=0.09,
        pending_cash_days=300,
    )
    shortlist = build_return_seeking_shortlist([only, step])
    roles = {r["role"] for r in shortlist["roles"]}
    assert roles == {"primary", "step_down"}
    assert any(s["role"] == "max_return_contrast" for s in shortlist["skipped"])


def test_write_lock_shortlist_artifacts(tmp_path: Path):
    pool = [
        _soft_bundle(
            allocation_name="30-20-25-25",
            bond_variant="B2",
            stock_sub_split="40-60",
            annualized_return=0.10,
            pending_cash_days=500,
        ),
        _soft_bundle(
            allocation_name="25-25-25-25",
            bond_variant="B1",
            stock_sub_split="40-60",
            annualized_return=0.09,
            pending_cash_days=400,
        ),
    ]
    shortlist = build_return_seeking_shortlist(pool)
    json_path, md_path = write_lock_shortlist_artifacts(tmp_path, shortlist)
    assert json_path.exists()
    assert md_path.exists()
    public = shortlist_public_payload(shortlist)
    assert "bundle" not in public["roles"][0]
    assert public["roles"][0]["lockable"] is False
    text = md_path.read_text(encoding="utf-8")
    assert "does **not** make a configuration `lockable`" in text
    assert "primary" in text


def test_smoke_three_roles_from_sweep_csv_shape():
    """Dry-run shortlist roles against output/sweep_results.csv when present."""
    import csv

    csv_path = Path("output/sweep_results.csv")
    if not csv_path.exists():
        pytest.skip("no output/sweep_results.csv")

    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    soft: list[dict] = []
    for r in rows:
        if r.get("validation_passed") != "True" or r.get("lockable") == "True":
            continue
        split = r["config_id"].rsplit("_s", 1)[-1] if "_s" in r["config_id"] else "60-40"
        material = [p.strip() for p in (r.get("material_needs_review") or "").split(";") if p.strip()]
        soft.append(
            {
                "config_id": r["config_id"],
                "allocation_name": r["allocation_name"],
                "stock_sub_split": split,
                "annualized_return": float(r["annualized_return"]),
                "max_drawdown": float(r["max_drawdown"]),
                "pending_cash_days": int(float(r.get("pending_cash_days") or 0)),
                "lockable": False,
                "material_needs_review": material,
                "validation": type(
                    "V",
                    (),
                    {
                        "passed": True,
                        "lockable": False,
                        "needs_review": material,
                        "material_needs_review": material,
                        "metrics": type(
                            "M",
                            (),
                            {
                                "annualized_return": float(r["annualized_return"]),
                                "max_drawdown": float(r["max_drawdown"]),
                            },
                        )(),
                    },
                )(),
                "config": type(
                    "C",
                    (),
                    {
                        "config_id": r["config_id"],
                        "allocation_name": r["allocation_name"],
                        "stock_sub_split": split,
                    },
                )(),
            }
        )

    assert soft, "expected soft-pass rows in sweep CSV"
    shortlist = build_return_seeking_shortlist(soft)
    roles = {r["role"] for r in shortlist["roles"]}
    assert "primary" in roles
    assert "step_down" in roles
    assert shortlist["roles"][0]["lockable"] is False
