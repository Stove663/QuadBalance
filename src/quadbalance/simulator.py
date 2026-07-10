"""Portfolio simulation: base position, DCA, annual rebalancing."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from quadbalance.config import (
    BASE_CAPITAL,
    CASH_SYMBOL,
    MONTHLY_CONTRIBUTION,
    QDII_SYMBOL,
    TRANSACTION_COST,
    Quadrant,
    StrategyConfig,
)


@dataclass
class SimulationResult:
    config_id: str
    daily_values: pd.Series
    annual_quadrant_returns: pd.DataFrame
    effective_start: str
    effective_end: str
    instrument_starts: dict[str, str]
    rebalance_events: list[str] = field(default_factory=list)


def _first_trading_days_per_month(index: pd.DatetimeIndex) -> set[pd.Timestamp]:
    df = pd.DataFrame(index=index)
    df["ym"] = index.to_period("M")
    return set(df.groupby("ym").apply(lambda g: g.index[0], include_groups=False))


def _first_trading_days_per_year(index: pd.DatetimeIndex) -> set[pd.Timestamp]:
    df = pd.DataFrame(index=index)
    df["year"] = index.year
    return set(df.groupby("year").apply(lambda g: g.index[0], include_groups=False))


def _buy(
    shares: dict[str, float],
    symbol: str,
    amount: float,
    price: float,
    cost_rate: float,
    premium: float = 0.0,
) -> float:
    """Buy with amount (currency). Returns unspent cash."""
    if amount <= 0 or price <= 0:
        return amount
    effective_price = price * (1 + premium) * (1 + cost_rate)
    buy_shares = amount / effective_price
    shares[symbol] = shares.get(symbol, 0.0) + buy_shares
    return 0.0


def _sell(
    shares: dict[str, float],
    symbol: str,
    amount: float,
    price: float,
    cost_rate: float,
) -> float:
    """Sell to raise target currency amount. Returns shortfall if insufficient."""
    if amount <= 0 or price <= 0:
        return 0.0
    effective_price = price * (1 - cost_rate)
    needed_shares = amount / effective_price
    available = shares.get(symbol, 0.0)
    if needed_shares <= available:
        shares[symbol] = available - needed_shares
        return 0.0
    # sell all available
    proceeds = available * effective_price
    shares[symbol] = 0.0
    return amount - proceeds


def _portfolio_value(shares: dict[str, float], day_prices: pd.Series) -> float:
    return sum(shares.get(s, 0.0) * day_prices[s] for s in day_prices.index if s in shares)


def _quadrant_values(
    shares: dict[str, float],
    day_prices: pd.Series,
    config: StrategyConfig,
) -> dict[Quadrant, float]:
    values: dict[Quadrant, float] = {"stocks": 0.0, "bonds": 0.0, "gold": 0.0, "cash": 0.0}
    for sym in config.symbols():
        q = config.quadrant_for_symbol(sym)
        values[q] += shares.get(sym, 0.0) * day_prices[sym]
    return values


def _allocate_to_quadrant(
    shares: dict[str, float],
    quadrant: Quadrant,
    amount: float,
    day_prices: pd.Series,
    config: StrategyConfig,
    cost_rate: float,
) -> None:
    if amount <= 0:
        return
    symbols = [s for s in config.symbols() if config.quadrant_for_symbol(s) == quadrant]
    for sym in symbols:
        sub = config.sub_weight(sym)
        total_sub = sum(config.sub_weight(s) for s in symbols)
        portion = amount * (sub / total_sub) if total_sub else 0.0
        premium = config.qdii_premium if sym == QDII_SYMBOL else 0.0
        _buy(shares, sym, portion, day_prices[sym], cost_rate, premium)


def _proportional_contribution(
    shares: dict[str, float],
    amount: float,
    day_prices: pd.Series,
    config: StrategyConfig,
    cost_rate: float,
) -> None:
    for sym, weight in config.instrument_weights().items():
        if sym not in day_prices.index:
            continue
        premium = config.qdii_premium if sym == QDII_SYMBOL else 0.0
        _buy(shares, sym, amount * weight, day_prices[sym], cost_rate, premium)


def _underweight_contribution(
    shares: dict[str, float],
    amount: float,
    day_prices: pd.Series,
    config: StrategyConfig,
    cost_rate: float,
) -> None:
    total = _portfolio_value(shares, day_prices)
    if total <= 0:
        _proportional_contribution(shares, amount, day_prices, config, cost_rate)
        return
    q_values = _quadrant_values(shares, day_prices, config)
    targets = config.quadrant_weights
    # most underweight = lowest (actual - target)
    deviations = {q: q_values[q] / total - targets[q] for q in targets}
    worst = min(deviations, key=deviations.get)  # type: ignore[arg-type]
    _allocate_to_quadrant(shares, worst, amount, day_prices, config, cost_rate)


def _rebalance(
    shares: dict[str, float],
    day_prices: pd.Series,
    config: StrategyConfig,
    cost_rate: float,
    extra_cash: float = 0.0,
) -> None:
    total = _portfolio_value(shares, day_prices) + extra_cash
    if total <= 0:
        return
    target_weights = config.instrument_weights()

    # sell overweight
    for sym, target_w in target_weights.items():
        if sym not in day_prices.index:
            continue
        current = shares.get(sym, 0.0) * day_prices[sym]
        target_val = total * target_w
        if current > target_val:
            _sell(shares, sym, current - target_val, day_prices[sym], cost_rate)

    total = _portfolio_value(shares, day_prices) + extra_cash
    # buy underweight
    for sym, target_w in target_weights.items():
        if sym not in day_prices.index:
            continue
        current = shares.get(sym, 0.0) * day_prices[sym]
        target_val = total * target_w
        if current < target_val:
            premium = config.qdii_premium if sym == QDII_SYMBOL else 0.0
            _buy(shares, sym, target_val - current, day_prices[sym], cost_rate, premium)


def simulate(
    prices: pd.DataFrame,
    config: StrategyConfig,
    base_capital: float = BASE_CAPITAL,
    monthly_contribution: float = MONTHLY_CONTRIBUTION,
    cost_rate: float = TRANSACTION_COST,
    enable_rebalance: bool = True,
) -> SimulationResult:
    """Run full backtest simulation."""
    symbols = config.symbols()
    available = [s for s in symbols if s in prices.columns]
    sim_prices = prices[available].dropna(how="any")
    if sim_prices.empty:
        raise ValueError("No overlapping price data for configured symbols")

    effective_start = sim_prices.index[0]
    month_starts = _first_trading_days_per_month(sim_prices.index)
    year_starts = _first_trading_days_per_year(sim_prices.index)

    shares: dict[str, float] = {s: 0.0 for s in available}
    values: list[float] = []
    dates: list[pd.Timestamp] = []
    rebalance_events: list[str] = []

    for i, (dt, day_prices) in enumerate(sim_prices.iterrows()):
        if i == 0:
            _proportional_contribution(shares, base_capital, day_prices, config, cost_rate)
        else:
            if dt in month_starts:
                if config.dca_method == "proportional":
                    _proportional_contribution(
                        shares, monthly_contribution, day_prices, config, cost_rate
                    )
                else:
                    _underweight_contribution(
                        shares, monthly_contribution, day_prices, config, cost_rate
                    )

            if enable_rebalance and dt in year_starts and i > 0:
                total = _portfolio_value(shares, day_prices)
                q_vals = _quadrant_values(shares, day_prices, config)
                targets = config.quadrant_weights
                triggered = any(
                    abs(q_vals[q] / total - targets[q]) > config.rebalance_threshold
                    for q in targets
                    if total > 0
                )
                if triggered:
                    extra = monthly_contribution if dt in month_starts else 0.0
                    if extra and config.dca_method == "underweight":
                        _underweight_contribution(
                            shares, extra, day_prices, config, cost_rate
                        )
                        extra = 0.0
                    elif extra:
                        _proportional_contribution(
                            shares, extra, day_prices, config, cost_rate
                        )
                        extra = 0.0
                    _rebalance(shares, day_prices, config, cost_rate, extra)
                    rebalance_events.append(dt.strftime("%Y-%m-%d"))

        values.append(_portfolio_value(shares, day_prices))
        dates.append(dt)

    daily_values = pd.Series(values, index=pd.DatetimeIndex(dates), name="portfolio_value")
    annual_quadrant = _compute_annual_quadrant_returns(sim_prices, config)

    instrument_starts = {
        s: sim_prices[s].first_valid_index().strftime("%Y-%m-%d") for s in available
    }

    return SimulationResult(
        config_id=config.config_id,
        daily_values=daily_values,
        annual_quadrant_returns=annual_quadrant,
        effective_start=effective_start.strftime("%Y-%m-%d"),
        effective_end=daily_values.index[-1].strftime("%Y-%m-%d"),
        instrument_starts=instrument_starts,
        rebalance_events=rebalance_events,
    )


def _compute_annual_quadrant_returns(
    prices: pd.DataFrame, config: StrategyConfig
) -> pd.DataFrame:
    """Buy-and-hold annual return per quadrant (for reporting)."""
    years = sorted(set(prices.index.year))
    rows: list[dict[str, float | int]] = []

    for year in years:
        mask = prices.index.year == year
        year_prices = prices.loc[mask]
        if len(year_prices) < 2:
            continue
        row: dict[str, float | int] = {"year": year}
        for q in ("stocks", "bonds", "gold", "cash"):
            syms = [s for s in config.symbols() if config.quadrant_for_symbol(s) == q]
            if not syms:
                row[q] = 0.0
                continue
            start_p = year_prices[syms].iloc[0].mean()
            end_p = year_prices[syms].iloc[-1].mean()
            row[q] = (end_p / start_p - 1) if start_p else 0.0
        rows.append(row)

    return pd.DataFrame(rows).set_index("year")
