"""Reusable stress scenario definitions."""

from __future__ import annotations

STRESS_SCENARIOS: dict[str, tuple[str, dict[str, float]]] = {
    "S1": ("A-share crash", {"stocks": -0.40}),
    "S2": ("Stock-bond dual kill", {"stocks": -0.20, "bonds": 0.0, "gold": 0.10, "cash": 0.02}),
    "S3": (
        "CNY depreciation",
        {"stocks": 0.048, "bonds": 0.0, "gold": 0.08, "cash": 0.0},
    ),
    "S6": ("Gold crash", {"gold": -0.20}),
    "S8": ("Stagflation", {"stocks": -0.20, "bonds": -0.08, "gold": 0.05, "cash": 0.02}),
    "S9": ("Global liquidity shock", {"stocks": -0.30, "bonds": -0.05, "gold": -0.10, "cash": 0.01}),
    "S10": ("CNY appreciation", {"stocks": 0.0, "bonds": 0.0, "gold": 0.0, "cash": 0.0}),
    "S11": ("Domestic inflation shock", {"stocks": -0.10, "bonds": -0.08, "gold": 0.05, "cash": 0.02}),
    "S12": ("Low growth stagnation", {"stocks": 0.0, "bonds": 0.0, "gold": 0.0, "cash": 0.0}),
}
