"""Markdown section helpers for validation reporting."""

from __future__ import annotations

from quadbalance.profile_thresholds import InvestorProfile
from quadbalance.simulator import LifecycleResult, SimulationResult
from quadbalance.stress import S4PathResult, StressResult
from quadbalance.long_term_stress import LongTermScenarioResult
from quadbalance.validation import ValidationResult


LOCK_SELECTION_KEYS = [
    "suitability rank for intended profile (suitable > caution > unsuitable) when supplied",
    "higher annualized return",
    "lower absolute maximum drawdown",
    "higher QDII fill rate",
    "lexicographic configuration ID ascending",
]


def format_rebalance_execution_markdown(sim_result: SimulationResult) -> str:
    rm = sim_result.rebalance_metrics
    if rm is None:
        return ""

    lines = [
        "## Rebalance Execution",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Sell shortfall events | {rm.shortfall_event_count} |",
        f"| Total shortfall amount | {rm.total_shortfall_cny:,.0f} CNY |",
        f"| Max single shortfall | {rm.max_single_shortfall_cny:,.0f} CNY |",
        f"| Max post-rebalance deviation | {rm.max_post_rebalance_deviation:.2%} |",
        "",
    ]
    return "\n".join(lines)


def format_boundary_summary(validation: ValidationResult) -> str:
    lines = ["## Strategy Boundary Summary", "", "| Boundary | Classification |", "|----------|----------------|"]
    for key, value in validation.boundary_classifications.items():
        lines.append(f"| {key} | {value} |")
    lines.append("")
    return "\n".join(lines)


def format_lifecycle_summary(lifecycle_results: list[LifecycleResult]) -> str:
    if not lifecycle_results:
        return ""
    lines = ["## Lifecycle Stress Tests", "", "| Scenario | Terminal Value | Real Terminal Value | Max Drawdown | Depleted | Recovery Days |", "|----------|----------------|---------------------|--------------|----------|---------------|"]
    for lr in lifecycle_results:
        lines.append(
            f"| {lr.scenario_id} | {lr.terminal_value:,.0f} | {lr.real_terminal_value:,.0f} | {lr.max_drawdown:.2%} | {'✓' if lr.depleted else '✗'} | {lr.recovery_days} |"
        )
    lines.append("")
    return "\n".join(lines)


def format_recovery_time_summary(validation: ValidationResult) -> str:
    metrics = validation.metrics
    recovery = metrics.max_drawdown_recovery_days
    if recovery is None:
        value = "Unrecovered within test window"
    else:
        value = f"{recovery} trading days"
    lines = [
        "## Recovery Time Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Max drawdown recovery time | {value} |",
        f"| Hard gate | {'Pass' if recovery is not None and recovery <= 252 else 'Fail'} |",
        "",
    ]
    return "\n".join(lines)


def format_profile_suitability_summary(validation: ValidationResult) -> str:
    if not validation.profile_suitability:
        return ""
    lines = ["## Investor Profile Suitability", "", "| Profile | Classification | Key Reasons | Warnings | Governance Notes |", "|---------|----------------|-------------|----------|------------------|"]
    for profile, payload in validation.profile_suitability.items():
        reasons = "; ".join(payload.get("reasons", [])) or "—"
        warnings = "; ".join(payload.get("warnings", [])) or "—"
        notes = "; ".join(payload.get("governance_notes", [])) or "—"
        lines.append(f"| {profile} | {payload.get('classification', 'caution')} | {reasons} | {warnings} | {notes} |")
    lines.append("")
    return "\n".join(lines)


def format_lock_selection_notes(intended_profile: str | None) -> str:
    lines = [
        "## Lock Selection Ranking",
        "",
        f"- Intended profile: {intended_profile or 'none (mechanical validity only)'}",
        "- Ranking keys (in order):",
    ]
    for i, key in enumerate(LOCK_SELECTION_KEYS, start=1):
        if intended_profile is None and i == 1:
            lines.append(f"  {i}. {key} — skipped for this run")
        else:
            lines.append(f"  {i}. {key}")
    lines.append("")
    return "\n".join(lines)


def format_profile_thresholds_summary(
    investor_profiles: tuple[InvestorProfile, ...],
    overrides: dict[str, list[str]],
) -> str:
    lines = [
        "## Effective Profile Thresholds",
        "",
        "| Profile | min_real_return | max_drawdown | max_underwater_years | Overrides |",
        "|---------|-----------------|--------------|----------------------|-----------|",
    ]
    for profile in investor_profiles:
        changed = ", ".join(overrides.get(profile.profile_id, [])) or "—"
        lines.append(
            f"| {profile.profile_id} | {profile.min_real_return:.2%} | {profile.max_drawdown:.2%} | "
            f"{profile.max_underwater_years} | {changed} |"
        )
    lines.append("")
    return "\n".join(lines)


def format_stress_summary_markdown(stress_results: list[StressResult]) -> str:
    lines = ["## Stress Test Summary", "", "| ID | Scenario | Portfolio Return | Passed |", "|----|----------|------------------|--------|"]
    for sr in stress_results:
        lines.append(f"| {sr.scenario_id} | {sr.scenario_name} | {sr.portfolio_return:.2%} | {'✓' if sr.passed else '✗'} |")
    lines.append("")
    return "\n".join(lines)


def format_long_term_stress_markdown(results: list[LongTermScenarioResult]) -> str:
    if not results:
        return ""
    lines = ["## Long-Term Macro Regime Stress", "", "| ID | Scenario | Horizon | Nominal Ann. | Real Ann. | Max Drawdown | Underwater Days | 5y Real | 10y Real | Purchasing Power | 4% Withdrawal | Classification | Reasons |", "|----|----------|---------|--------------|-----------|--------------|-----------------|---------|---------|------------------|--------------|----------------|---------|"]
    for r in results:
        reasons = "; ".join(r.threshold_reasons) or "—"
        lines.append(
            f"| {r.scenario_id} | {r.scenario_name} | {r.horizon_years}y | {r.nominal_annualized_return:.2%} | {r.real_annualized_return:.2%} | {r.max_drawdown:.2%} | {r.longest_underwater_days} | {r.worst_rolling_5y_real_return:.2%} | {r.worst_rolling_10y_real_return:.2%} | {'✓' if r.purchasing_power_preserved else '✗'} | {'✗' if r.withdrawal_4pct_depleted else '✓'} | {r.classification} | {reasons} |"
        )
    lines.append("")
    return "\n".join(lines)


def format_s4_path_markdown(s4: S4PathResult) -> str:
    years_str = ", ".join(str(y) for y in s4.window_years)
    lines = [
        "## S4 Five-Year Path",
        "",
        f"Shock window: {years_str}",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| 5-year cumulative return | {s4.cumulative_return:.2%} |",
        f"| Worst single year in window | {s4.worst_year_return:.2%} |",
        f"| Window annualized return | {s4.window_annualized_return:.2%} |",
        f"| Passed (cumulative ≥ -10%) | {'✓' if s4.passed else '✗'} |",
        "",
    ]
    return "\n".join(lines)
