"""Behavioral stress rules triggered by drawdowns and underperformance."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from quadbalance.metrics import PerformanceMetrics, external_cashflows_from_events, time_weighted_daily_returns
from quadbalance.path_stress import PathStressResult
from quadbalance.simulator import SimulationResult
from quadbalance.stress import StressResult


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
    evaluation_mode: str = "historical"  # historical | stress-fed


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


def _eval_rules_against_drawdown(
    *,
    drawdown: pd.Series,
    metrics: PerformanceMetrics,
    base_terminal: float,
    base_total_return: float,
    rules: tuple[BehaviorRule, ...],
    evaluation_mode: str,
    proxy_note: str | None = None,
) -> list[BehaviorStressResult]:
    results: list[BehaviorStressResult] = []
    for rule in rules:
        breaches = drawdown[drawdown <= rule.trigger_drawdown]
        prolonged_pain = metrics.longest_underwater_days >= 252 * 3 if rule.rule_id == "BHV3" else True
        # Stress-fed BHV3: treat deep proxy MDD as prolonged-pain equivalent.
        if evaluation_mode == "stress-fed" and rule.rule_id == "BHV3":
            prolonged_pain = bool(not breaches.empty) or prolonged_pain
        triggered = bool(not breaches.empty and prolonged_pain)
        trigger_date = breaches.index[0].strftime("%Y-%m-%d") if triggered and len(breaches.index) else None
        if triggered and evaluation_mode == "stress-fed" and trigger_date is None:
            trigger_date = "stress-proxy"
        adjusted_terminal = base_terminal * (1.0 - rule.terminal_haircut) if triggered else base_terminal
        adjusted_return = (1.0 + base_total_return) * (1.0 - rule.terminal_haircut) - 1.0 if triggered else base_total_return
        classification, reasons = _classify_behavior(triggered, adjusted_return, rule.terminal_haircut)
        if proxy_note and triggered:
            reasons = [proxy_note, *reasons]
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
                evaluation_mode=evaluation_mode,
            )
        )
    return results


def _synthetic_drawdown_from_proxy(proxy_mdd: float, index: pd.DatetimeIndex) -> pd.Series:
    """Build a one-trough drawdown series reaching proxy_mdd."""
    if len(index) < 3:
        index = pd.bdate_range("2020-01-01", periods=5)
    mid = index[len(index) // 2]
    values = pd.Series(1.0, index=index)
    values.loc[mid] = 1.0 + proxy_mdd
    # Ensure trough is the min relative to a prior peak of 1.0
    return values / values.cummax() - 1.0


def stress_drawdown_proxies(
    path_results: list[PathStressResult] | None,
    stress_results: list[StressResult] | None,
) -> float | None:
    """Most severe proxy MDD from P1 and selected short-horizon stresses."""
    proxies: list[float] = []
    for pr in path_results or []:
        if pr.scenario_id == "P1" and pr.max_drawdown < 0:
            proxies.append(float(pr.max_drawdown))
    for sr in stress_results or []:
        if sr.scenario_id in {"S14", "S18"} and sr.portfolio_return < 0:
            # Treat portfolio return shock as MDD surrogate (negative).
            proxies.append(float(sr.portfolio_return))
    if not proxies:
        return None
    return min(proxies)


def run_behavior_stress_tests(
    sim_result: SimulationResult,
    metrics: PerformanceMetrics,
    rules: tuple[BehaviorRule, ...] = DEFAULT_BEHAVIOR_RULES,
    path_results: list[PathStressResult] | None = None,
    stress_results: list[StressResult] | None = None,
) -> list[BehaviorStressResult]:
    daily = sim_result.daily_values
    drawdown = _drawdown_series(daily)
    base_terminal = float(daily.iloc[-1])
    twr = time_weighted_daily_returns(daily, external_cashflows_from_events(daily, getattr(sim_result, "events", []) or []))
    base_total_return = float((1.0 + twr).prod() - 1.0) if len(twr) else float(daily.iloc[-1] / daily.iloc[0] - 1.0)

    results = _eval_rules_against_drawdown(
        drawdown=drawdown,
        metrics=metrics,
        base_terminal=base_terminal,
        base_total_return=base_total_return,
        rules=rules,
        evaluation_mode="historical",
    )

    proxy = stress_drawdown_proxies(path_results, stress_results)
    if proxy is not None:
        proxy_dd = _synthetic_drawdown_from_proxy(proxy, daily.index)
        results.extend(
            _eval_rules_against_drawdown(
                drawdown=proxy_dd,
                metrics=metrics,
                base_terminal=base_terminal,
                base_total_return=base_total_return,
                rules=rules,
                evaluation_mode="stress-fed",
                proxy_note=f"stress-fed proxy drawdown {proxy:.2%}",
            )
        )
    return results
