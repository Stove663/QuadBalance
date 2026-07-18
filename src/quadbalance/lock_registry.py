"""Immutable strategy lock registry (SQLite)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quadbalance.config import StrategyConfig
from quadbalance.db import connect


@dataclass(frozen=True)
class StrategyLock:
    id: int
    locked_at: str
    config_id: str
    run_dir: str
    intended_profile: str | None
    snapshot: dict[str, Any]
    is_active: bool
    validation_passed: bool


def build_lock_snapshot(
    config: StrategyConfig,
    *,
    metrics_summary: dict[str, Any] | None = None,
    suitability_summary: dict[str, Any] | None = None,
    config_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Self-contained snapshot for live targets without mutable code defaults."""
    base = config_artifact or {
        "config_id": config.config_id,
        "allocation_name": config.allocation_name,
        "stocks": config.stocks,
        "bonds": config.bonds,
        "gold": config.gold,
        "cash": config.cash,
        "bond_variant": config.bond_variant,
        "dca_method": config.dca_method,
        "rebalance_threshold": config.rebalance_threshold,
        "stock_sub_split": config.stock_sub_split,
        "enable_qdii_quota": config.enable_qdii_quota,
        "qdii_daily_caps": config.qdii_daily_caps,
        "instrument_weights": config.instrument_weights(),
    }
    return {
        "config": base,
        "quadrant_weights": {
            "stocks": config.stocks,
            "bonds": config.bonds,
            "gold": config.gold,
            "cash": config.cash,
        },
        "instrument_weights": dict(base.get("instrument_weights") or config.instrument_weights()),
        "rebalance_threshold": float(base.get("rebalance_threshold", config.rebalance_threshold)),
        "metrics": metrics_summary or {},
        "suitability": suitability_summary or {},
    }


def activate_lock(
    *,
    config: StrategyConfig,
    run_dir: Path | str,
    validation_passed: bool,
    intended_profile: str | None = None,
    snapshot: dict[str, Any] | None = None,
    metrics_summary: dict[str, Any] | None = None,
    suitability_summary: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> StrategyLock:
    if not validation_passed:
        raise ValueError("Only configurations that passed validation may be locked")
    snap = snapshot or build_lock_snapshot(
        config, metrics_summary=metrics_summary, suitability_summary=suitability_summary
    )
    locked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with connect(db_path) as conn:
        conn.execute("UPDATE strategy_locks SET is_active = 0 WHERE is_active = 1")
        cur = conn.execute(
            """
            INSERT INTO strategy_locks (
                locked_at, config_id, run_dir, intended_profile, snapshot_json, is_active, validation_passed
            ) VALUES (?, ?, ?, ?, ?, 1, 1)
            """,
            (
                locked_at,
                config.config_id,
                str(run_dir),
                intended_profile,
                json.dumps(snap, sort_keys=True),
            ),
        )
        lock_id = int(cur.lastrowid)
        conn.commit()
    return StrategyLock(
        id=lock_id,
        locked_at=locked_at,
        config_id=config.config_id,
        run_dir=str(run_dir),
        intended_profile=intended_profile,
        snapshot=snap,
        is_active=True,
        validation_passed=True,
    )


def _row_to_lock(row: Any) -> StrategyLock:
    return StrategyLock(
        id=int(row["id"]),
        locked_at=row["locked_at"],
        config_id=row["config_id"],
        run_dir=row["run_dir"],
        intended_profile=row["intended_profile"],
        snapshot=json.loads(row["snapshot_json"]),
        is_active=bool(row["is_active"]),
        validation_passed=bool(row["validation_passed"]),
    )


def get_active_lock(db_path: Path | None = None) -> StrategyLock | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM strategy_locks WHERE is_active = 1 ORDER BY id DESC LIMIT 1").fetchone()
    return _row_to_lock(row) if row else None


def list_locks(db_path: Path | None = None) -> list[StrategyLock]:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM strategy_locks ORDER BY id DESC").fetchall()
    return [_row_to_lock(r) for r in rows]
