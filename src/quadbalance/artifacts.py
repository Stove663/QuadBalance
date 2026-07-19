"""Stable intermediate JSON artifact writers for Phase 1 runs."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

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


def _drawdown_series(daily_values: pd.Series) -> pd.Series:
    cummax = daily_values.cummax()
    return daily_values / cummax - 1.0


def write_equity_curve_artifact(artifacts_dir: Path, config_id: str, daily_values: pd.Series) -> Path:
    """Write equity/NAV and drawdown series for GUI charts."""
    dd = _drawdown_series(daily_values)
    dates = [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d) for d in daily_values.index]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "config_id": config_id,
        "dates": dates,
        "equity": [float(v) for v in daily_values.values],
        "drawdown": [float(v) for v in dd.values],
    }
    path = artifacts_dir / "equity_curve.json"
    _write_json(path, payload)
    return path


def write_stress_summary_artifact(artifacts_dir: Path, config_id: str, validation: ValidationResult) -> Path | None:
    """Compact stress summary for table / traffic-light UI."""
    scenarios: list[dict[str, Any]] = []
    for sr in validation.stress_results or []:
        scenarios.append(
            {
                "id": getattr(sr, "scenario_id", ""),
                "kind": "stress",
                "classification": getattr(sr, "classification", ""),
                "passed": bool(getattr(sr, "passed", False)),
                "max_drawdown": getattr(sr, "max_drawdown", None),
            }
        )
    for pr in getattr(validation, "path_stress_results", None) or []:
        scenarios.append(
            {
                "id": getattr(pr, "scenario_id", ""),
                "kind": "path",
                "classification": getattr(pr, "classification", ""),
                "passed": getattr(pr, "classification", "") not in {"fail", "thesis-broken"},
            }
        )
    for br in getattr(validation, "behavior_stress_results", None) or []:
        scenarios.append(
            {
                "id": getattr(br, "rule_id", getattr(br, "scenario_id", "")),
                "kind": "behavior",
                "classification": getattr(br, "classification", ""),
                "passed": getattr(br, "classification", "") not in {"fail", "thesis-broken"},
            }
        )
    for cr in getattr(validation, "cross_border_stress_results", None) or []:
        scenarios.append(
            {
                "id": getattr(cr, "scenario_id", ""),
                "kind": "cross_border",
                "classification": getattr(cr, "classification", ""),
                "passed": getattr(cr, "classification", "") not in {"fail", "thesis-broken"},
            }
        )
    for lt in validation.long_term_results or []:
        scenarios.append(
            {
                "id": getattr(lt, "scenario_id", ""),
                "kind": "long_term",
                "classification": getattr(lt, "classification", ""),
                "passed": getattr(lt, "classification", "") not in {"fail", "thesis-broken"},
                "max_drawdown": getattr(lt, "max_drawdown", None),
                "real_max_drawdown": getattr(lt, "real_max_drawdown", None),
            }
        )
    if not scenarios and not validation.needs_review:
        return None
    payload = {
        "schema_version": SCHEMA_VERSION,
        "config_id": config_id,
        "needs_review": list(validation.needs_review or []),
        "scenarios": scenarios,
    }
    path = artifacts_dir / "stress_summary.json"
    _write_json(path, payload)
    return path


def write_run_artifacts(
    output_dir: Path,
    config: StrategyConfig,
    sim_result: SimulationResult,
    validation: ValidationResult,
    investor_profiles: tuple[InvestorProfile, ...],
    lifecycle_results: list[LifecycleResult] | None = None,
) -> Path:
    """Emit artifacts bundle including equity_curve for GUI charts."""
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
        "instrument_weights": config.instrument_weights(),
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
        "validation_passed": validation.passed,
        "lockable": getattr(validation, "lockable", False),
        "needs_review": list(getattr(validation, "needs_review", None) or []),
        "material_needs_review": list(getattr(validation, "material_needs_review", None) or []),
        "sign_off": (
            validation.sign_off.to_dict()
            if getattr(validation, "sign_off", None) is not None
            else None
        ),
        "cpi_assumption_annual": 0.03,
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
    write_equity_curve_artifact(artifacts_dir, config.config_id, sim_result.daily_values)
    write_stress_summary_artifact(artifacts_dir, config.config_id, validation)
    return artifacts_dir
