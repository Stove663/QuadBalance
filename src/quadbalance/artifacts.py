"""Stable intermediate JSON artifact writers for Phase 1 runs."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from quadbalance.config import StrategyConfig
from quadbalance.profile_thresholds import (
    InvestorProfile,
    overridden_fields,
    profile_to_dict,
)
from quadbalance.simulator import LifecycleResult, SimulationEvent, SimulationResult
from quadbalance.validation import ValidationResult

SCHEMA_VERSION = 1


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _event_to_dict(event: SimulationEvent) -> dict[str, Any]:
    return asdict(event)


def write_run_artifacts(
    output_dir: Path,
    config: StrategyConfig,
    sim_result: SimulationResult,
    validation: ValidationResult,
    investor_profiles: tuple[InvestorProfile, ...],
    lifecycle_results: list[LifecycleResult] | None = None,
) -> Path:
    """Emit artifacts/config.json, events.json, metrics.json, suitability.json."""
    artifacts_dir = output_dir / "artifacts"
    overrides = overridden_fields(investor_profiles)
    effective = {p.profile_id: profile_to_dict(p) for p in investor_profiles}

    config_payload = {
        "schema_version": SCHEMA_VERSION,
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
        "effective_profile_thresholds": effective,
        "overridden_profile_fields": overrides,
    }
    _write_json(artifacts_dir / "config.json", config_payload)

    events: list[dict[str, Any]] = [_event_to_dict(e) for e in sim_result.events]
    for lr in lifecycle_results or validation.lifecycle_results:
        events.extend(_event_to_dict(e) for e in lr.events)
    events.sort(key=lambda e: (e.get("date") or "", e.get("event_type") or ""))
    _write_json(
        artifacts_dir / "events.json",
        {"schema_version": SCHEMA_VERSION, "config_id": config.config_id, "events": events},
    )

    m = validation.metrics
    qm = sim_result.qdii_metrics
    rm = sim_result.rebalance_metrics
    metrics_payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "config_id": config.config_id,
        "annualized_return": m.annualized_return,
        "annualized_volatility": m.annualized_volatility,
        "max_drawdown": m.max_drawdown,
        "sharpe_ratio": m.sharpe_ratio,
        "positive_years_pct": m.positive_years_pct,
        "rebalance_premium": m.rebalance_premium,
        "real_annualized_return": m.real_annualized_return,
        "real_terminal_wealth": m.real_terminal_wealth,
        "worst_rolling_3y_real_return": m.worst_rolling_3y_real_return,
        "longest_underwater_days": m.longest_underwater_days,
        "qdii": asdict(qm) if qm is not None else None,
        "rebalance": asdict(rm) if rm is not None else None,
        "lifecycle": [
            {
                "scenario_id": lr.scenario_id,
                "terminal_value": lr.terminal_value,
                "real_terminal_value": lr.real_terminal_value,
                "max_drawdown": lr.max_drawdown,
                "depleted": lr.depleted,
                "recovery_days": lr.recovery_days,
            }
            for lr in (lifecycle_results or validation.lifecycle_results)
        ],
    }
    _write_json(artifacts_dir / "metrics.json", metrics_payload)

    suitability_payload = {
        "schema_version": SCHEMA_VERSION,
        "config_id": config.config_id,
        "profiles": {
            profile_id: {
                "classification": payload.get("classification", "caution"),
                "reasons": list(payload.get("reasons", [])),
                "effective_thresholds": effective.get(profile_id, {}),
            }
            for profile_id, payload in validation.profile_suitability.items()
        },
    }
    _write_json(artifacts_dir / "suitability.json", suitability_payload)
    return artifacts_dir
