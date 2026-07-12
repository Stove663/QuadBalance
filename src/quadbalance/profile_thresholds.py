"""Default investor profile thresholds and labels."""

from __future__ import annotations

from dataclasses import dataclass


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
