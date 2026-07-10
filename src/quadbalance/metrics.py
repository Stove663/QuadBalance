"""Performance metrics calculation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quadbalance.config import CASH_SYMBOL, StrategyConfig
from quadbalance.simulator import SimulationResult, simulate


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


def compute_metrics(
    result: SimulationResult,
    config: StrategyConfig,
    prices: pd.DataFrame,
    risk_free_annual: float,
    no_rebalance_result: SimulationResult | None = None,
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
    )


def cash_risk_free_rate(prices: pd.DataFrame) -> float:
    """Annualized return of cash instrument as risk-free proxy."""
    cash = prices[CASH_SYMBOL].dropna()
    if len(cash) < 2:
        return 0.02
    total = cash.iloc[-1] / cash.iloc[0] - 1
    years = len(cash) / 252
    return (1 + total) ** (1 / years) - 1 if years > 0 else 0.0
