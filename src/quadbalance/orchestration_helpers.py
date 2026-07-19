"""Shared orchestration helpers for sweep and single-run flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quadbalance.metrics import PerformanceMetrics, classify_suitability
from quadbalance.product_risk import assess_product_risk as _assess_product_risk
from quadbalance.profile_thresholds import DEFAULT_INVESTOR_PROFILES


def load_profile_thresholds(profile_thresholds_path: Path | None):
    return DEFAULT_INVESTOR_PROFILES


def assess_product_risk(*args, **kwargs):
    return _assess_product_risk(*args, **kwargs)


def build_profile_suitability(config: Any, metrics: PerformanceMetrics, sim_result: Any, profile_thresholds_path: Path | None):
    investor_profiles = load_profile_thresholds(profile_thresholds_path)
    suitability = classify_suitability(
        config=config,
        metrics=metrics,
        qdii_fill_rate=getattr(sim_result.qdii_metrics, "qdii_fill_rate", 1.0),
        avg_qdii_weight_gap=getattr(sim_result.qdii_metrics, "avg_qdii_weight_gap", 0.0),
        qdii_friction_months=getattr(sim_result.qdii_metrics, "qdii_friction_months", 0),
        qdii_recovery_months=getattr(sim_result.qdii_metrics, "qdii_recovery_months", 0),
        investor_profiles=investor_profiles,
        sequence_risk={},
    )
    return {
        profile_id: {
            "classification": item.classification,
            "reasons": item.reasons,
            "drivers": item.drivers,
            "warnings": item.warnings,
            "governance_notes": item.governance_notes,
        }
        for profile_id, item in suitability.items()
    }
