"""Dynamic path-dependent stress tests."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from quadbalance.config import StrategyConfig


@dataclass(frozen=True)
class PathStressPhase:
    name: str
    months: int
    quadrant_returns: dict[str, float]
    rebalance_locked: bool = False
    qdii_locked: bool = False
    contribution_multiplier: float = 1.0


@dataclass(frozen=True)
class PathStressScenario:
    scenario_id: str
    name: str
    phases: tuple[PathStressPhase, ...]


@dataclass
class PathStressResult:
    scenario_id: str
    name: str
    cumulative_return: float
    max_drawdown: float
    longest_underwater_months: int
    locked_months: int
    qdii_locked_months: int
    classification: str
    reasons: list[str] = field(default_factory=list)


PATH_STRESS_SCENARIOS: tuple[PathStressScenario, ...] = (
    PathStressScenario(
        "P1",
        "Cascading crisis with failed rebalancing",
        (
            PathStressPhase("equity crash", 3, {"stocks": -0.25, "bonds": 0.00, "gold": 0.03, "cash": 0.002}),
            PathStressPhase("locked rebound", 3, {"stocks": 0.08, "bonds": -0.03, "gold": -0.04, "cash": 0.002}, rebalance_locked=True, qdii_locked=True),
            PathStressPhase("second leg down", 6, {"stocks": -0.22, "bonds": -0.08, "gold": -0.10, "cash": 0.002}, rebalance_locked=True),
            PathStressPhase("slow recovery", 12, {"stocks": 0.12, "bonds": 0.02, "gold": 0.01, "cash": 0.01}),
        ),
    ),
    PathStressScenario(
        "P2",
        "Inflation grind with cash drag",
        (
            PathStressPhase("rate shock", 6, {"stocks": -0.10, "bonds": -0.09, "gold": -0.05, "cash": -0.02}),
            PathStressPhase("policy lag", 12, {"stocks": 0.02, "bonds": -0.05, "gold": 0.02, "cash": -0.04}),
            PathStressPhase("real erosion", 18, {"stocks": 0.06, "bonds": 0.00, "gold": 0.03, "cash": -0.06}),
        ),
    ),
    PathStressScenario(
        "P3",
        "QDII whipsaw and quota lock",
        (
            PathStressPhase("overseas drawdown", 4, {"stocks": -0.18, "bonds": 0.01, "gold": 0.02, "cash": 0.002}, qdii_locked=True),
            PathStressPhase("fx reversal", 5, {"stocks": -0.08, "bonds": 0.00, "gold": -0.03, "cash": 0.002}, qdii_locked=True, rebalance_locked=True),
            PathStressPhase("quota recovery", 9, {"stocks": 0.10, "bonds": 0.01, "gold": 0.00, "cash": 0.005}),
        ),
    ),
)


def _portfolio_phase_return(config: StrategyConfig, phase: PathStressPhase) -> float:
    weighted = sum(config.quadrant_weights[q] * phase.quadrant_returns.get(q, 0.0) for q in config.quadrant_weights)
    lock_drag = 0.0
    if phase.rebalance_locked:
        lock_drag += 0.01
    if phase.qdii_locked:
        lock_drag += config.qdii_target_weight() * 0.04
    contribution_drag = max(0.0, 1.0 - phase.contribution_multiplier) * 0.01
    return weighted - lock_drag - contribution_drag


def _classify_path(cumulative: float, max_drawdown: float, locked_months: int) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if cumulative < -0.25 or max_drawdown < -0.30:
        reasons.append("path stress breaches thesis-broken loss floor")
        return "thesis-broken", reasons
    if cumulative < -0.12 or max_drawdown < -0.20 or locked_months >= 6:
        reasons.append("path stress requires governance review")
        return "review-required", reasons
    return "normal", reasons


def run_path_stress_tests(config: StrategyConfig, scenarios: tuple[PathStressScenario, ...] = PATH_STRESS_SCENARIOS) -> list[PathStressResult]:
    results: list[PathStressResult] = []
    for scenario in scenarios:
        monthly = [1.0]
        locked_months = 0
        qdii_locked_months = 0
        for phase in scenario.phases:
            phase_return = _portfolio_phase_return(config, phase)
            monthly_return = (1.0 + phase_return) ** (1.0 / max(phase.months, 1)) - 1.0 if phase_return > -1 else -1.0
            for _ in range(phase.months):
                monthly.append(monthly[-1] * (1.0 + monthly_return))
            if phase.rebalance_locked:
                locked_months += phase.months
            if phase.qdii_locked:
                qdii_locked_months += phase.months
        series = pd.Series(monthly)
        drawdown = series / series.cummax() - 1.0
        underwater = series < series.cummax()
        longest = current = 0
        for flag in underwater:
            if flag:
                current += 1
                longest = max(longest, current)
            else:
                current = 0
        cumulative = float(series.iloc[-1] / series.iloc[0] - 1.0)
        max_drawdown = float(drawdown.min())
        classification, reasons = _classify_path(cumulative, max_drawdown, locked_months)
        results.append(
            PathStressResult(
                scenario.scenario_id,
                scenario.name,
                cumulative,
                max_drawdown,
                longest,
                locked_months,
                qdii_locked_months,
                classification,
                reasons,
            )
        )
    return results
