"""Stress classification thresholds."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StressThreshold:
    metric_type: str
    review: float
    fail: float

    def classify(self, value: float) -> tuple[str, list[str]]:
        if value < self.fail:
            return "thesis-broken", [f"{self.metric_type} {value:.2%} below fail floor {self.fail:.2%}"]
        if value < self.review:
            return "review-required", [f"{self.metric_type} {value:.2%} below review floor {self.review:.2%}"]
        return "normal", []


DEFAULT_STRESS_THRESHOLDS: dict[str, StressThreshold] = {
    "S1": StressThreshold("portfolio_return", -0.15, -0.25),
    "S2": StressThreshold("portfolio_return", -0.12, -0.20),
    "S3": StressThreshold("portfolio_return", -0.05, -0.12),
    "S4": StressThreshold("cumulative_return", -0.05, -0.10),
    "S5": StressThreshold("impact_vs_baseline", -0.03, -0.10),
    "S6": StressThreshold("portfolio_return", -0.08, -0.15),
    "S7": StressThreshold("impact_vs_baseline", -0.03, -0.08),
    "S8": StressThreshold("portfolio_return", -0.12, -0.20),
    "S9": StressThreshold("portfolio_return", -0.15, -0.25),
    "S10": StressThreshold("portfolio_return", -0.05, -0.12),
    "S11": StressThreshold("portfolio_return", -0.10, -0.18),
    "S12": StressThreshold("portfolio_return", -0.05, -0.12),
    "S13": StressThreshold("portfolio_return", -0.10, -0.15),
    "S14": StressThreshold("portfolio_return", -0.15, -0.25),
    "S15": StressThreshold("portfolio_return", -0.12, -0.20),
    "S16": StressThreshold("portfolio_return", -0.10, -0.18),
    "S17": StressThreshold("real_return_proxy", -0.06, -0.12),
    "S18": StressThreshold("portfolio_return", -0.18, -0.30),
    "S19": StressThreshold("portfolio_return", -0.10, -0.18),
    "S20": StressThreshold("real_liquidity_return", -0.05, -0.10),
    "S21": StressThreshold("behavioral_return", -0.18, -0.30),
}
