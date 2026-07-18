"""Cross-border access and settlement constraint stress tests.

The scenarios use neutral descriptions and focus on portfolio mechanics: access,
settlement, liquidity, valuation haircuts, and capital mobility constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quadbalance.config import StrategyConfig


@dataclass(frozen=True)
class CrossBorderStressScenario:
    scenario_id: str
    name: str
    description: str
    domestic_stock_return: float
    qdii_return: float
    bond_return: float
    gold_return: float
    cash_real_return: float
    qdii_valuation_haircut: float
    qdii_frozen_weight_ratio: float
    liquidity_impairment_months: int
    capital_mobility_constraint_months: int
    rebalance_locked_months: int
    gold_liquidity_haircut: float = 0.0


@dataclass
class CrossBorderStressResult:
    scenario_id: str
    name: str
    portfolio_return: float
    liquid_portfolio_return: float
    frozen_asset_weight: float
    qdii_haircut: float
    liquidity_impairment_months: int
    capital_mobility_constraint_months: int
    rebalance_locked_months: int
    classification: str
    reasons: list[str] = field(default_factory=list)


CROSS_BORDER_STRESS_SCENARIOS: tuple[CrossBorderStressScenario, ...] = (
    CrossBorderStressScenario(
        "CB1",
        "Cross-border settlement friction",
        "Cross-border access remains available, but subscription, redemption, premium/discount, and settlement friction rise for several months.",
        domestic_stock_return=-0.15,
        qdii_return=-0.12,
        bond_return=0.00,
        gold_return=0.10,
        cash_real_return=-0.03,
        qdii_valuation_haircut=0.08,
        qdii_frozen_weight_ratio=0.25,
        liquidity_impairment_months=6,
        capital_mobility_constraint_months=6,
        rebalance_locked_months=3,
        gold_liquidity_haircut=0.02,
    ),
    CrossBorderStressScenario(
        "CB2",
        "Cross-border access constraint",
        "Overseas-linked fund access is constrained for an extended period and usable value diverges from reported value.",
        domestic_stock_return=-0.30,
        qdii_return=-0.25,
        bond_return=-0.03,
        gold_return=0.15,
        cash_real_return=-0.06,
        qdii_valuation_haircut=0.30,
        qdii_frozen_weight_ratio=0.70,
        liquidity_impairment_months=12,
        capital_mobility_constraint_months=12,
        rebalance_locked_months=9,
        gold_liquidity_haircut=0.05,
    ),
    CrossBorderStressScenario(
        "CB3",
        "Severe external asset availability constraint",
        "A severe cross-border constraint limits external-asset availability, redemption timing, and portfolio rebalancing for a prolonged period.",
        domestic_stock_return=-0.45,
        qdii_return=-0.35,
        bond_return=-0.08,
        gold_return=0.20,
        cash_real_return=-0.10,
        qdii_valuation_haircut=0.65,
        qdii_frozen_weight_ratio=1.00,
        liquidity_impairment_months=24,
        capital_mobility_constraint_months=24,
        rebalance_locked_months=18,
        gold_liquidity_haircut=0.10,
    ),
)


def _stock_sleeve_return(config: StrategyConfig, scenario: CrossBorderStressScenario) -> float:
    qdii_weight = config.stock_weights.get("161125", 0.0)
    domestic_weight = max(0.0, 1.0 - qdii_weight)
    stressed_qdii = scenario.qdii_return - scenario.qdii_valuation_haircut
    return domestic_weight * scenario.domestic_stock_return + qdii_weight * stressed_qdii


def _portfolio_return(config: StrategyConfig, scenario: CrossBorderStressScenario) -> float:
    stock_return = _stock_sleeve_return(config, scenario)
    gold_return = scenario.gold_return - scenario.gold_liquidity_haircut
    return (
        config.stocks * stock_return
        + config.bonds * scenario.bond_return
        + config.gold * gold_return
        + config.cash * scenario.cash_real_return
    )


def _liquid_portfolio_return(config: StrategyConfig, scenario: CrossBorderStressScenario) -> float:
    qdii_target = config.qdii_target_weight()
    frozen_weight = qdii_target * scenario.qdii_frozen_weight_ratio
    portfolio_return = _portfolio_return(config, scenario)
    unavailable_drag = frozen_weight * (scenario.qdii_return - scenario.qdii_valuation_haircut)
    liquid_base = max(1.0 - frozen_weight, 1e-9)
    return (portfolio_return - unavailable_drag) / liquid_base


def _classify(result: CrossBorderStressResult) -> CrossBorderStressResult:
    reasons: list[str] = []
    classification = "normal"
    if result.frozen_asset_weight >= 0.20:
        reasons.append("external-linked frozen weight is material")
    if result.liquidity_impairment_months >= 12:
        reasons.append("liquidity impairment persists for at least 12 months")
    if result.capital_mobility_constraint_months >= 12:
        reasons.append("capital mobility constraint persists for at least 12 months")
    # thesis-broken requires portfolio outcomes only — scenario-definition durations
    # (e.g. CB3 capital_mobility=24) must not alone force thesis-broken.
    if result.portfolio_return < -0.30 or result.frozen_asset_weight >= 0.30:
        classification = "thesis-broken"
    elif result.portfolio_return < -0.15 or result.liquidity_impairment_months >= 6 or result.frozen_asset_weight >= 0.10:
        classification = "review-required"
    if not reasons and classification != "normal":
        reasons.append("cross-border constraint materially affects portfolio usability")
    result.classification = classification
    result.reasons = reasons
    return result


def run_cross_border_stress_tests(
    config: StrategyConfig,
    scenarios: tuple[CrossBorderStressScenario, ...] = CROSS_BORDER_STRESS_SCENARIOS,
) -> list[CrossBorderStressResult]:
    results: list[CrossBorderStressResult] = []
    qdii_target = config.qdii_target_weight()
    for scenario in scenarios:
        result = CrossBorderStressResult(
            scenario.scenario_id,
            scenario.name,
            _portfolio_return(config, scenario),
            _liquid_portfolio_return(config, scenario),
            qdii_target * scenario.qdii_frozen_weight_ratio,
            scenario.qdii_valuation_haircut,
            scenario.liquidity_impairment_months,
            scenario.capital_mobility_constraint_months,
            scenario.rebalance_locked_months,
            "normal",
            [],
        )
        results.append(_classify(result))
    return results
