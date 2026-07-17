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
    "S13": ("Persistent correlation/liquidity stress", {"stocks": -0.18, "bonds": -0.10, "gold": -0.06, "cash": 0.0}),
    "S14": ("Quad hedge failure", {"stocks": -0.35, "bonds": -0.15, "gold": -0.20, "cash": -0.02}),
    "S15": ("Rebalance lockout", {"stocks": -0.28, "bonds": -0.08, "gold": -0.12, "cash": 0.0}),
    "S16": ("QDII FX/premium/quota triple shock", {"stocks": -0.22, "bonds": 0.0, "gold": -0.03, "cash": 0.0}),
    "S17": ("Silent inflation confiscation", {"stocks": -0.04, "bonds": -0.06, "gold": -0.03, "cash": -0.08}),
    "S18": ("Front-loaded crash after deployment", {"stocks": -0.45, "bonds": -0.10, "gold": -0.08, "cash": 0.0}),
    "S19": ("Bond fund redemption spiral", {"stocks": -0.10, "bonds": -0.14, "gold": -0.03, "cash": -0.01}),
    "S20": ("Cash liquidity and inflation erosion", {"stocks": -0.08, "bonds": -0.04, "gold": 0.0, "cash": -0.06}),
    "S21": ("Behavioral capitulation", {"stocks": -0.32, "bonds": -0.07, "gold": -0.10, "cash": 0.0}),
}
