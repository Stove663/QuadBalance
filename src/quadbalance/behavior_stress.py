"""Behavioral stress rules triggered by drawdowns and underperformance."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from quadbalance.metrics import PerformanceMetrics
from quadbalance.simulator import SimulationResult


@dataclass(frozen=True)
class BehaviorRule:
    rule_id: str
    name: str
    trigger_drawdown: float
    terminal_haircut: float
    contribution_pause_months: int = 0
    risk_reduction: float = 0.0


@dataclass
class BehaviorStressResult:
    rule_id: str
    name: str
    triggered: bool
    trigger_date: str | None
    adjusted_terminal_wealth: float
    adjusted_total_return: float
    contribution_pause_months: int
    classification: str
    reasons: list[str] = field(default_factory=list)


DEFAULT_BEHAVIOR_RULES: tuple[BehaviorRule, ...] = (
    BehaviorRule("BHV1", "Pause contributions after 20% drawdown", -0.20, 0.04, contribution_pause_months=12),
    BehaviorRule("BHV2", "Cut risk after 30% drawdown", -0.30, 0.12, risk_reduction=0.5),
    BehaviorRule("BHV3", "Strategy abandonment after prolonged pain", -0.25, 0.18, contribution_pause_months=24, risk_reduction=1.0),
)


def _drawdown_series(daily_values: pd.Series) -> pd.Series:
    return daily_values / daily_values.cummax() - 1.0


def _classify_behavior(triggered: bool, adjusted_total_return: float, haircut: float) -> tuple[str, list[str]]:
    if not triggered:
        return "normal", []
    reasons = ["behavior rule is triggered by historical/stressed drawdown"]
    if adjusted_total_return < -0.20 or haircut >= 0.15:
        reasons.append("behavioral response materially impairs terminal wealth")
        return "thesis-broken", reasons
    return "review-required", reasons


def run_behavior_stress_tests(
    sim_result: SimulationResult,
    metrics: PerformanceMetrics,
    rules: tuple[BehaviorRule, ...] = DEFAULT_BEHAVIOR_RULES,
) -> list[BehaviorStressResult]:
    daily = sim_result.daily_values
    drawdown = _drawdown_series(daily)
    base_terminal = float(daily.iloc[-1])
    base_total_return = float(daily.iloc[-1] / daily.iloc[0] - 1.0)
    results: list[BehaviorStressResult] = []
    for rule in rules:
        breaches = drawdown[drawdown <= rule.trigger_drawdown]
        prolonged_pain = metrics.longest_underwater_days >= 252 * 3 if rule.rule_id == "BHV3" else True
        triggered = bool(not breaches.empty and prolonged_pain)
        trigger_date = breaches.index[0].strftime("%Y-%m-%d") if triggered else None
        adjusted_terminal = base_terminal * (1.0 - rule.terminal_haircut) if triggered else base_terminal
        adjusted_return = base_total_return - rule.terminal_haircut if triggered else base_total_return
        classification, reasons = _classify_behavior(triggered, adjusted_return, rule.terminal_haircut)
        results.append(
            BehaviorStressResult(
                rule.rule_id,
                rule.name,
                triggered,
                trigger_date,
                adjusted_terminal,
                adjusted_return,
                rule.contribution_pause_months if triggered else 0,
                classification,
                reasons,
            )
        )
    return results
