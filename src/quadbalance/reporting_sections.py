"""Markdown section helpers for validation reporting."""

from __future__ import annotations

from quadbalance.behavior_stress import BehaviorStressResult
from quadbalance.cross_border_stress import CrossBorderStressResult
from quadbalance.path_stress import PathStressResult
from quadbalance.product_risk import ProductRiskSummary
from quadbalance.profile_thresholds import InvestorProfile
from quadbalance.simulator import LifecycleResult, SimulationResult
from quadbalance.stress import S4PathResult, StressResult
from quadbalance.long_term_stress import LongTermScenarioResult
from quadbalance.sweep import RobustnessSweepResult
from quadbalance.validation import ValidationResult


RISK_MAP_ORDER = [
    ("market", "市场价格与相关性压力"),
    ("macro", "宏观与购买力压力"),
    ("path", "路径依赖与再平衡失效"),
    ("behavior", "投资者行为与执行纪律"),
    ("cross_border", "跨境访问与结算约束"),
    ("product", "产品层实现风险"),
]


LOCK_SELECTION_KEYS = [
    "lockable over soft-pass (material needs_review without sign-off excluded)",
    "suitability rank for intended profile (suitable > caution > unsuitable) when supplied",
    "stocks sub-split risk-budget preference (60-40 over 40-60 when return edge < 50bp or extra CB reviews)",
    "higher annualized return",
    "lower absolute maximum drawdown",
    "higher QDII fill rate",
    "lexicographic configuration ID ascending",
]

# Stress IDs evaluated via closed-form / formula shocks (not full simulate paths).
FORMULA_STRESS_IDS = frozenset({
    "S1", "S2", "S3", "S6", "S8", "S9", "S10", "S11", "S12", "S13", "S14", "S15",
    "S16", "S17", "S18", "S19", "S20", "S21", "S22", "S23", "S24", "S25", "S26", "S27",
})
PATH_STRESS_IDS = frozenset({"S4", "S5", "S7"})


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
    needs_review = getattr(validation, "needs_review", None) or []
    if needs_review:
        lines.extend(["## Needs Review", ""])
        for item in needs_review:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)


