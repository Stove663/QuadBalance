"""Markdown section helpers for validation reporting."""

from __future__ import annotations

from quadbalance.simulator import LifecycleResult, SimulationResult
from quadbalance.stress import S4PathResult, StressResult
from quadbalance.validation import ValidationResult


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


def format_profile_suitability_summary(validation: ValidationResult) -> str:
    if not validation.profile_suitability:
        return ""
    lines = ["## Investor Profile Suitability", "", "| Profile | Classification | Key Reasons |", "|---------|----------------|-------------|"]
    for profile, payload in validation.profile_suitability.items():
        reasons = "; ".join(payload.get("reasons", [])) or "—"
        lines.append(f"| {profile} | {payload.get('classification', 'caution')} | {reasons} |")
    lines.append("")
    return "\n".join(lines)


def format_stress_summary_markdown(stress_results: list[StressResult]) -> str:
    lines = ["## Stress Test Summary", "", "| ID | Scenario | Portfolio Return | Passed |", "|----|----------|------------------|--------|"]
    for sr in stress_results:
        lines.append(f"| {sr.scenario_id} | {sr.scenario_name} | {sr.portfolio_return:.2%} | {'✓' if sr.passed else '✗'} |")
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
