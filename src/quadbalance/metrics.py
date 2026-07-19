"""Performance metrics calculation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from quadbalance.config import CASH_SYMBOL, StrategyConfig
from quadbalance.profile_thresholds import DEFAULT_INVESTOR_PROFILES, InvestorProfile
from quadbalance.simulator import SimulationResult, simulate


@dataclass
class ProfileSuitability:
    profile_id: str
    classification: str
    reasons: list[str]
    drivers: list[str]
    warnings: list[str]
    governance_notes: list[str]
    qdii_friction_months: int = 0
    qdii_recovery_months: int = 0
    sequence_risk_classification: str = "normal"
    sequence_risk_reasons: list[str] = field(default_factory=list)


@dataclass
class PerformanceMetrics:
    annualized_return: float
    annualized_volatility: float
    max_drawdown: float
    max_drawdown_peak: str
    max_drawdown_trough: str
    sharpe_ratio: float
    positive_years_pct: float
    rebalance_premium: float
    worst_year_return: float
    annual_returns: pd.Series
    max_drawdown_recovery_days: int | None = None
    real_annualized_return: float = 0.0
    real_terminal_wealth: float = 0.0
    worst_rolling_1y_return: float = 0.0
    worst_rolling_3y_return: float = 0.0
    worst_rolling_5y_return: float = 0.0
    worst_rolling_1y_real_return: float = 0.0
    worst_rolling_3y_real_return: float = 0.0
    worst_rolling_5y_real_return: float = 0.0
    longest_underwater_days: int = 0
    average_drawdown: float = 0.0
    ulcer_index: float = 0.0
    pain_index: float = 0.0
    cdar_95: float = 0.0
    drawdown_10pct_events: int = 0
    drawdown_15pct_events: int = 0
    drawdown_20pct_events: int = 0


def _annual_returns(daily_values: pd.Series) -> pd.Series:
    grouped = daily_values.groupby(daily_values.index.year)
    returns = grouped.apply(lambda s: s.iloc[-1] / s.iloc[0] - 1)
    returns.index.name = "year"
    return returns


def _max_drawdown(daily_values: pd.Series) -> tuple[float, str, str]:
    cummax = daily_values.cummax()
    drawdown = daily_values / cummax - 1
    trough_idx = drawdown.idxmin()
    peak_idx = daily_values.loc[:trough_idx].idxmax()
    return float(drawdown.min()), peak_idx.strftime("%Y-%m-%d"), trough_idx.strftime("%Y-%m-%d")


def _worst_rolling_return(daily_values: pd.Series, window: int) -> float:
    if len(daily_values) < window + 1:
        return 0.0
    rolling = daily_values.pct_change(window).dropna()
    return float(rolling.min()) if len(rolling) else 0.0


def _worst_rolling_real_return(daily_values: pd.Series, window: int, inflation_annual: float) -> float:
    if len(daily_values) < window + 1:
        return 0.0
    nominal = daily_values.pct_change(window).dropna()
    if len(nominal) == 0:
        return 0.0
    real = (1.0 + nominal) / ((1.0 + inflation_annual) ** (window / 252.0)) - 1.0
    return float(real.min())


def _longest_underwater_days(daily_values: pd.Series) -> int:
    peak = daily_values.cummax()
    underwater = daily_values < peak
    longest = current = 0
    for flag in underwater:
        if flag:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _drawdown_series(daily_values: pd.Series) -> pd.Series:
    return daily_values / daily_values.cummax() - 1.0


def _drawdown_event_count(drawdown: pd.Series, threshold: float) -> int:
    in_event = False
    events = 0
    for value in drawdown:
        breached = value <= threshold
        if breached and not in_event:
            events += 1
            in_event = True
        elif value >= 0:
            in_event = False
    return events


def _drawdown_pain_metrics(daily_values: pd.Series) -> dict[str, float | int]:
    drawdown = _drawdown_series(daily_values)
    negative = drawdown[drawdown < 0]
    abs_negative = negative.abs()
    if abs_negative.empty:
        return {
            "average_drawdown": 0.0,
            "ulcer_index": 0.0,
            "pain_index": 0.0,
            "cdar_95": 0.0,
            "drawdown_10pct_events": 0,
            "drawdown_15pct_events": 0,
            "drawdown_20pct_events": 0,
        }
    cutoff = abs_negative.quantile(0.95)
    tail = abs_negative[abs_negative >= cutoff]
    return {
        "average_drawdown": -float(abs_negative.mean()),
        "ulcer_index": float(np.sqrt((drawdown.pow(2).mean()))),
        "pain_index": float(abs_negative.sum() / len(drawdown)),
        "cdar_95": -float(tail.mean()) if len(tail) else 0.0,
        "drawdown_10pct_events": _drawdown_event_count(drawdown, -0.10),
        "drawdown_15pct_events": _drawdown_event_count(drawdown, -0.15),
        "drawdown_20pct_events": _drawdown_event_count(drawdown, -0.20),
    }


def _max_drawdown_recovery_days(daily_values: pd.Series) -> int | None:
    cummax = daily_values.cummax()
    drawdown = daily_values / cummax - 1
    trough_idx = drawdown.idxmin()
    peak_idx = daily_values.loc[:trough_idx].idxmax()
    peak_value = float(daily_values.loc[peak_idx])
    recovery = daily_values.loc[trough_idx:]
    recovered = recovery[recovery >= peak_value]
    if recovered.empty:
        return None
    # Count trading sessions in the series, not calendar days (aligns with MAX_NAV_RECOVERY_DAYS=252).
    peak_pos = daily_values.index.get_loc(peak_idx)
    recover_pos = daily_values.index.get_loc(recovered.index[0])
    if isinstance(peak_pos, slice):
        peak_pos = peak_pos.start
    if isinstance(recover_pos, slice):
        recover_pos = recover_pos.start
    return int(recover_pos - peak_pos)


def time_weighted_daily_returns(daily_values: pd.Series, cashflows: pd.Series) -> pd.Series:
    """Daily TWR linking returns: r_t = (V_t - CF_t) / V_{t-1} - 1.

    External inflows (contributions) are stripped so DCA deposits are not treated as performance.
    ``cashflows`` should be aligned to ``daily_values`` (0 on non-flow days). Day-0 base capital
    is ignored for linking (performance starts from the first post-inception return).
    """
    if daily_values.empty:
        return pd.Series(dtype=float)
    cf = cashflows.reindex(daily_values.index).fillna(0.0).astype(float)
    prev = daily_values.shift(1)
    linked = (daily_values - cf) / prev - 1.0
    return linked.iloc[1:].replace([np.inf, -np.inf], np.nan).fillna(0.0)


def external_cashflows_from_events(daily_values: pd.Series, events: list) -> pd.Series:
    """Sum base_position / contribution / withdrawal cash amounts onto the value index."""
    cf = pd.Series(0.0, index=daily_values.index)
    for event in events or []:
        event_type = getattr(event, "event_type", None)
        amount = float(getattr(event, "cash_amount", 0.0) or 0.0)
        if amount == 0.0 or event_type not in {"base_position", "contribution", "withdrawal"}:
            continue
        dt = pd.Timestamp(getattr(event, "date"))
        if dt not in cf.index:
            continue
        # Withdrawals are outflows (negative external cashflow for TWR).
        cf.loc[dt] += -amount if event_type == "withdrawal" else amount
    return cf


def dca_schedule_cashflows(
    index: pd.DatetimeIndex,
    base_capital: float,
    monthly_contribution: float,
    month_starts: set | pd.DatetimeIndex | list,
) -> pd.Series:
    """Cashflow schedule matching simulator DCA: base on day 0, monthly on later month-starts."""
    cf = pd.Series(0.0, index=index)
    if len(index) == 0:
        return cf
    cf.iloc[0] = float(base_capital)
    month_start_set = set(pd.DatetimeIndex(list(month_starts)))
    for dt in index[1:]:
        if dt in month_start_set:
            cf.loc[dt] = float(monthly_contribution)
    return cf


def annualized_twr(daily_returns: pd.Series) -> float:
    if daily_returns.empty:
        return 0.0
    years = len(daily_returns) / 252.0
    if years <= 0:
        return 0.0
    return float((1.0 + daily_returns).prod() ** (1.0 / years) - 1.0)


def _twr_wealth_index(daily_returns: pd.Series) -> pd.Series:
    if daily_returns.empty:
        return pd.Series(dtype=float)
    return (1.0 + daily_returns).cumprod()


def compute_metrics(
    result: SimulationResult,
    config: StrategyConfig,
    prices: pd.DataFrame,
    risk_free_annual: float,
    no_rebalance_result: SimulationResult | None = None,
    inflation_annual: float = 0.03,
    include_rebalance_premium: bool = True,
) -> PerformanceMetrics:
    daily = result.daily_values
    cashflows = external_cashflows_from_events(daily, getattr(result, "events", []) or [])
    # Fall back if events are missing (synthetic / partial results).
    if float(cashflows.sum()) <= 0 and len(daily):
        from quadbalance.asset_universe import BASE_CAPITAL, MONTHLY_CONTRIBUTION
        from quadbalance.simulator import _first_trading_days_per_month

        cashflows = dca_schedule_cashflows(
            daily.index,
            BASE_CAPITAL,
            MONTHLY_CONTRIBUTION,
            _first_trading_days_per_month(daily.index),
        )

    twr_returns = time_weighted_daily_returns(daily, cashflows)
    twr_index = _twr_wealth_index(twr_returns)
    trading_days = len(daily)
    years = trading_days / 252

    ann_return = annualized_twr(twr_returns)
    ann_vol = float(twr_returns.std() * np.sqrt(252)) if len(twr_returns) else 0.0
    wealth_for_risk = twr_index if len(twr_index) else daily
    mdd, peak, trough = _max_drawdown(wealth_for_risk)
    sharpe = (ann_return - risk_free_annual) / ann_vol if ann_vol > 0 else 0.0

    annual_rets = _annual_returns(wealth_for_risk)
    positive_pct = float((annual_rets > 0).mean()) if len(annual_rets) else 0.0
    worst_year = float(annual_rets.min()) if len(annual_rets) else 0.0

    rebalance_premium = 0.0
    if include_rebalance_premium and no_rebalance_result is not None:
        nr_cf = external_cashflows_from_events(
            no_rebalance_result.daily_values,
            getattr(no_rebalance_result, "events", []) or [],
        )
        nr_twr = time_weighted_daily_returns(no_rebalance_result.daily_values, nr_cf)
        rebalance_premium = ann_return - annualized_twr(nr_twr)

    total_contributed = float(cashflows[cashflows > 0].sum())
    real_factor = (1.0 + inflation_annual) ** years if years > 0 else 1.0
    real_terminal_value = daily.iloc[-1] / real_factor if real_factor > 0 else daily.iloc[-1]
    # Purchasing-power multiple of capital contributed (1.0 ≈ real capital preserved).
    real_terminal = (real_terminal_value / total_contributed) if total_contributed > 0 else 0.0
    real_ann_return = ((1 + ann_return) / (1 + inflation_annual) - 1) if inflation_annual > -1 else ann_return

    worst_1y = _worst_rolling_return(wealth_for_risk, 252)
    worst_3y = _worst_rolling_return(wealth_for_risk, 252 * 3)
    worst_5y = _worst_rolling_return(wealth_for_risk, 252 * 5)
    worst_1y_real = _worst_rolling_real_return(wealth_for_risk, 252, inflation_annual)
    worst_3y_real = _worst_rolling_real_return(wealth_for_risk, 252 * 3, inflation_annual)
    worst_5y_real = _worst_rolling_real_return(wealth_for_risk, 252 * 5, inflation_annual)
    pain = _drawdown_pain_metrics(wealth_for_risk)

    return PerformanceMetrics(
        annualized_return=ann_return,
        annualized_volatility=ann_vol,
        max_drawdown=mdd,
        max_drawdown_peak=peak,
        max_drawdown_trough=trough,
        max_drawdown_recovery_days=_max_drawdown_recovery_days(wealth_for_risk),
        sharpe_ratio=sharpe,
        positive_years_pct=positive_pct,
        rebalance_premium=rebalance_premium,
        worst_year_return=worst_year,
        annual_returns=annual_rets,
        real_annualized_return=real_ann_return,
        real_terminal_wealth=real_terminal,
        worst_rolling_1y_return=worst_1y,
        worst_rolling_3y_return=worst_3y,
        worst_rolling_5y_return=worst_5y,
        worst_rolling_1y_real_return=worst_1y_real,
        worst_rolling_3y_real_return=worst_3y_real,
        worst_rolling_5y_real_return=worst_5y_real,
        longest_underwater_days=_longest_underwater_days(wealth_for_risk),
        average_drawdown=float(pain["average_drawdown"]),
        ulcer_index=float(pain["ulcer_index"]),
        pain_index=float(pain["pain_index"]),
        cdar_95=float(pain["cdar_95"]),
        drawdown_10pct_events=int(pain["drawdown_10pct_events"]),
        drawdown_15pct_events=int(pain["drawdown_15pct_events"]),
        drawdown_20pct_events=int(pain["drawdown_20pct_events"]),
    )


def _qdii_notes(
    qdii_fill_rate: float,
    avg_qdii_weight_gap: float,
    qdii_friction_months: int,
    qdii_recovery_months: int,
) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    warnings: list[str] = []
    if qdii_fill_rate < 0.9:
        reasons.append("QDII fill rate below 90% target")
    if avg_qdii_weight_gap < -0.02:
        reasons.append("QDII weight gap more than 2 percentage points below target")
        warnings.append("Execution friction is suppressing QDII exposure")
    if qdii_friction_months >= 12:
        reasons.append("QDII exposure stayed more than 2 percentage points below target for at least 12 months")
        warnings.append("Profile classification should note persistent execution friction")
    if qdii_recovery_months >= 24:
        reasons.append("QDII exposure failed to recover to at least 50% of target within 24 months")
        warnings.append("Persistent quota constraints may require review")
    return reasons, warnings


def _classify_accumulation(metrics: PerformanceMetrics, qdii_reasons: list[str], qdii_warnings: list[str], profile: InvestorProfile) -> ProfileSuitability:
    reasons: list[str] = []
    drivers: list[str] = []
    warnings: list[str] = []
    if metrics.real_annualized_return > 0:
        reasons.append("positive real annualized return")
        drivers.append("real annualized return above zero")
    if metrics.annualized_return < 0.06:
        reasons.append("modest nominal growth may be too defensive for accumulation")
        warnings.append("Nominal growth may lag long-horizon accumulation goals")
    if metrics.worst_rolling_5y_real_return < 0:
        reasons.append("5-year rolling real return can fall below zero")
        drivers.append("negative 5-year rolling real return")
    reasons.extend(qdii_reasons)
    warnings.extend(qdii_warnings)
    classification = "caution"
    if metrics.worst_rolling_5y_real_return < -0.10:
        classification = "unsuitable"
    elif metrics.real_annualized_return > profile.min_real_return and metrics.max_drawdown >= profile.max_drawdown:
        classification = "suitable"
    governance = ["Accumulation classification should be reviewed if execution friction persists"] if warnings else []
    return ProfileSuitability(profile.profile_id, classification, reasons, drivers, warnings, governance)


def _classify_balanced(metrics: PerformanceMetrics, qdii_reasons: list[str], qdii_warnings: list[str], profile: InvestorProfile) -> ProfileSuitability:
    reasons: list[str] = []
    drivers: list[str] = []
    warnings: list[str] = []
    if metrics.max_drawdown >= profile.max_drawdown:
        reasons.append("drawdown within moderate tolerance")
        drivers.append("drawdown within profile tolerance")
    if metrics.real_annualized_return > 0:
        reasons.append("preserves purchasing power on average")
    reasons.extend(qdii_reasons)
    warnings.extend(qdii_warnings)
    classification = "suitable" if metrics.max_drawdown >= profile.max_drawdown and metrics.worst_rolling_5y_real_return > -0.10 else "caution"
    governance = ["Balanced core classification should be reviewed if execution friction persists"] if warnings else []
    return ProfileSuitability(profile.profile_id, classification, reasons, drivers, warnings, governance)


def _classify_preservation(metrics: PerformanceMetrics, qdii_fill_rate: float, qdii_warnings: list[str], profile: InvestorProfile) -> ProfileSuitability:
    reasons: list[str] = []
    drivers: list[str] = []
    warnings: list[str] = []
    if metrics.longest_underwater_days > 252 * 3:
        reasons.append("extended underwater duration is risky near retirement")
        drivers.append("long underwater duration")
    if qdii_fill_rate < 0.75:
        reasons.append("execution friction can worsen liquidity planning")
        warnings.append("QDII fill rate is weak for pre-retirement liquidity needs")
    warnings.extend(qdii_warnings)
    classification = "unsuitable" if metrics.max_drawdown < profile.max_drawdown or metrics.longest_underwater_days > 252 * profile.max_underwater_years else "caution"
    governance = ["Pre-retirement suitability should be reviewed when execution friction or duration risks persist"] if warnings else []
    return ProfileSuitability(profile.profile_id, classification, reasons, drivers, warnings, governance)


def _classify_retirement(metrics: PerformanceMetrics, profile: InvestorProfile) -> ProfileSuitability:
    reasons: list[str] = []
    drivers: list[str] = []
    warnings: list[str] = []
    if metrics.worst_rolling_5y_real_return < -0.10:
        reasons.append("5-year real return breach threatens purchasing power")
        drivers.append("negative 5-year rolling real return")
    if metrics.longest_underwater_days > 252 * 5:
        reasons.append("underwater duration too long for withdrawal phase")
        warnings.append("Withdrawal phase may not tolerate long recovery periods")
    classification = "unsuitable" if metrics.real_terminal_wealth <= 0 or metrics.max_drawdown < profile.max_drawdown else "caution"
    governance = ["Retirement suitability should be reviewed if depletion risk or underwater duration becomes excessive"] if warnings else []
    return ProfileSuitability(profile.profile_id, classification, reasons, drivers, warnings, governance)


def classify_suitability(
    config: StrategyConfig,
    metrics: PerformanceMetrics,
    qdii_fill_rate: float,
    avg_qdii_weight_gap: float,
    qdii_friction_months: int = 0,
    qdii_recovery_months: int = 0,
    investor_profiles: tuple[InvestorProfile, ...] = DEFAULT_INVESTOR_PROFILES,
    sequence_risk: dict[str, dict[str, object]] | None = None,
) -> dict[str, ProfileSuitability]:
    profiles: dict[str, ProfileSuitability] = {}
    qdii_reasons, qdii_warnings = _qdii_notes(qdii_fill_rate, avg_qdii_weight_gap, qdii_friction_months, qdii_recovery_months)

    sequence_risk = sequence_risk or {}
    for profile in investor_profiles:
        if profile.profile_id == "accumulation":
            profiles[profile.profile_id] = _classify_accumulation(metrics, qdii_reasons, qdii_warnings, profile)
        elif profile.profile_id == "balanced_core":
            profiles[profile.profile_id] = _classify_balanced(metrics, qdii_reasons, qdii_warnings, profile)
        elif profile.profile_id == "pre_retirement_preservation":
            profiles[profile.profile_id] = _classify_preservation(metrics, qdii_fill_rate, qdii_warnings, profile)
        else:
            profiles[profile.profile_id] = _classify_retirement(metrics, profile)
        seq = sequence_risk.get(profile.profile_id)
        if seq is not None:
            profiles[profile.profile_id].sequence_risk_classification = str(seq.get("classification", "normal"))
            profiles[profile.profile_id].sequence_risk_reasons = list(seq.get("reasons", []))

    return profiles


def cash_risk_free_rate(prices: pd.DataFrame) -> float:
    """Annualized return of cash instrument as risk-free proxy."""
    cash = prices[CASH_SYMBOL].dropna()
    if len(cash) < 2:
        return 0.02
    total = cash.iloc[-1] / cash.iloc[0] - 1
    years = len(cash) / 252
    return (1 + total) ** (1 / years) - 1 if years > 0 else 0.0