def format_lifecycle_summary(lifecycle_results: list[LifecycleResult]) -> str:
    if not lifecycle_results:
        return ""
    lines = [
        "## Lifecycle Stress Tests",
        "",
        "| Scenario | Terminal Value | Real Terminal Value | Max Drawdown | Depleted | Coverage | Forced Sale | Underwater Sale | Real Spending |",
        "|----------|----------------|---------------------|--------------|----------|----------|-------------|-----------------|---------------|",
    ]
    for lr in lifecycle_results:
        lines.append(
            f"| {lr.scenario_id} | {lr.terminal_value:,.0f} | {lr.real_terminal_value:,.0f} | {lr.max_drawdown:.2%} | {'✓' if lr.depleted else '✗'} | {lr.withdrawal_coverage_ratio:.1%} | {lr.forced_sale_amount:,.0f} | {lr.underwater_forced_sale_amount:,.0f} | {lr.real_spending_preservation:.1%} |"
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


def _layer_statuses(validation: ValidationResult) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Shared severity used by Risk Overview and Risk Map."""
    metrics = validation.metrics
    stress = validation.stress_results
    path = getattr(validation, "path_stress_results", []) or []
    behavior = getattr(validation, "behavior_stress_results", []) or []
    cross_border = getattr(validation, "cross_border_stress_results", []) or []
    product = getattr(validation, "product_risk", None)

    def status(signals: list[str]) -> str:
        if not signals:
            return "green"
        if any("critical" in s or "failed" in s or "breach" in s or "frozen" in s for s in signals):
            return "red"
        return "yellow"

    market_signals: list[str] = []
    if metrics.max_drawdown <= -0.20:
        market_signals.append("critical: max drawdown exceeds 20%")
    if metrics.drawdown_20pct_events > 0:
        market_signals.append("multiple 20% drawdown episodes")
    if any(sr.scenario_id in {"S13", "S14", "S19"} and sr.classification != "normal" for sr in stress):
        market_signals.append("defensive sleeves lose hedge value")

    macro_signals: list[str] = []
    if metrics.worst_rolling_5y_real_return < 0:
        macro_signals.append("critical: negative 5-year real return")
    if metrics.pain_index > 0.05:
        macro_signals.append("persistent drawdown pain")
    if any(sr.scenario_id in {"S8", "S9", "S11", "S12", "S17"} and sr.classification != "normal" for sr in stress):
        macro_signals.append("inflation / stagnation / purchasing power stress")

    path_signals: list[str] = []
    if any(r.classification != "normal" for r in path):
        path_signals.append("rebalancing or cash conversion is blocked under stress")
    if metrics.max_drawdown_recovery_days is None or metrics.max_drawdown_recovery_days > 252:
        path_signals.append("long recovery time")

    behavior_signals: list[str] = []
    stress_fed = [r for r in behavior if getattr(r, "evaluation_mode", "historical") == "stress-fed"]
    hist = [r for r in behavior if getattr(r, "evaluation_mode", "historical") == "historical"]
    if any(r.triggered for r in behavior):
        behavior_signals.append("behavioral rules trigger in deep drawdown")
    if stress_fed and not any(r.triggered for r in hist) and any(r.triggered for r in stress_fed):
        behavior_signals.append("stress-fed behavior rules trigger despite shallow historical MDD")
    if metrics.longest_underwater_days > 252 * 2:
        behavior_signals.append("long underwater periods may challenge discipline")
    if any(getattr(r, "classification", "normal") != "normal" for r in stress_fed):
        if not behavior_signals:
            behavior_signals.append("stress-fed behavior evaluation requires review")

    cross_border_signals: list[str] = []
    if any(r.classification != "normal" for r in cross_border):
        cross_border_signals.append("critical: cross-border access or settlement constraints reduce usable value")
    if any(getattr(r, "frozen_asset_weight", 0) > 0 for r in cross_border):
        cross_border_signals.append("frozen external-linked weight is non-zero")

    product_signals: list[str] = []
    if product is not None:
        product_signals.append(f"weighted product risk score {product.weighted_score:.1f}")
        if product.worst_classification != "normal":
            product_signals.append(f"worst sleeve {product.worst_classification}")

    signals = {
        "market": market_signals,
        "macro": macro_signals,
        "path": path_signals,
        "behavior": behavior_signals,
        "cross_border": cross_border_signals,
        "product": product_signals,
    }
    statuses = {key: status(vals) for key, vals in signals.items()}
    return statuses, signals


def format_risk_overview_panel(validation: ValidationResult) -> str:
    metrics = validation.metrics
    path = getattr(validation, "path_stress_results", []) or []
    behavior = getattr(validation, "behavior_stress_results", []) or []
    cross_border = getattr(validation, "cross_border_stress_results", []) or []
    product = getattr(validation, "product_risk", None)
    layers, _ = _layer_statuses(validation)

    def line(status: str, text: str) -> str:
        return f"{status}|{text}"

    rows = [
        line(layers["market"], f"市场：max drawdown {metrics.max_drawdown:.2%}，{metrics.drawdown_20pct_events} 次深回撤"),
        line(layers["macro"], f"宏观：5y real return {metrics.worst_rolling_5y_real_return:.2%}，pain {metrics.pain_index:.2%}"),
        line(layers["path"], f"路径：{len(path)} 个场景"),
        line(layers["behavior"], f"行为：{len(behavior)} 条规则"),
        line(layers["cross_border"], f"跨境：{len(cross_border)} 个场景"),
        line(layers["product"], f"产品：风险分数 {product.weighted_score:.1f}" if product is not None else "产品：未评估"),
    ]
    red = [r.split("|", 1)[1] for r in rows if r.startswith("red|")]
    yellow = [r.split("|", 1)[1] for r in rows if r.startswith("yellow|")]
    green = [r.split("|", 1)[1] for r in rows if r.startswith("green|")]
    top_risks = red[:3]
    lines = ["## Risk Overview Panel", "", f"- Red items: {len(red)}", f"- Yellow items: {len(yellow)}", f"- Green items: {len(green)}", "", "### Top 3 Risks"]
    lines.extend([f"- {item}" for item in top_risks] or ["- —"])
    lines.extend(["", "### Red"])
    lines.extend([f"- {item}" for item in red] or ["- —"])
    lines.extend(["", "### Yellow"])
    lines.extend([f"- {item}" for item in yellow] or ["- —"])
    lines.extend(["", "### Green"])
    lines.extend([f"- {item}" for item in green] or ["- —"])
    lines.append("")
    return "\n".join(lines)


def format_risk_summary_page(validation: ValidationResult) -> str:
    layers, _ = _layer_statuses(validation)
    red_layers = [name for name, key in [
        ("市场价格与相关性压力", "market"),
        ("宏观与购买力压力", "macro"),
        ("路径依赖与再平衡失效", "path"),
        ("投资者行为与执行纪律", "behavior"),
        ("跨境访问与结算约束", "cross_border"),
        ("产品层实现风险", "product"),
    ] if layers.get(key) == "red"]
    yellow_count = sum(1 for k in ("market", "macro", "path", "behavior", "cross_border", "product") if layers.get(k) == "yellow")
    green_count = sum(1 for k in ("market", "macro", "path", "behavior", "cross_border", "product") if layers.get(k) == "green")

    if red_layers:
        core = "；".join(red_layers[:3])
    else:
        core = "当前未见明确红色风险"

    material = getattr(validation, "material_needs_review", None) or material_from_validation(validation)
    lines = [
        "## One-Page Risk Summary",
        "",
        f"- 核心结论：{core}",
        f"- 总体风险数：红 {len(red_layers)} / 黄 {yellow_count} / 绿 {green_count}",
        f"- Lockable：{'是' if getattr(validation, 'lockable', False) else '否'}",
        "",
        "### 需要优先处理",
    ]
    priority = material[:5] if material else []
    lines.extend([f"- {item}" for item in priority] or ["- —"])
    lines.extend(["", "### 其次关注"])
    secondary = [item for item in (getattr(validation, "needs_review", None) or []) if item not in priority][:5]
    lines.extend([f"- {item}" for item in secondary] or ["- —"])
    lines.append("")
    return "\n".join(lines)


def material_from_validation(validation: ValidationResult) -> list[str]:
    from quadbalance.lock_integrity import material_needs_review

    return material_needs_review(list(getattr(validation, "needs_review", None) or []))


def format_uncovered_risk_summary(validation: ValidationResult) -> str:
    metrics = validation.metrics
    path = getattr(validation, "path_stress_results", [])
    behavior = getattr(validation, "behavior_stress_results", [])
    cross_border = getattr(validation, "cross_border_stress_results", [])
    product = getattr(validation, "product_risk", None)
    items: list[str] = []
    if metrics.max_drawdown <= -0.20:
        items.append("深回撤与恢复期压力")
    if metrics.worst_rolling_5y_real_return < 0:
        items.append("真实购买力侵蚀")
    if any(r.classification != "normal" for r in path):
        items.append("路径依赖与再平衡失效")
    if any(r.triggered for r in behavior):
        items.append("行为纪律与执行风险")
    if any(r.classification != "normal" for r in cross_border):
        items.append("跨境访问与结算约束")
    if product is not None and product.weighted_score >= 40:
        items.append("产品级实现脆弱性")

    lines = ["## Uncovered Risk Summary", ""]
    if items:
        lines.extend([f"- {item}" for item in items])
    else:
        lines.append("- 当前未见新增未覆盖风险")
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
        # Key index 2 is suitability — skip when no intended profile.
        if intended_profile is None and "suitability rank" in key:
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
    lines = [
        "## Stress Test Summary",
        "",
        "| ID | Scenario | Portfolio Return | Classification | Mechanism | Threshold Basis | Liquidity Days | Notes | Reason |",
        "|----|----------|------------------|----------------|-----------|-----------------|----------------|-------|--------|",
    ]
    for sr in stress_results:
        reason = "; ".join(sr.threshold_reasons) or "—"
        notes = "; ".join(sr.notes) or "—"
        if sr.scenario_id in PATH_STRESS_IDS:
            mechanism = "path-simulated"
        elif sr.scenario_id in FORMULA_STRESS_IDS:
            mechanism = "formula/closed-form"
        else:
            mechanism = "mixed/unspecified"
        lines.append(
            f"| {sr.scenario_id} | {sr.scenario_name} | {sr.portfolio_return:.2%} | {sr.classification} | {mechanism} | {sr.threshold_basis} | {sr.liquidity_impairment_days} | {notes} | {reason} |"
        )
    lines.append("")
    return "\n".join(lines)


def format_risk_map_markdown(validation: ValidationResult) -> str:
    lines = [
        "## Risk Map Summary",
        "",
        "| Layer | Status | Focus | Most Vulnerable Signals |",
        "|------|--------|-------|--------------------------|",
    ]
    layers, signals = _layer_statuses(validation)
    rows = []
    for label, key in [
        ("市场价格与相关性压力", "market"),
        ("宏观与购买力压力", "macro"),
        ("路径依赖与再平衡失效", "path"),
        ("投资者行为与执行纪律", "behavior"),
        ("跨境访问与结算约束", "cross_border"),
        ("产品层实现风险", "product"),
    ]:
        rows.append((label, layers[key], "; ".join(signals[key]) or "—"))
    priority = sorted(
        rows,
        key=lambda row: {"red": 0, "yellow": 1, "green": 2}.get(row[1], 1),
    )
    lines.extend([
        "",
        "### Priority Order",
        "",
        "| Rank | Layer | Status | Suggested Action |",
        "|------|-------|--------|------------------|",
    ])
    for idx, (label, sev, _signals) in enumerate(priority, start=1):
        action = {
            "red": "Review the allocation, execution assumptions, and concentration immediately.",
            "yellow": "Monitor closely and consider adding margin or diversification.",
            "green": "No specific action beyond routine monitoring.",
        }.get(sev, "Monitor closely.")
        lines.append(f"| {idx} | {label} | {sev} | {action} |")
    lines.append("")
    return "\n".join(lines)


def format_path_stress_markdown(results: list[PathStressResult]) -> str:
    if not results:
        return ""
    lines = [
        "## Dynamic Path Stress Tests",
        "",
        "| ID | Scenario | Cumulative Return | Max Drawdown | Underwater Months | Locked Months | QDII Locked Months | Classification | Reasons |",
        "|----|----------|-------------------|--------------|-------------------|---------------|--------------------|----------------|---------|",
    ]
    for r in results:
        reasons = "; ".join(r.reasons) or "—"
        lines.append(
            f"| {r.scenario_id} | {r.name} | {r.cumulative_return:.2%} | {r.max_drawdown:.2%} | {r.longest_underwater_months} | {r.locked_months} | {r.qdii_locked_months} | {r.classification} | {reasons} |"
        )
    lines.append("")
    return "\n".join(lines)


def format_behavior_stress_markdown(results: list[BehaviorStressResult]) -> str:
    if not results:
        return ""
    lines = [
        "## Behavioral Stress Rules",
        "",
        "| Rule | Mode | Triggered | Trigger Date | Adjusted Return | Pause Months | Classification | Reasons |",
        "|------|------|-----------|--------------|-----------------|--------------|----------------|---------|",
    ]
    for r in results:
        reasons = "; ".join(r.reasons) or "—"
        mode = getattr(r, "evaluation_mode", "historical")
        lines.append(
            f"| {r.name} | {mode} | {'✓' if r.triggered else '✗'} | {r.trigger_date or '—'} | {r.adjusted_total_return:.2%} | {r.contribution_pause_months} | {r.classification} | {reasons} |"
        )
    lines.append("")
    return "\n".join(lines)


def format_cross_border_stress_markdown(results: list[CrossBorderStressResult]) -> str:
    if not results:
        return ""
    lines = [
        "## Cross-Border Access and Settlement Stress",
        "",
        "| ID | Scenario | Portfolio Return | Liquid Portfolio Return | Frozen Weight | QDII Haircut | Liquidity Months | Mobility Constraint Months | Rebalance Locked Months | Classification | Reasons |",
        "|----|----------|------------------|-------------------------|---------------|--------------|------------------|----------------------------|-------------------------|----------------|---------|",
    ]
    for r in results:
        reasons = "; ".join(r.reasons) or "—"
        lines.append(
            f"| {r.scenario_id} | {r.name} | {r.portfolio_return:.2%} | {r.liquid_portfolio_return:.2%} | {r.frozen_asset_weight:.2%} | {r.qdii_haircut:.2%} | {r.liquidity_impairment_months} | {r.capital_mobility_constraint_months} | {r.rebalance_locked_months} | {r.classification} | {reasons} |"
        )
    lines.append("")
    return "\n".join(lines)


def format_product_risk_markdown(summary: ProductRiskSummary | None) -> str:
    if summary is None:
        return ""
    lines = [
        "## Product-Level Risk",
        "",
        f"- Weighted product risk score: {summary.weighted_score:.1f}",
        f"- Worst classification: {summary.worst_classification}",
    ]
    if summary.reasons:
        lines.extend(["- Key reasons:"] + [f"  - {reason}" for reason in summary.reasons])
    lines.extend([
        "",
        "| Symbol | Name | Quadrant | Weight | Score | Classification | Reasons |",
        "|--------|------|----------|--------|-------|----------------|---------|",
    ])
    for r in summary.results:
        reasons = "; ".join(r.reasons) or "—"
        lines.append(f"| {r.symbol} | {r.name} | {r.quadrant} | {r.weight:.2%} | {r.score} | {r.classification} | {reasons} |")
    lines.append("")
    return "\n".join(lines)


def format_robustness_summary_markdown(robustness: RobustnessSweepResult | None) -> str:
    if robustness is None:
        return ""
    summary = robustness.summary
    lines = [
        "## Robustness and Valuation-Start Risk",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Verdict | {summary.verdict} |",
        f"| Pass rate | {summary.pass_rate:.0%} |",
        f"| Pass count | {summary.pass_count} |",
        f"| Fail count | {summary.fail_count} |",
        f"| Fragile dimension | {summary.fragile_dimension or '—'} |",
        "",
    ]
    if summary.worst_case is not None:
        lines.extend([
            f"- Worst case: {summary.worst_case.case_id} ({summary.worst_case.label})",
            f"- Worst-case reasons: {'; '.join(summary.worst_case.failure_reasons) or '—'}",
            "",
        ])
    if summary.reasons:
        lines.extend(["- Key reasons:"] + [f"  - {reason}" for reason in summary.reasons] + [""])
    if robustness.parameter_cases:
        lines.extend(["### Parameter Perturbations", "", "| Case | Label | Real Ann. | Real Terminal | Passed |", "|------|-------|-----------|---------------|--------|"])
        for case in robustness.cases:
            if case.kind != "parameter":
                continue
            lines.append(f"| {case.case_id} | {case.label} | {case.metrics.real_annualized_return:.2%} | {case.metrics.real_terminal_wealth:.2f}x | {'✓' if case.passed else '✗'} |")
        lines.append("")
    if robustness.valuation_cases:
        lines.extend(["### Valuation Overlays", "", "| Case | Label | Real Ann. | Real Terminal | Passed |", "|------|-------|-----------|---------------|--------|"])
        for case in robustness.cases:
            if case.kind != "overlay":
                continue
            lines.append(f"| {case.case_id} | {case.label} | {case.metrics.real_annualized_return:.2%} | {case.metrics.real_terminal_wealth:.2f}x | {'✓' if case.passed else '✗'} |")
        lines.append("")
    return "\n".join(lines)


def format_long_term_stress_markdown(results: list[LongTermScenarioResult]) -> str:
    if not results:
        return ""
    lines = ["## Long-Term Macro Regime Stress", "", "| ID | Scenario | Path Mode | Horizon | Nominal Ann. | Real Ann. | Max Drawdown | Underwater Days | 5y Real | 10y Real | Purchasing Power | 4% Withdrawal | Sequence Risk | Classification | Reasons |", "|----|----------|-----------|---------|--------------|-----------|--------------|-----------------|---------|---------|------------------|--------------|--------------|----------------|---------|"]
    for r in results:
        reasons = "; ".join(r.threshold_reasons) or "—"
        seq = "—"
        if getattr(r, "sequence_risk_results", None):
            seq = "; ".join(f"{x.get('scenario_id')}: {x.get('classification')}" for x in r.sequence_risk_results)
        path_mode = getattr(r, "path_mode", "smooth")
        lines.append(
            f"| {r.scenario_id} | {r.scenario_name} | {path_mode} | {r.horizon_years}y | {r.nominal_annualized_return:.2%} | {r.real_annualized_return:.2%} | {r.max_drawdown:.2%} | {r.longest_underwater_days} | {r.worst_rolling_5y_real_return:.2%} | {r.worst_rolling_10y_real_return:.2%} | {'✓' if r.purchasing_power_preserved else '✗'} | {'✗' if r.withdrawal_4pct_depleted else '✓'} | {seq} | {r.classification} | {reasons} |"
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
