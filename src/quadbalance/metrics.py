"""Performance metrics calculation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quadbalance.config import CASH_SYMBOL, StrategyConfig
from quadbalance.simulator import SimulationResult, simulate


@dataclass
class ProfileSuitability:
    profile_id: str
    classification: str
    reasons: list[str]


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


def classify_suitability(
    config: StrategyConfig,
    metrics: PerformanceMetrics,
    qdii_fill_rate: float,
    avg_qdii_weight_gap: float,
) -> dict[str, ProfileSuitability]:
    profiles: dict[str, ProfileSuitability] = {}

    accumulation_reasons: list[str] = []
    if metrics.real_annualized_return > 0:
        accumulation_reasons.append("positive real annualized return")
    if metrics.annualized_return < 0.06:
        accumulation_reasons.append("modest nominal growth may be too defensive for accumulation")
    if metrics.worst_rolling_5y_real_return < 0:
        accumulation_reasons.append("5-year rolling real return can fall below zero")
    if qdii_fill_rate < 0.9 or avg_qdii_weight_gap < -0.02:
        accumulation_reasons.append("QDII execution friction reduces global equity exposure")
    accumulation_class = "suitable" if metrics.real_annualized_return > 0.02 and metrics.max_drawdown > -0.25 else "caution"
    if metrics.worst_rolling_5y_real_return < -0.10:
        accumulation_class = "unsuitable"
    profiles["accumulation"] = ProfileSuitability("accumulation", accumulation_class, accumulation_reasons)

    balanced_reasons = []
    if metrics.max_drawdown > -0.25:
        balanced_reasons.append("drawdown within moderate tolerance")
    if metrics.real_annualized_return > 0:
        balanced_reasons.append("preserves purchasing power on average")
    balanced_class = "suitable" if metrics.max_drawdown >= -0.25 and metrics.worst_rolling_5y_real_return > -0.10 else "caution"
    profiles["balanced_core"] = ProfileSuitability("balanced_core", balanced_class, balanced_reasons)

    pre_retire_reasons = []
    if metrics.longest_underwater_days > 252 * 3:
        pre_retire_reasons.append("extended underwater duration is risky near retirement")
    if qdii_fill_rate < 0.75:
        pre_retire_reasons.append("execution friction can worsen liquidity planning")
    pre_retire_class = "unsuitable" if metrics.max_drawdown < -0.30 or metrics.longest_underwater_days > 252 * 5 else "caution"
    profiles["pre_retirement_preservation"] = ProfileSuitability("pre_retirement_preservation", pre_retire_class, pre_retire_reasons)

    retirement_reasons = []
    if metrics.worst_rolling_5y_real_return < -0.10:
        retirement_reasons.append("5-year real return breach threatens purchasing power")
    if metrics.longest_underwater_days > 252 * 5:
        retirement_reasons.append("underwater duration too long for withdrawal phase")
    retirement_class = "unsuitable" if metrics.real_terminal_wealth <= 0 or metrics.max_drawdown < -0.30 else "caution"
    profiles["retirement_withdrawal"] = ProfileSuitability("retirement_withdrawal", retirement_class, retirement_reasons)

    return profiles


def cash_risk_free_rate(prices: pd.DataFrame) -> float:
    """Annualized return of cash instrument as risk-free proxy."""
    cash = prices[CASH_SYMBOL].dropna()
    if len(cash) < 2:
        return 0.02
    total = cash.iloc[-1] / cash.iloc[0] - 1
    years = len(cash) / 252
    return (1 + total) ** (1 / years) - 1 if years > 0 else 0.0
