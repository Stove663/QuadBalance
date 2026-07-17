"""Long-term macro regime stress scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from quadbalance.config import StrategyConfig
from quadbalance.metrics import compute_metrics
from quadbalance.simulator import simulate, simulate_lifecycle


@dataclass(frozen=True)
class LongTermPathSegment:
    name: str
    months: int
    stock_multiplier: float = 1.0
    bond_multiplier: float = 1.0
    gold_multiplier: float = 1.0
    cash_multiplier: float = 1.0
    cpi_multiplier: float = 1.0
    qdii_multiplier: float = 1.0
    currency_multiplier: float = 1.0
    shock: bool = False
    rebound: bool = False


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
    path_segments: tuple[LongTermPathSegment, ...] = field(default_factory=tuple)
    path_mode: str = "smooth"


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
    path_mode: str
    nominal_annualized_return: float
    real_annualized_return: float
    real_terminal_wealth: float
    max_drawdown: float
    real_max_drawdown: float
    longest_underwater_days: int
    real_longest_underwater_days: int
    real_recovery_days: int | None
    worst_rolling_5y_real_return: float
    worst_rolling_10y_real_return: float
    worst_1m_return: float
    worst_q_return: float
    false_recoveries: int
    phase_realized_returns: dict[str, float] = field(default_factory=dict)
    purchasing_power_preserved: bool = False
    classification: str = "normal"
    threshold_reasons: list[str] = field(default_factory=list)
    withdrawal_4pct_depleted: bool = False
    withdrawal_4pct_terminal_wealth: float = 0.0
    sequence_risk_results: list[dict[str, object]] = field(default_factory=list)


SCENARIOS: tuple[LongTermScenario, ...] = (
    LongTermScenario(
        "LT1",
        "Prolonged stagflation",
        10,
        (
            LongTermPhase(
                4,
                -0.04,
                -0.05,
                0.04,
                0.02,
                0.08,
                "oil-shock inflation",
                path_segments=(
                    LongTermPathSegment("crash", 8, stock_multiplier=2.0, bond_multiplier=1.5, gold_multiplier=0.8, shock=True),
                    LongTermPathSegment("failed rebound", 8, stock_multiplier=0.8, rebound=True),
                    LongTermPathSegment("stagnation", 32, stock_multiplier=0.5, bond_multiplier=0.7),
                ),
                path_mode="shaped",
            ),
            LongTermPhase(
                6,
                -0.02,
                -0.03,
                0.02,
                0.015,
                0.06,
                "sticky inflation",
                qdii_return_drag=-0.03,
                currency_drag=0.02,
                path_segments=(
                    LongTermPathSegment("grind-down", 24, stock_multiplier=1.2, bond_multiplier=1.1, qdii_multiplier=1.3),
                    LongTermPathSegment("plateau", 24, stock_multiplier=0.6, bond_multiplier=0.8, rebound=True),
                    LongTermPathSegment("late rebound", 24, stock_multiplier=1.1, qdii_multiplier=0.9, rebound=True),
                ),
                path_mode="shaped",
            ),
        ),
    ),
    LongTermScenario(
        "LT2",
        "Deflationary stagnation",
        20,
        (
            LongTermPhase(
                5,
                -0.03,
                0.01,
                -0.01,
                0.004,
                -0.01,
                "deleveraging onset",
                qdii_return_drag=-0.01,
                currency_drag=0.01,
                path_segments=(
                    LongTermPathSegment("shock", 12, stock_multiplier=1.8, bond_multiplier=0.9, shock=True),
                    LongTermPathSegment("failed rebound", 18, stock_multiplier=0.7, qdii_multiplier=1.2),
                    LongTermPathSegment("stagnation plateau", 30, stock_multiplier=0.4, bond_multiplier=0.8),
                ),
                path_mode="shaped",
            ),
            LongTermPhase(
                10,
                -0.015,
                0.005,
                -0.005,
                0.003,
                -0.008,
                "persistent deflation",
                qdii_return_drag=-0.015,
                currency_drag=0.005,
                path_segments=(
                    LongTermPathSegment("slow bleed", 36, stock_multiplier=0.7, bond_multiplier=0.9),
                    LongTermPathSegment("brief rebound", 12, stock_multiplier=1.0, rebound=True),
                    LongTermPathSegment("renewed grind", 72, stock_multiplier=0.6, qdii_multiplier=1.1),
                ),
                path_mode="shaped",
            ),
            LongTermPhase(
                5,
                -0.01,
                0.003,
                0.0,
                0.002,
                -0.005,
                "late stagnation",
                qdii_return_drag=-0.01,
                currency_drag=0.005,
                path_segments=(
                    LongTermPathSegment("plateau", 20, stock_multiplier=0.6),
                    LongTermPathSegment("rebound", 20, stock_multiplier=1.0, rebound=True),
                    LongTermPathSegment("fade", 20, stock_multiplier=0.5),
                ),
                path_mode="shaped",
            ),
        ),
    ),
    LongTermScenario(
        "LT3",
        "Balance-sheet recession / Japanification",
        30,
        (
            LongTermPhase(
                5,
                -0.04,
                0.02,
                -0.015,
                0.005,
                -0.01,
                "bank deleveraging",
                qdii_return_drag=-0.02,
                currency_drag=0.01,
                path_segments=(
                    LongTermPathSegment("crisis", 12, stock_multiplier=2.2, shock=True),
                    LongTermPathSegment("failed rebound", 24, stock_multiplier=0.8),
                    LongTermPathSegment("plateau", 24, stock_multiplier=0.5, bond_multiplier=0.8),
                ),
                path_mode="shaped",
            ),
            LongTermPhase(
                10,
                -0.015,
                0.003,
                -0.008,
                0.0025,
                -0.006,
                "persistent deflation",
                qdii_return_drag=-0.03,
                currency_drag=0.015,
                path_segments=(
                    LongTermPathSegment("grind-down", 48, stock_multiplier=0.7, qdii_multiplier=1.2),
                    LongTermPathSegment("bear-market rally", 12, stock_multiplier=1.3, rebound=True),
                    LongTermPathSegment("renewed drift", 60, stock_multiplier=0.5),
                ),
                path_mode="shaped",
            ),
            LongTermPhase(
                15,
                -0.005,
                0.001,
                -0.003,
                0.001,
                -0.003,
                "lost decades plateau",
                qdii_return_drag=-0.035,
                currency_drag=0.02,
                path_segments=(
                    LongTermPathSegment("stagnation", 60, stock_multiplier=0.4),
                    LongTermPathSegment("false recovery", 12, stock_multiplier=1.4, rebound=True),
                    LongTermPathSegment("plateau", 108, stock_multiplier=0.6, bond_multiplier=0.9),
                ),
                path_mode="shaped",
            ),
        ),
    ),
)


def _scenario_daily_series(start: float, phase: LongTermPhase) -> pd.Series:
    idx = pd.RangeIndex(phase.years * 252)
    growth = np.arange(len(idx), dtype=float) / 252.0
    return pd.Series(start * (1 + phase.stocks_return) ** growth, index=idx)


def _cpi_factor_for_phase(cpi: float, years: int) -> float:
    return (1.0 + cpi) ** years


def _build_segment_series(start: float, total_days: int, segments: tuple[LongTermPathSegment, ...], base_daily_return: float, stock_multiplier: float, qdii_multiplier: float = 1.0, currency_multiplier: float = 1.0) -> np.ndarray:
    if not segments:
        return start * (1 + base_daily_return) ** np.arange(total_days, dtype=float)
    total_months = sum(s.months for s in segments)
    seg_days = [max(1, int(total_days * (s.months / total_months))) for s in segments]
    seg_days[-1] += total_days - sum(seg_days)
    out = np.empty(total_days, dtype=float)
    current = start
    pos = 0
    for seg, n in zip(segments, seg_days):
        daily = np.full(n, base_daily_return)
        if seg.shock:
            daily[: max(1, n // 4)] -= abs(base_daily_return) * 6 * seg.stock_multiplier
        if seg.rebound:
            daily[-max(1, n // 4):] += abs(base_daily_return) * 5 * seg.stock_multiplier
        if seg.name.lower().startswith("plateau") or seg.name.lower().startswith("stagnation"):
            daily += -abs(base_daily_return) * 0.5
        for d in daily:
            current *= 1.0 + (d * stock_multiplier * qdii_multiplier / currency_multiplier)
            out[pos] = current
            pos += 1
    return out


def build_synthetic_prices(prices: pd.DataFrame, scenario: LongTermScenario, path_mode: str = "smooth") -> pd.DataFrame:
    total_days = sum(phase.years for phase in scenario.phases) * 252
    synthetic = pd.DataFrame(index=pd.bdate_range(prices.index[0], periods=total_days))
    synthetic.attrs["path_mode"] = path_mode
    for col in prices.columns:
        current = float(prices[col].iloc[0])
        pieces: list[np.ndarray] = []
        for phase in scenario.phases:
            base_daily = (1 + (phase.bonds_return if col.lower().startswith("bond") else phase.gold_return if col.lower().startswith("gold") else phase.cash_return if col.lower().startswith("cash") else phase.stocks_return)) ** (1 / 252.0) - 1.0
            if col.lower().startswith("bond"):
                mult = 1.0
            elif col.lower().startswith("gold"):
                mult = 1.0
            elif col.lower().startswith("cash"):
                mult = 1.0
            else:
                mult = 1.0
            qdii_mult = 1.0 + phase.qdii_return_drag if "qdii" in col.lower() else 1.0
            ccy_mult = 1.0 + phase.currency_drag if "qdii" in col.lower() else 1.0
            if path_mode == "shaped" and phase.path_segments:
                segment = _build_segment_series(current, phase.years * 252, phase.path_segments, base_daily, mult, qdii_mult, ccy_mult)
            else:
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
            pieces.append(segment)
        synthetic[col] = np.concatenate(pieces)
    return synthetic


def _daily_real_series(nominal: pd.Series, inflation_annual: float) -> pd.Series:
    inflation_daily = (1.0 + inflation_annual) ** (1 / 252.0) - 1.0
    factor = (1.0 + inflation_daily) ** np.arange(len(nominal), dtype=float)
    return nominal / factor


def _path_metrics(daily_values: pd.Series, inflation_annual: float) -> tuple[float, float, int | None, int, float, float, int]:
    real = _daily_real_series(daily_values, inflation_annual)
    real_peak = real.cummax()
    real_dd = real / real_peak - 1
    trough = real_dd.idxmin()
    peak = real.loc[:trough].idxmax()
    recovery = real.loc[trough:]
    recovered = recovery[recovery >= real.loc[peak]]
    recovery_days = int((recovered.index[0] - peak).days) if not recovered.empty else None
    longest_real_underwater = int((real < real_peak).astype(int).groupby((real >= real_peak).astype(int).cumsum()).sum().max()) if len(real) else 0
    monthly = daily_values.resample("ME").last().pct_change().dropna()
    quarterly = daily_values.resample("QE").last().pct_change().dropna()
    worst_1m = float(monthly.min()) if len(monthly) else 0.0
    worst_q = float(quarterly.min()) if len(quarterly) else 0.0
    false_recoveries = int(((daily_values < daily_values.cummax()) & (daily_values.shift(1) >= daily_values.shift(1).cummax())).sum()) if len(daily_values) else 0
    return float(real_dd.min()), float(real.iloc[-1] / max(real_peak.iloc[-1], 1.0)), recovery_days, longest_real_underwater, worst_1m, worst_q, false_recoveries


def classify_long_term(metrics) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if metrics.real_annualized_return < 0:
        reasons.append("negative real annualized return")
    if metrics.real_max_drawdown < -0.20:
        reasons.append("real max drawdown breaches 20%")
    if metrics.real_longest_underwater_days > 252 * 5:
        reasons.append("real underwater duration exceeds 5 years")
    if metrics.worst_rolling_5y_real_return < -0.10:
        reasons.append("worst rolling 5-year real return below -10%")
    if metrics.real_terminal_wealth < 0.8:
        reasons.append("real terminal wealth loss exceeds 20%")
    if metrics.worst_rolling_10y_real_return < -0.10:
        reasons.append("worst rolling 10-year real return below -10%")
    if metrics.real_annualized_return >= 0 and metrics.real_longest_underwater_days <= 252 * 5 and metrics.real_terminal_wealth >= 1.0:
        return "normal", reasons
    if metrics.real_max_drawdown < -0.20 or metrics.real_terminal_wealth < 0.8 or metrics.real_longest_underwater_days > 252 * 10:
        return "thesis-broken", reasons
    return "review-required", reasons


def _scenario_phase_metrics(prices: pd.DataFrame, config: StrategyConfig, phase: LongTermPhase) -> tuple[float, float, float, float, int, float, pd.Series]:
    total_days = phase.years * 252
    growth = np.arange(total_days, dtype=float) / 252.0
    synthetic = pd.DataFrame(index=pd.bdate_range(prices.index[0], periods=total_days))
    for col in prices.columns:
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
        synthetic[col] = float(prices[col].iloc[0]) * (1 + r) ** growth
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
    inflation_factor = (1.0 + inflation_annual) ** (252 * 10 / 252.0)
    real_window = (1.0 + window) / inflation_factor - 1.0
    return float(real_window.min())


def run_long_term_scenario(prices: pd.DataFrame, config: StrategyConfig, scenario: LongTermScenario, path_mode: str = "smooth") -> LongTermScenarioResult:
    synthetic = build_synthetic_prices(prices, scenario, path_mode=path_mode)
    sim = simulate(synthetic, config)
    metrics = compute_metrics(sim, config, synthetic, risk_free_annual=0.0, inflation_annual=scenario.phases[-1].cpi)
    phase_reasons: list[str] = []
    phase_realized: dict[str, float] = {}
    for phase in scenario.phases:
        ann, real_ann, real_term, mdd, underwater, worst_5y, _ = _scenario_phase_metrics(prices, config, phase)
        phase_realized[phase.label] = real_ann
        phase_reasons.append(f"{phase.label}: target real ann {real_ann:.1%}, mdd {mdd:.1%}, underwater {underwater}d")

    inflation = scenario.phases[-1].cpi
    real_daily = _daily_real_series(sim.daily_values, inflation)
    real_peak = real_daily.cummax()
    real_dd = real_daily / real_peak - 1
    real_trough_idx = real_dd.idxmin()
    real_peak_idx = real_daily.loc[:real_trough_idx].idxmax()
    real_recovery = real_daily.loc[real_trough_idx:]
    real_recovered = real_recovery[real_recovery >= real_daily.loc[real_peak_idx]]
    real_recovery_days = int((real_recovered.index[0] - real_peak_idx).days) if not real_recovered.empty else None
    real_longest_underwater_days = int((real_daily < real_peak).astype(int).groupby((real_daily >= real_peak).astype(int).cumsum()).sum().max()) if len(real_daily) else 0
    real_max_drawdown = float(real_dd.min())
    worst_1m = float(sim.daily_values.resample("ME").last().pct_change().dropna().min()) if len(sim.daily_values) else 0.0
    worst_q = float(sim.daily_values.resample("QE").last().pct_change().dropna().min()) if len(sim.daily_values) else 0.0
    false_recoveries = int(((sim.daily_values < sim.daily_values.cummax()) & (sim.daily_values.shift(1) >= sim.daily_values.shift(1).cummax())).sum()) if len(sim.daily_values) else 0

    withdrawal_4pct = simulate_lifecycle(synthetic, config, "withdrawal_4pct_long_term", withdrawal_rate=0.04, withdrawal_mode="annual")
    sequence_profiles = [
        ("seq_fixed", simulate_lifecycle(synthetic, config, "bear_market_retirement_start", withdrawal_rate=0.04, withdrawal_mode="annual")),
        ("seq_inflation", simulate_lifecycle(synthetic, config, "inflation_escalation", withdrawal_rate=0.04, withdrawal_mode="annual")),
        ("seq_lumpy", simulate_lifecycle(synthetic, config, "one_time_liquidity_20pct", withdrawal_rate=0.0, withdrawal_mode="annual")),
        ("seq_interrupt", simulate_lifecycle(synthetic, config, "contribution_interrupt", withdrawal_rate=0.0, interrupt_months=24, withdrawal_mode="annual")),
    ]
    long_term_metrics = type(
        "M",
        (),
        {
            **metrics.__dict__,
            "real_max_drawdown": real_max_drawdown,
            "real_longest_underwater_days": real_longest_underwater_days,
            "worst_rolling_10y_real_return": _worst_rolling_10y_real_return(sim.daily_values, inflation),
        },
    )()
    classification, reasons = classify_long_term(long_term_metrics)
    reasons.extend(phase_reasons)
    sequence_risk_results: list[dict[str, object]] = []
    for sid, result in sequence_profiles:
        seq_class = "thesis-broken" if result.depleted or result.safe_spending_breached else ("review-required" if result.withdrawal_coverage_ratio < 0.95 else "normal")
        sequence_risk_results.append({"scenario_id": sid, "classification": seq_class, "reasons": [f"coverage {result.withdrawal_coverage_ratio:.1%}", f"forced sale {result.forced_sale_amount:,.0f}"]})
        if seq_class != "normal":
            reasons.append(f"{sid}: {result.withdrawal_coverage_ratio:.1%} coverage, forced sale {result.forced_sale_amount:,.0f}")
    if withdrawal_4pct.depleted:
        reasons.append("4% withdrawal depletes under long-term regime")
    return LongTermScenarioResult(
        scenario.scenario_id,
        scenario.scenario_name,
        scenario.horizon_years,
        path_mode,
        metrics.annualized_return,
        metrics.real_annualized_return,
        metrics.real_terminal_wealth,
        metrics.max_drawdown,
        real_max_drawdown,
        metrics.longest_underwater_days,
        real_longest_underwater_days,
        real_recovery_days,
        metrics.worst_rolling_5y_real_return,
        _worst_rolling_10y_real_return(sim.daily_values, scenario.phases[-1].cpi),
        worst_1m,
        worst_q,
        false_recoveries,
        phase_realized_returns=phase_realized,
        purchasing_power_preserved=metrics.real_terminal_wealth >= 1.0,
        classification=classification,
        threshold_reasons=reasons,
        withdrawal_4pct_depleted=withdrawal_4pct.depleted,
        withdrawal_4pct_terminal_wealth=withdrawal_4pct.real_terminal_value,
        sequence_risk_results=sequence_risk_results,
    )
