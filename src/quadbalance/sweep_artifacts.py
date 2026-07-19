"""Helpers for projecting sweep validation state into tabular outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quadbalance.sweep_constants import ARTIFACT_MANIFEST_FILENAME, ARTIFACTS_DIRNAME


def sweep_artifact_paths(artifacts_dir: Path | None) -> dict[str, str]:
    if artifacts_dir is None:
        return {}
    return {
        "artifact_manifest": str(artifacts_dir / ARTIFACT_MANIFEST_FILENAME),
        "artifact_bundle": str(artifacts_dir),
    }


def sweep_validation_projection(validation: Any, qdii: Any) -> dict[str, Any]:
    return {
        "validation_stage": "deep-validated",
        "validation_passed": validation.passed,
        "failure_reasons": "; ".join(validation.failure_reasons),
        "needs_review": "; ".join(getattr(validation, "needs_review", []) or []),
        "material_needs_review": "; ".join(getattr(validation, "material_needs_review", []) or []),
        "lockable": getattr(validation, "lockable", False),
        "qdii_pending_days_gate": "fail" if (getattr(qdii, "pending_cash_days", 0) or 0) > 252 else "pass",
        "qdii_weight_gap_gate": (
            "fail"
            if (getattr(qdii, "qdii_friction_months", 0) or 0) >= 12
            and abs(getattr(qdii, "avg_qdii_weight_gap", 0.0) or 0.0) > 0.02
            else "pass"
        ),
        "boundary_macro": validation.boundary_classifications.get("macro", ""),
        "boundary_behavioral": validation.boundary_classifications.get("behavioral", ""),
        "boundary_real_return": validation.boundary_classifications.get("real_return", ""),
        "accumulation_classification": validation.profile_suitability.get("accumulation", {}).get("classification", ""),
        "balanced_core_classification": validation.profile_suitability.get("balanced_core", {}).get("classification", ""),
        "pre_retirement_preservation_classification": validation.profile_suitability.get("pre_retirement_preservation", {}).get("classification", ""),
        "retirement_withdrawal_classification": validation.profile_suitability.get("retirement_withdrawal", {}).get("classification", ""),
        "stress_fail_count": sum(1 for s in validation.stress_results if s.classification in {"fail", "thesis-broken"}),
        "path_fail_count": sum(1 for s in getattr(validation, "path_stress_results", []) if getattr(s, "classification", "normal") in {"fail", "thesis-broken"}),
        "behavior_fail_count": sum(1 for s in getattr(validation, "behavior_stress_results", []) if getattr(s, "classification", "normal") in {"fail", "thesis-broken"}),
        "cross_border_fail_count": sum(1 for s in getattr(validation, "cross_border_stress_results", []) if getattr(s, "classification", "normal") in {"fail", "thesis-broken"}),
        "product_risk_score": getattr(getattr(validation, "product_risk", None), "weighted_score", None),
        "product_risk_classification": getattr(getattr(validation, "product_risk", None), "worst_classification", ""),
    }
