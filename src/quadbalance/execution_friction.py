"""Execution friction profiles used by the simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class FrictionWindow:
    start: str
    end: str
    purchase_fee_mult: float = 1.0
    redemption_fee_mult: float = 1.0
    spread_bps: float = 0.0
    premium_shock: float = 0.0
    qdii_cap_mult: float = 1.0


@dataclass(frozen=True)
class ExecutionFrictionProfile:
    windows: tuple[FrictionWindow, ...] = field(default_factory=tuple)
    name: str = "default"


def validate_friction_profile(profile: ExecutionFrictionProfile | None) -> None:
    if profile is None:
        return
    for window in profile.windows:
        if window.start > window.end:
            raise ValueError("FrictionWindow start must be <= end")


def window_for_date(profile: ExecutionFrictionProfile | None, dt: date):
    if profile is None:
        return None
    d = dt.isoformat()
    for window in profile.windows:
        if window.start <= d <= window.end:
            return window
    return None
