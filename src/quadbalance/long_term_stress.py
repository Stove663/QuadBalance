"""Long-term macro regime stress scenarios."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quadbalance.config import StrategyConfig
from quadbalance.metrics import compute_metrics
from quadbalance.simulator import simulate, simulate_lifecycle


@dataclass(frozen=True)
class LongTermPhase:
    years: int
    stocks_return: float
    bonds_return: float
    gold_return: float
    cash_return: float
    cpi: float
    label: str
    qdii_return_drag: float = 0.0
    currency_drag: float = 0.0


@dataclass(frozen=True)
class LongTermScenario:
    scenario_id: str
    scenario_name: str
    horizon_years: int
    phases: tuple[LongTermPhase, ...]


@dataclass(frozen=True)
class LongTermScenarioResult:
    scenario_id: str
    scenario_name: str
    horizon_years: int
    nominal_annualized_return: float
    real_annualized_return: float
    real_terminal_wealth: float
    max_drawdown: float
    longest_underwater_days: int
    worst_rolling_5y_real_return: float
    worst_rolling_10y_real_return: float
    purchasing_power_preserved: bool
    classification: str
    threshold_reasons: list[str]
    withdrawal_4pct_depleted: bool = False
    withdrawal_4pct_terminal_wealth: float = 0.0


SCENARIOS: tuple[LongTermScenario, ...] = (
    LongTermScenario(
        "LT1",
        "Prolonged stagflation",
        10,
        (
            LongTermPhase(4, -0.04, -0.05, 0.04, 0.02, 0.08, "oil-shock inflation"),
            LongTermPhase(6, -0.02, -0.03, 0.02, 0.015, 0.06, "sticky inflation", qdii_return_drag=-0.03, currency_drag=0.02),
        ),
    ),
    LongTermScenario(
        "LT2",
        "Deflationary stagnation",
        20,
        (
            LongTermPhase(5, -0.03, 0.01, -0.01, 0.004, -0.01, "deleveraging onset", qdii_return_drag=-0.01, currency_drag=0.01),
            LongTermPhase(10, -0.015, 0.005, -0.005, 0.003, -0.008, "persistent deflation", qdii_return_drag=-0.015, currency_drag=0.005),
            LongTermPhase(5, -0.01, 0.003, 0.0, 0.002, -0.005, "late stagnation", qdii_return_drag=-0.01, currency_drag=0.005),
        ),
    ),
    LongTermScenario(
        "LT3",
        "Balance-sheet recession / Japanification",
        30,
        (
            LongTermPhase(5, -0.04, 0.02, -0.015, 0.005, -0.01, "bank deleveraging", qdii_return_drag=-0.02, currency_drag=0.01),
            LongTermPhase(10, -0.015, 0.003, -0.008, 0.0025, -0.006, "persistent deflation", qdii_return_drag=-0.03, currency_drag=0.015),
            LongTermPhase(15, -0.005, 0.001, -0.003, 0.001, -0.003, "lost decades plateau", qdii_return_drag=-0.035, currency_drag=0.02),
        ),
    ),
)


def _scenario_daily_series(start: float, phase: LongTermPhase) -> pd.Series:
    idx = pd.RangeIndex(phase.years * 252)
    growth = np.arange(len(idx), dtype=float) / 252.0
    return pd.Series(start * (1 + phase.stocks_return) ** growth, index=idx)


def build_synthetic_prices(prices: pd.DataFrame, scenario: LongTermScenario) -> pd.DataFrame:
    total_days = sum(phase.years for phase in scenario.phases) * 252
    synthetic = pd.DataFrame(index=pd.bdate_range(prices.index[0], periods=total_days))
    for col in prices.columns:
        col_series = []
        current = float(prices[col].iloc[0])
        for phase in scenario.phases:
            growth = np.arange(phase.years * 252, dtype=float) / 252.0
            if col.lower().startswith("bond"):
                r = phase.bonds_return
            elif col.lower().startswith("gold"):
                r = phase.gold_return
            elif col.lower().startswith("cash"):
                r = phase.cash_return
            else:
                r = phase.stocks_return
                if "qdii" in col.lower():
                    r += phase.qdii_return_drag - phase.currency_drag
            segment = current * (1 + r) ** growth
            current = float(segment[-1])
            col_series.append(segment)
        synthetic[col] = np.concatenate(col_series)
    return synthetic


def classify_long_term(metrics) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if metrics.real_annualized_return < 0:
        reasons.append("negative real annualized return")
    if metrics.longest_underwater_days > 252 * 5:
        reasons.append("underwater duration exceeds 5 years")
    if metrics.worst_rolling_5y_real_return < -0.10:
        reasons.append("worst rolling 5-year real return below -10%")
    if metrics.real_terminal_wealth < 0.8:
        reasons.append("real terminal wealth loss exceeds 20%")
    if metrics.worst_rolling_10y_real_return < -0.10:
        reasons.append("worst rolling 10-year real return below -10%")
    if metrics.real_annualized_return >= 0 and metrics.longest_underwater_days <= 252 * 5 and metrics.real_terminal_wealth >= 1.0:
        return "normal", reasons
    if metrics.worst_rolling_5y_real_return < -0.10 or metrics.real_terminal_wealth < 0.8 or metrics.longest_underwater_days > 252 * 10:
        return "thesis-broken", reasons
    return "review-required", reasons


def _scenario_phase_metrics(prices: pd.DataFrame, config: StrategyConfig, phase: LongTermPhase) -> tuple[float, float, float, float, int, float, pd.Series]:
    synthetic = prices.copy()
    total_days = phase.years * 252
    growth = np.arange(total_days, dtype=float) / 252.0
    for col in synthetic.columns:
        if col.lower().startswith("bond"):
            r = phase.bonds_return
        elif col.lower().startswith("gold"):
            r = phase.gold_return
        elif col.lower().startswith("cash"):
            r = phase.cash_return
        else:
            r = phase.stocks_return
            if "qdii" in col.lower():
                r += phase.qdii_return_drag - phase.currency_drag
        synthetic[col] = synthetic[col].iloc[0] * (1 + r) ** growth
    sim = simulate(synthetic, config)
    metrics = compute_metrics(sim, config, synthetic, risk_free_annual=0.0, inflation_annual=phase.cpi)
    return (
        metrics.annualized_return,
        metrics.real_annualized_return,
        metrics.real_terminal_wealth,
        metrics.max_drawdown,
        metrics.longest_underwater_days,
        metrics.worst_rolling_5y_real_return,
        sim.daily_values,
    )


def _worst_rolling_10y_real_return(daily_values: pd.Series, inflation_annual: float) -> float:
    if len(daily_values) < 252 * 10 + 1:
        return 0.0
    window = daily_values.pct_change(252 * 10).dropna()
    if len(window) == 0:
        return 0.0
    real_window = (1.0 + window) / ((1.0 + inflation_annual) ** 10) - 1.0
    return float(real_window.min())


def run_long_term_scenario(prices: pd.DataFrame, config: StrategyConfig, scenario: LongTermScenario) -> LongTermScenarioResult:
    synthetic = build_synthetic_prices(prices, scenario)
    sim = simulate(synthetic, config)
    metrics = compute_metrics(sim, config, synthetic, risk_free_annual=0.0, inflation_annual=scenario.phases[-1].cpi)
    phase_reasons: list[str] = []
    for phase in scenario.phases:
        _, real_ann, _, mdd, _, _, _ = _scenario_phase_metrics(prices, config, phase)
        phase_reasons.append(f"{phase.label}: real ann {real_ann:.1%}, mdd {mdd:.1%}")

    withdrawal_4pct = simulate_lifecycle(synthetic, config, "withdrawal_4pct_long_term", withdrawal_rate=0.04, withdrawal_mode="annual")
    classification, reasons = classify_long_term(metrics)
    reasons.extend(phase_reasons)
    if withdrawal_4pct.depleted:
        reasons.append("4% withdrawal depletes under long-term regime")
    return LongTermScenarioResult(
        scenario.scenario_id,
        scenario.scenario_name,
        scenario.horizon_years,
        metrics.annualized_return,
        metrics.real_annualized_return,
        metrics.real_terminal_wealth,
        metrics.max_drawdown,
        metrics.longest_underwater_days,
        metrics.worst_rolling_5y_real_return,
        _worst_rolling_10y_real_return(sim.daily_values, scenario.phases[-1].cpi),
        metrics.real_terminal_wealth >= 1.0,
        classification,
        reasons,
        withdrawal_4pct_depleted=withdrawal_4pct.depleted,
        withdrawal_4pct_terminal_wealth=withdrawal_4pct.real_terminal_value,
    )
