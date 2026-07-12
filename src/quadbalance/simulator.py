"""Portfolio simulation: base position, DCA, annual rebalancing."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from quadbalance.asset_universe import BASE_CAPITAL, CASH_SYMBOL, MONTHLY_CONTRIBUTION, QDII_SYMBOL, Quadrant
from quadbalance.config import StrategyConfig
from quadbalance.fees import purchase_fee_rate, redemption_fee_rate
from quadbalance.instrument_pool import primary_qdii_handoff_date, qdii_pool_for_date


@dataclass(frozen=True)
class QdiiExecutionMetrics:
    qdii_fill_rate: float
    avg_pending_cash: float
    max_pending_cash: float
    pending_cash_days: int
    avg_qdii_weight_gap: float
    qdii_friction_months: int = 0
    qdii_recovery_months: int = 0


@dataclass(frozen=True)
class RebalanceShortfallEvent:
    date: str
    symbol: str
    requested_cny: float
    raised_cny: float
    shortfall_cny: float


@dataclass(frozen=True)
class RebalanceExecutionMetrics:
    shortfall_event_count: int
    total_shortfall_cny: float
    max_single_shortfall_cny: float
    max_post_rebalance_deviation: float


@dataclass
class SimulationResult:
    config_id: str
    daily_values: pd.Series
    annual_quadrant_returns: pd.DataFrame
    effective_start: str
    effective_end: str
    instrument_starts: dict[str, str]
    rebalance_events: list[str] = field(default_factory=list)
    pending_cash_series: pd.Series = field(default_factory=pd.Series)
    backup_events: list[str] = field(default_factory=list)
    qdii_metrics: QdiiExecutionMetrics | None = None
    rebalance_shortfalls: list[RebalanceShortfallEvent] = field(default_factory=list)
    rebalance_metrics: RebalanceExecutionMetrics | None = None


@dataclass
class LifecycleResult:
    scenario_id: str
    terminal_value: float
    real_terminal_value: float
    max_drawdown: float
    depleted: bool
    recovery_days: int


@dataclass
class _SimContext:
    qdii_backlog: float = 0.0
    quota_used: dict[str, float] = field(default_factory=dict)
    last_date: pd.Timestamp | None = None
    qdii_intended: float = 0.0
    qdii_executed: float = 0.0
    backlog_history: list[float] = field(default_factory=list)
    weight_gaps: list[float] = field(default_factory=list)
    backup_events: list[str] = field(default_factory=list)
    rebalance_shortfalls: list[RebalanceShortfallEvent] = field(default_factory=list)
    post_rebalance_deviations: list[float] = field(default_factory=list)
    qdii_friction_months: int = 0
    qdii_recovery_months: int = 0
    qdii_friction_streak: int = 0
    qdii_recovery_streak: int = 0


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
    premium: float = 0.0,
) -> float:
    if amount <= 0 or price <= 0:
        return amount
    effective_price = price * (1 + premium) * (1 + purchase_fee_rate(symbol))
    buy_shares = amount / effective_price
    shares[symbol] = shares.get(symbol, 0.0) + buy_shares
    return 0.0


def _sell(
    shares: dict[str, float],
    symbol: str,
    amount: float,
    price: float,
) -> float:
    if amount <= 0 or price <= 0:
        return 0.0
    effective_price = price * (1 - redemption_fee_rate(symbol))
    needed_shares = amount / effective_price
    available = shares.get(symbol, 0.0)
    if needed_shares <= available:
        shares[symbol] = available - needed_shares
        return 0.0
    proceeds = available * effective_price
    shares[symbol] = 0.0
    return amount - proceeds


def _merge_day_prices(core_row: pd.Series, backup_prices: dict[str, pd.Series] | None, dt: pd.Timestamp) -> pd.Series:
    merged = core_row.copy()
    if not backup_prices:
        return merged
    for sym, series in backup_prices.items():
        if dt in series.index:
            val = series.loc[dt]
            if pd.notna(val):
                merged[sym] = float(val)
    return merged


def _qdii_symbols_for_date(dt: pd.Timestamp, day_prices: pd.Series) -> list[str]:
    return [s for s in qdii_pool_for_date(dt) if s in day_prices.index and pd.notna(day_prices[s])]


def _is_proxy_era(dt: pd.Timestamp) -> bool:
    return dt < primary_qdii_handoff_date()


def _qdii_holdings_value(shares: dict[str, float], day_prices: pd.Series, dt: pd.Timestamp) -> float:
    return sum(shares.get(s, 0.0) * day_prices[s] for s in _qdii_symbols_for_date(dt, day_prices))


def _portfolio_value(shares: dict[str, float], day_prices: pd.Series, pending_cash: float = 0.0) -> float:
    holdings = sum(shares.get(s, 0.0) * day_prices[s] for s in day_prices.index if s in shares)
    return holdings + pending_cash


def _park_in_cash(shares: dict[str, float], amount: float, day_prices: pd.Series) -> None:
    if amount > 0 and CASH_SYMBOL in day_prices.index:
        _buy(shares, CASH_SYMBOL, amount, day_prices[CASH_SYMBOL])


def _cash_holding_value(shares: dict[str, float], day_prices: pd.Series) -> float:
    if CASH_SYMBOL not in day_prices.index:
        return 0.0
    return shares.get(CASH_SYMBOL, 0.0) * day_prices[CASH_SYMBOL]


def _quadrant_values(shares: dict[str, float], day_prices: pd.Series, config: StrategyConfig) -> dict[Quadrant, float]:
    values: dict[Quadrant, float] = {"stocks": 0.0, "bonds": 0.0, "gold": 0.0, "cash": 0.0}
    for sym in config.simulation_symbols():
        if sym not in day_prices.index:
            continue
        q = config.quadrant_for_symbol(sym)
        values[q] += shares.get(sym, 0.0) * day_prices[sym]
    return values


def _maybe_reset_quota(ctx: _SimContext, dt: pd.Timestamp) -> None:
    if ctx.last_date is None or dt.date() != ctx.last_date.date():
        ctx.quota_used = {}
    ctx.last_date = dt


def _remaining_quota(symbol: str, config: StrategyConfig, ctx: _SimContext) -> float:
    cap = config.qdii_daily_caps.get(symbol, 0.0)
    used = ctx.quota_used.get(symbol, 0.0)
    return max(0.0, cap - used)


def _buy_qdii_with_quota(shares: dict[str, float], amount: float, day_prices: pd.Series, config: StrategyConfig, ctx: _SimContext, dt: pd.Timestamp, *, count_intended: bool = True) -> float:
    if amount <= 0:
        return 0.0
    if count_intended:
        ctx.qdii_intended += amount
    if not config.enable_qdii_quota or _is_proxy_era(dt):
        if QDII_SYMBOL in day_prices.index:
            _buy(shares, QDII_SYMBOL, amount, day_prices[QDII_SYMBOL], config.qdii_premium)
            ctx.qdii_executed += amount
        return 0.0
    remainder = amount
    pool = _qdii_symbols_for_date(dt, day_prices)
    primary = QDII_SYMBOL
    for sym in pool:
        if remainder <= 0:
            break
        cap_left = _remaining_quota(sym, config, ctx)
        if cap_left <= 0:
            continue
        buy_amt = min(remainder, cap_left)
        premium = config.qdii_premium if sym == QDII_SYMBOL else 0.0
        _buy(shares, sym, buy_amt, day_prices[sym], premium)
        ctx.quota_used[sym] = ctx.quota_used.get(sym, 0.0) + buy_amt
        ctx.qdii_executed += buy_amt
        remainder -= buy_amt
        if sym != primary and buy_amt > 0:
            ctx.backup_events.append(f"{dt.strftime('%Y-%m-%d')}: {primary}→{sym} {buy_amt:.0f} CNY")
    return remainder


def _process_qdii_backlog(shares: dict[str, float], day_prices: pd.Series, config: StrategyConfig, ctx: _SimContext, dt: pd.Timestamp) -> None:
    if ctx.qdii_backlog <= 0:
        return
    cash_avail = _cash_holding_value(shares, day_prices)
    attempt = min(ctx.qdii_backlog, cash_avail)
    if attempt <= 0:
        return
    _sell(shares, CASH_SYMBOL, attempt, day_prices[CASH_SYMBOL])
    unfilled = _buy_qdii_with_quota(shares, attempt, day_prices, config, ctx, dt, count_intended=False)
    ctx.qdii_backlog = unfilled
    if unfilled > 0:
        _park_in_cash(shares, unfilled, day_prices)


def _handle_qdii_unfilled(shares: dict[str, float], unfilled: float, day_prices: pd.Series, ctx: _SimContext) -> None:
    if unfilled <= 0:
        return
    ctx.qdii_backlog += unfilled
    _park_in_cash(shares, unfilled, day_prices)


def _buy_instrument(shares: dict[str, float], symbol: str, amount: float, day_prices: pd.Series, config: StrategyConfig, ctx: _SimContext, dt: pd.Timestamp) -> None:
    if amount <= 0 or symbol not in day_prices.index:
        return
    if config.is_qdii_symbol(symbol):
        unfilled = _buy_qdii_with_quota(shares, amount, day_prices, config, ctx, dt)
        _handle_qdii_unfilled(shares, unfilled, day_prices, ctx)
        return
    _buy(shares, symbol, amount, day_prices[symbol], config.qdii_premium if symbol == QDII_SYMBOL else 0.0)


def _sell_qdii_pro_rata(shares: dict[str, float], amount: float, day_prices: pd.Series, config: StrategyConfig, dt: pd.Timestamp) -> tuple[float, list[RebalanceShortfallEvent]]:
    pool = _qdii_symbols_for_date(dt, day_prices)
    total = _qdii_holdings_value(shares, day_prices, dt)
    if total <= 0 or amount <= 0:
        return 0.0, []
    events: list[RebalanceShortfallEvent] = []
    total_raised = 0.0
    for sym in pool:
        holding = shares.get(sym, 0.0) * day_prices[sym]
        if holding <= 0:
            continue
        portion = amount * (holding / total)
        shortfall = _sell(shares, sym, portion, day_prices[sym])
        raised = portion - shortfall
        total_raised += raised
        if shortfall > 0:
            events.append(RebalanceShortfallEvent(dt.strftime("%Y-%m-%d"), sym, portion, raised, shortfall))
    return total_raised, events


def _allocate_to_quadrant(shares: dict[str, float], quadrant: Quadrant, amount: float, day_prices: pd.Series, config: StrategyConfig, ctx: _SimContext, dt: pd.Timestamp) -> None:
    if amount <= 0:
        return
    symbols = [s for s in config.symbols() if config.quadrant_for_symbol(s) == quadrant]
    for sym in symbols:
        sub = config.sub_weight(sym)
        total_sub = sum(config.sub_weight(s) for s in symbols)
        portion = amount * (sub / total_sub) if total_sub else 0.0
        _buy_instrument(shares, sym, portion, day_prices, config, ctx, dt)


def _proportional_contribution(shares: dict[str, float], amount: float, day_prices: pd.Series, config: StrategyConfig, ctx: _SimContext, dt: pd.Timestamp) -> None:
    for sym, weight in config.instrument_weights().items():
        _buy_instrument(shares, sym, amount * weight, day_prices, config, ctx, dt)


def _underweight_contribution(shares: dict[str, float], amount: float, day_prices: pd.Series, config: StrategyConfig, ctx: _SimContext, dt: pd.Timestamp) -> None:
    total = _portfolio_value(shares, day_prices)
    if total <= 0:
        _proportional_contribution(shares, amount, day_prices, config, ctx, dt)
        return
    q_values = _quadrant_values(shares, day_prices, config)
    targets = config.quadrant_weights
    deviations = {q: q_values[q] / total - targets[q] for q in targets}
    worst = min(deviations, key=deviations.get)
    _allocate_to_quadrant(shares, worst, amount, day_prices, config, ctx, dt)


def _max_quadrant_deviation(shares: dict[str, float], day_prices: pd.Series, config: StrategyConfig, pending_cash: float = 0.0) -> float:
    total = _portfolio_value(shares, day_prices, pending_cash)
    if total <= 0:
        return 0.0
    q_vals = _quadrant_values(shares, day_prices, config)
    targets = config.quadrant_weights
    return max(abs(q_vals[q] / total - targets[q]) for q in targets)


def _rebalance(shares: dict[str, float], day_prices: pd.Series, config: StrategyConfig, ctx: _SimContext, dt: pd.Timestamp, extra_cash: float = 0.0) -> None:
    total = _portfolio_value(shares, day_prices) + extra_cash
    if total <= 0:
        return
    target_weights = config.instrument_weights()
    qdii_target = config.qdii_target_weight()
    rebalance_cash = extra_cash

    for sym, target_w in target_weights.items():
        if sym not in day_prices.index or config.is_qdii_symbol(sym):
            continue
        current = shares.get(sym, 0.0) * day_prices[sym]
        target_val = total * target_w
        if current > target_val:
            sell_amt = current - target_val
            shortfall = _sell(shares, sym, sell_amt, day_prices[sym])
            raised = sell_amt - shortfall
            rebalance_cash += raised
            if shortfall > 0:
                ctx.rebalance_shortfalls.append(RebalanceShortfallEvent(dt.strftime("%Y-%m-%d"), sym, sell_amt, raised, shortfall))

    total = _portfolio_value(shares, day_prices) + rebalance_cash
    current_qdii = _qdii_holdings_value(shares, day_prices, dt)
    target_qdii = total * qdii_target
    if current_qdii > target_qdii:
        raised, events = _sell_qdii_pro_rata(shares, current_qdii - target_qdii, day_prices, config, dt)
        rebalance_cash += raised
        ctx.rebalance_shortfalls.extend(events)

    total = _portfolio_value(shares, day_prices) + rebalance_cash
    buy_needs: list[tuple[str, float]] = []
    for sym, target_w in target_weights.items():
        if sym not in day_prices.index or config.is_qdii_symbol(sym):
            continue
        current = shares.get(sym, 0.0) * day_prices[sym]
        target_val = total * target_w
        if current < target_val:
            buy_needs.append((sym, target_val - current))

    total_buy_need = sum(need for _, need in buy_needs)
    scale = min(1.0, rebalance_cash / total_buy_need) if total_buy_need > 0 else 0.0
    for sym, need in buy_needs:
        buy_amt = need * scale
        if buy_amt <= 0:
            continue
        rebalance_cash -= buy_amt
        _buy_instrument(shares, sym, buy_amt, day_prices, config, ctx, dt)

    total = _portfolio_value(shares, day_prices) + rebalance_cash
    current_qdii = _qdii_holdings_value(shares, day_prices, dt)
    target_qdii = total * qdii_target
    if current_qdii < target_qdii:
        buy_amt = min(target_qdii - current_qdii, rebalance_cash)
        if buy_amt > 0:
            rebalance_cash -= buy_amt
            unfilled = _buy_qdii_with_quota(shares, buy_amt, day_prices, config, ctx, dt)
            _handle_qdii_unfilled(shares, unfilled, day_prices, ctx)

    ctx.post_rebalance_deviations.append(_max_quadrant_deviation(shares, day_prices, config, ctx.qdii_backlog))


def _record_weight_gap(shares: dict[str, float], day_prices: pd.Series, config: StrategyConfig, ctx: _SimContext, dt: pd.Timestamp) -> None:
    total = _portfolio_value(shares, day_prices, ctx.qdii_backlog)
    if total <= 0:
        return
    actual = _qdii_holdings_value(shares, day_prices, dt) / total
    gap = actual - config.qdii_target_weight()
    ctx.weight_gaps.append(gap)
    if gap < -0.02:
        ctx.qdii_friction_streak += 1
    else:
        if ctx.qdii_friction_streak >= 12:
            ctx.qdii_friction_months = max(ctx.qdii_friction_months, ctx.qdii_friction_streak)
        ctx.qdii_friction_streak = 0
    if actual >= config.qdii_target_weight() * 0.5:
        if ctx.qdii_recovery_streak > 0 and ctx.qdii_recovery_streak >= 24:
            ctx.qdii_recovery_months = max(ctx.qdii_recovery_months, ctx.qdii_recovery_streak)
        ctx.qdii_recovery_streak = 0
    else:
        ctx.qdii_recovery_streak += 1


def _build_rebalance_metrics(ctx: _SimContext) -> RebalanceExecutionMetrics:
    shortfalls = ctx.rebalance_shortfalls
    total_shortfall = sum(e.shortfall_cny for e in shortfalls)
    max_single = max((e.shortfall_cny for e in shortfalls), default=0.0)
    max_dev = max(ctx.post_rebalance_deviations, default=0.0)
    return RebalanceExecutionMetrics(len(shortfalls), total_shortfall, max_single, max_dev)


def _build_qdii_metrics(ctx: _SimContext) -> QdiiExecutionMetrics:
    fill_rate = ctx.qdii_executed / ctx.qdii_intended if ctx.qdii_intended > 0 else 1.0
    pending = ctx.backlog_history
    return QdiiExecutionMetrics(
        fill_rate,
        float(sum(pending) / len(pending)) if pending else 0.0,
        float(max(pending)) if pending else 0.0,
        sum(1 for p in pending if p > 0),
        float(sum(ctx.weight_gaps) / len(ctx.weight_gaps)) if ctx.weight_gaps else 0.0,
        ctx.qdii_friction_months,
        ctx.qdii_recovery_months,
    )


def simulate(
    prices: pd.DataFrame,
    config: StrategyConfig,
    base_capital: float = BASE_CAPITAL,
    monthly_contribution: float = MONTHLY_CONTRIBUTION,
    enable_rebalance: bool = True,
    backup_prices: dict[str, pd.Series] | None = None,
) -> SimulationResult:
    core_symbols = [s for s in config.symbols() if s in prices.columns]
    sim_prices = prices[core_symbols].dropna(how="any")
    if sim_prices.empty:
        raise ValueError("No overlapping price data for configured symbols")

    tradable_symbols = set(core_symbols)
    if backup_prices:
        tradable_symbols.update(backup_prices.keys())

    effective_start = sim_prices.index[0]
    month_starts = _first_trading_days_per_month(sim_prices.index)
    year_starts = _first_trading_days_per_year(sim_prices.index)

    shares: dict[str, float] = {s: 0.0 for s in tradable_symbols}
    ctx = _SimContext()
    values: list[float] = []
    pending_series: list[float] = []
    dates: list[pd.Timestamp] = []
    rebalance_events: list[str] = []

    for i, (dt, core_row) in enumerate(sim_prices.iterrows()):
        day_prices = _merge_day_prices(core_row, backup_prices, dt)
        _maybe_reset_quota(ctx, dt)
        if i > 0:
            _process_qdii_backlog(shares, day_prices, config, ctx, dt)
        if i == 0:
            _proportional_contribution(shares, base_capital, day_prices, config, ctx, dt)
        else:
            if dt in month_starts:
                if config.dca_method == "proportional":
                    _proportional_contribution(shares, monthly_contribution, day_prices, config, ctx, dt)
                else:
                    _underweight_contribution(shares, monthly_contribution, day_prices, config, ctx, dt)
            if enable_rebalance and dt in year_starts and i > 0:
                total = _portfolio_value(shares, day_prices)
                q_vals = _quadrant_values(shares, day_prices, config)
                targets = config.quadrant_weights
                triggered = any(abs(q_vals[q] / total - targets[q]) > config.rebalance_threshold for q in targets if total > 0)
                if triggered:
                    extra = monthly_contribution if dt in month_starts else 0.0
                    if extra and config.dca_method == "underweight":
                        _underweight_contribution(shares, extra, day_prices, config, ctx, dt)
                        extra = 0.0
                    elif extra:
                        _proportional_contribution(shares, extra, day_prices, config, ctx, dt)
                        extra = 0.0
                    _rebalance(shares, day_prices, config, ctx, dt, extra)
                    rebalance_events.append(dt.strftime("%Y-%m-%d"))

        _record_weight_gap(shares, day_prices, config, ctx, dt)
        ctx.backlog_history.append(ctx.qdii_backlog)
        values.append(_portfolio_value(shares, day_prices))
        pending_series.append(ctx.qdii_backlog)
        dates.append(dt)

    daily_values = pd.Series(values, index=pd.DatetimeIndex(dates), name="portfolio_value")
    pending_cash_series = pd.Series(pending_series, index=pd.DatetimeIndex(dates), name="pending_cash")
    annual_quadrant = _compute_annual_quadrant_returns(sim_prices, config)
    instrument_starts = {s: sim_prices[s].first_valid_index().strftime("%Y-%m-%d") for s in core_symbols}

    if ctx.qdii_friction_streak >= 12:
        ctx.qdii_friction_months = max(ctx.qdii_friction_months, ctx.qdii_friction_streak)
    if ctx.qdii_recovery_streak >= 24:
        ctx.qdii_recovery_months = max(ctx.qdii_recovery_months, ctx.qdii_recovery_streak)

    return SimulationResult(
        config_id=config.config_id,
        daily_values=daily_values,
        annual_quadrant_returns=annual_quadrant,
        effective_start=effective_start.strftime("%Y-%m-%d"),
        effective_end=daily_values.index[-1].strftime("%Y-%m-%d"),
        instrument_starts=instrument_starts,
        rebalance_events=rebalance_events,
        pending_cash_series=pending_cash_series,
        backup_events=ctx.backup_events,
        qdii_metrics=_build_qdii_metrics(ctx),
        rebalance_shortfalls=list(ctx.rebalance_shortfalls),
        rebalance_metrics=_build_rebalance_metrics(ctx),
    )


def _longest_recovery_days(values: pd.Series) -> int:
    peak = values.iloc[0]
    peak_idx = values.index[0]
    longest = 0
    underwater_start: pd.Timestamp | None = None
    for dt, val in values.items():
        if val >= peak:
            if underwater_start is not None:
                longest = max(longest, (dt - underwater_start).days)
                underwater_start = None
            peak = val
            peak_idx = dt
        else:
            if underwater_start is None:
                underwater_start = peak_idx
    return longest


def simulate_lifecycle(
    prices: pd.DataFrame,
    config: StrategyConfig,
    scenario_id: str,
    withdrawal_rate: float = 0.0,
    interrupt_months: int = 0,
    withdrawal_mode: str = "end",
) -> LifecycleResult:
    base = simulate(prices, config)
    lifecycle = base.daily_values.copy()
    month_periods = lifecycle.index.to_period("M")
    months = sorted(month_periods.unique())
    interrupted = set(months[:interrupt_months]) if interrupt_months > 0 else set()

    if interrupted:
        lifecycle.loc[month_periods.isin(interrupted)] = 0.0

    if scenario_id == "one_time_liquidity_20pct" and len(lifecycle) > 0:
        drawdown_floor = lifecycle.cummax() * 0.8
        drawdown_mask = lifecycle < lifecycle.cummax()
        if drawdown_mask.any():
            trigger_idx = lifecycle[drawdown_mask].index[0]
        else:
            trigger_idx = lifecycle.index[len(lifecycle) // 2]
        lifecycle.loc[trigger_idx:] = lifecycle.loc[trigger_idx:] * 0.8

    if withdrawal_rate > 0:
        if withdrawal_mode == "annual":
            years = sorted(set(lifecycle.index.year))
            if scenario_id == "bear_market_retirement_start" and years:
                worst_year = min(
                    years,
                    key=lambda y: float(
                        lifecycle[lifecycle.index.year == y].iloc[-1]
                        / lifecycle[lifecycle.index.year == y].iloc[0]
                        - 1
                    ),
                )
                years = [y for y in years if y >= worst_year]
            for year in years:
                mask = lifecycle.index.year == year
                values = lifecycle.loc[mask]
                if len(values) == 0:
                    continue
                peak = values.cummax()
                floor = peak * (1 - withdrawal_rate)
                lifecycle.loc[mask] = values.clip(lower=floor)
        else:
            lifecycle = lifecycle * max(0.0, 1.0 - withdrawal_rate)

    peak = lifecycle.cummax()
    dd = lifecycle / peak - 1
    depleted = bool((lifecycle <= 0).any())
    recovery_days = _longest_recovery_days(lifecycle)
    real_terminal_value = float(lifecycle.iloc[-1] / max(peak.iloc[-1], 1.0))
    return LifecycleResult(
        scenario_id=scenario_id,
        terminal_value=float(lifecycle.iloc[-1]),
        real_terminal_value=real_terminal_value,
        max_drawdown=float(dd.min()),
        depleted=depleted,
        recovery_days=recovery_days,
    )


def _compute_annual_quadrant_returns(prices: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
    years = sorted(set(prices.index.year))
    rows: list[dict[str, float | int]] = []
    for year in years:
        mask = prices.index.year == year
        year_prices = prices.loc[mask]
        if len(year_prices) < 2:
            continue
        row: dict[str, float | int] = {"year": year}
        for q in ("stocks", "bonds", "gold", "cash"):
            syms = [s for s in config.simulation_symbols() if config.quadrant_for_symbol(s) == q and s in year_prices.columns]
            if not syms:
                row[q] = 0.0
                continue
            start_p = year_prices[syms].iloc[0].mean()
            end_p = year_prices[syms].iloc[-1].mean()
            row[q] = (end_p / start_p - 1) if start_p else 0.0
        rows.append(row)
    return pd.DataFrame(rows).set_index("year")
