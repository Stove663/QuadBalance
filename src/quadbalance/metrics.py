"""Performance metrics calculation."""

from __future__ import annotations

from dataclasses import dataclass
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
    real_annualized_return: float = 0.0
    real_terminal_wealth: float = 0.0
    worst_rolling_1y_return: float = 0.0
    worst_rolling_3y_return: float = 0.0
    worst_rolling_5y_return: float = 0.0
    worst_rolling_1y_real_return: float = 0.0
    worst_rolling_3y_real_return: float = 0.0
    worst_rolling_5y_real_return: float = 0.0
    longest_underwater_days: int = 0


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


def compute_metrics(
    result: SimulationResult,
    config: StrategyConfig,
    prices: pd.DataFrame,
    risk_free_annual: float,
    no_rebalance_result: SimulationResult | None = None,
    inflation_annual: float = 0.03,
) -> PerformanceMetrics:
    daily = result.daily_values
    daily_returns = daily.pct_change().dropna()
    trading_days = len(daily)
    years = trading_days / 252

    total_return = daily.iloc[-1] / daily.iloc[0] - 1
    ann_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0
    ann_vol = float(daily_returns.std() * np.sqrt(252)) if len(daily_returns) else 0.0
    mdd, peak, trough = _max_drawdown(daily)
    sharpe = (ann_return - risk_free_annual) / ann_vol if ann_vol > 0 else 0.0

    annual_rets = _annual_returns(daily)
    positive_pct = float((annual_rets > 0).mean()) if len(annual_rets) else 0.0
    worst_year = float(annual_rets.min()) if len(annual_rets) else 0.0

    rebalance_premium = 0.0
    if no_rebalance_result is not None:
        nr = no_rebalance_result.daily_values
        nr_total = nr.iloc[-1] / nr.iloc[0] - 1
        nr_years = len(nr) / 252
        nr_ann = (1 + nr_total) ** (1 / nr_years) - 1 if nr_years > 0 else 0.0
        rebalance_premium = ann_return - nr_ann

    real_factor = (1.0 + inflation_annual) ** years if years > 0 else 1.0
    real_terminal = daily.iloc[-1] / real_factor if real_factor > 0 else daily.iloc[-1]
    real_ann_return = ((1 + ann_return) / (1 + inflation_annual) - 1) if inflation_annual > -1 else ann_return

    return PerformanceMetrics(
        annualized_return=ann_return,
        annualized_volatility=ann_vol,
        max_drawdown=mdd,
        max_drawdown_peak=peak,
        max_drawdown_trough=trough,
        sharpe_ratio=sharpe,
        positive_years_pct=positive_pct,
        rebalance_premium=rebalance_premium,
        worst_year_return=worst_year,
        annual_returns=annual_rets,
        real_annualized_return=real_ann_return,
        real_terminal_wealth=real_terminal,
        worst_rolling_1y_return=_worst_rolling_return(daily, 252),
        worst_rolling_3y_return=_worst_rolling_return(daily, 252 * 3),
        worst_rolling_5y_return=_worst_rolling_return(daily, 252 * 5),
        worst_rolling_1y_real_return=_worst_rolling_return(daily, 252),
        worst_rolling_3y_real_return=_worst_rolling_return(daily, 252 * 3),
        worst_rolling_5y_real_return=_worst_rolling_return(daily, 252 * 5),
        longest_underwater_days=_longest_underwater_days(daily),
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
) -> dict[str, ProfileSuitability]:
    profiles: dict[str, ProfileSuitability] = {}
    qdii_reasons, qdii_warnings = _qdii_notes(qdii_fill_rate, avg_qdii_weight_gap, qdii_friction_months, qdii_recovery_months)

    for profile in investor_profiles:
        if profile.profile_id == "accumulation":
            profiles[profile.profile_id] = _classify_accumulation(metrics, qdii_reasons, qdii_warnings, profile)
        elif profile.profile_id == "balanced_core":
            profiles[profile.profile_id] = _classify_balanced(metrics, qdii_reasons, qdii_warnings, profile)
        elif profile.profile_id == "pre_retirement_preservation":
            profiles[profile.profile_id] = _classify_preservation(metrics, qdii_fill_rate, qdii_warnings, profile)
        else:
            profiles[profile.profile_id] = _classify_retirement(metrics, profile)

    return profiles


def cash_risk_free_rate(prices: pd.DataFrame) -> float:
    """Annualized return of cash instrument as risk-free proxy."""
    cash = prices[CASH_SYMBOL].dropna()
    if len(cash) < 2:
        return 0.02
    total = cash.iloc[-1] / cash.iloc[0] - 1
    years = len(cash) / 252
    return (1 + total) ** (1 / years) - 1 if years > 0 else 0.0
