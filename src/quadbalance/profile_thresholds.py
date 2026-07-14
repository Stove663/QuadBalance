"""Default investor profile thresholds and labels."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any

NUMERIC_OVERRIDE_FIELDS = frozenset(
    {
        "horizon_years",
        "min_real_return",
        "max_drawdown",
        "max_underwater_years",
        "qdii_friction_limit_months",
        "qdii_recovery_limit_months",
    }
)


@dataclass(frozen=True)
class InvestorProfile:
    profile_id: str
    horizon_years: int
    contribution_pattern: str
    withdrawal_pattern: str
    behavioral_tolerance: str
    min_real_return: float
    max_drawdown: float
    max_underwater_years: int
    qdii_friction_limit_months: int = 12
    qdii_recovery_limit_months: int = 24


DEFAULT_INVESTOR_PROFILES: tuple[InvestorProfile, ...] = (
    InvestorProfile("accumulation", 10, "stable_dca", "none", "higher", 0.02, -0.25, 5),
    InvestorProfile("balanced_core", 7, "stable_dca", "occasional", "moderate", 0.01, -0.25, 5),
    InvestorProfile("pre_retirement_preservation", 5, "declining_dca", "rare", "lower", 0.0, -0.30, 3),
    InvestorProfile("retirement_withdrawal", 0, "none", "recurring_withdrawal", "low", 0.0, -0.30, 5),
)

PROFILE_THRESHOLD_MAP: dict[str, InvestorProfile] = {
    profile.profile_id: profile for profile in DEFAULT_INVESTOR_PROFILES
}

KNOWN_PROFILE_IDS = frozenset(PROFILE_THRESHOLD_MAP)
KNOWN_PROFILE_FIELD_NAMES = frozenset(f.name for f in fields(InvestorProfile))


def profile_to_dict(profile: InvestorProfile) -> dict[str, Any]:
    return asdict(profile)


def merge_profile_overrides(
    overrides: dict[str, dict[str, Any]],
    base: tuple[InvestorProfile, ...] = DEFAULT_INVESTOR_PROFILES,
) -> tuple[InvestorProfile, ...]:
    """Deep-merge numeric threshold overrides by profile_id onto built-in defaults."""
    if not overrides:
        return base

    unknown_ids = set(overrides) - KNOWN_PROFILE_IDS
    if unknown_ids:
        raise ValueError(f"Unknown investor profile id(s): {sorted(unknown_ids)}")

    merged: list[InvestorProfile] = []
    for profile in base:
        patch = overrides.get(profile.profile_id)
        if not patch:
            merged.append(profile)
            continue
        unknown_fields = set(patch) - KNOWN_PROFILE_FIELD_NAMES
        if unknown_fields:
            raise ValueError(
                f"Unknown threshold field(s) for {profile.profile_id}: {sorted(unknown_fields)}"
            )
        kwargs = {k: v for k, v in patch.items() if k != "profile_id"}
        merged.append(replace(profile, **kwargs))
    return tuple(merged)


def load_profile_thresholds(path: Path | None) -> tuple[InvestorProfile, ...]:
    """Load JSON overrides and merge onto defaults. None path returns defaults."""
    if path is None:
        return DEFAULT_INVESTOR_PROFILES
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Profile threshold file must be a JSON object keyed by profile_id")
    normalized: dict[str, dict[str, Any]] = {}
    for profile_id, patch in raw.items():
        if not isinstance(patch, dict):
            raise ValueError(f"Override for {profile_id} must be an object")
        normalized[profile_id] = patch
    return merge_profile_overrides(normalized)


def overridden_fields(
    effective: tuple[InvestorProfile, ...],
    base: tuple[InvestorProfile, ...] = DEFAULT_INVESTOR_PROFILES,
) -> dict[str, list[str]]:
    """Return profile_id -> list of fields that differ from base defaults."""
    base_map = {p.profile_id: p for p in base}
    result: dict[str, list[str]] = {}
    for profile in effective:
        baseline = base_map.get(profile.profile_id)
        if baseline is None:
            continue
        changed = [
            name
            for name in NUMERIC_OVERRIDE_FIELDS
            if getattr(profile, name) != getattr(baseline, name)
        ]
        if changed:
            result[profile.profile_id] = changed
    return result
