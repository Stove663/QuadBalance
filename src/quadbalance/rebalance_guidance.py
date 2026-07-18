"""Threshold-gated rebalance guidance from ledger vs active lock."""

from __future__ import annotations

from dataclasses import dataclass, field

from quadbalance.asset_universe import CASH_SYMBOL, Quadrant
from quadbalance.config import StrategyConfig
from quadbalance.lock_registry import StrategyLock


@dataclass(frozen=True)
class TradeLeg:
    side: str  # buy | sell
    symbol: str
    amount: float
    approx_shares: float | None
    note: str = ""


@dataclass(frozen=True)
class GuidanceResult:
    alert: bool
    reasons: list[str] = field(default_factory=list)
    quadrant_drift: dict[str, float] = field(default_factory=dict)
    legs: list[TradeLeg] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    incomplete: bool = False
    missing_prices: list[str] = field(default_factory=list)


def _quadrant_for_symbol(symbol: str, config_like: dict) -> Quadrant | None:
    # Use instrument weights keys and known universe mapping via StrategyConfig helpers when possible.
    from quadbalance.asset_universe import BOND_VARIANTS, DOMESTIC_STOCK_SYMBOL, GOLD_SYMBOL, QDII_SYMBOL

    if symbol in {DOMESTIC_STOCK_SYMBOL, QDII_SYMBOL} or symbol.startswith("11") and symbol != CASH_SYMBOL:
        if symbol in {DOMESTIC_STOCK_SYMBOL, QDII_SYMBOL}:
            return "stocks"
    if symbol == GOLD_SYMBOL:
        return "gold"
    if symbol == CASH_SYMBOL:
        return "cash"
    for variant in BOND_VARIANTS.values():
        if symbol in variant:
            return "bonds"
    # Fallback: look at locked instrument list membership only
    iw = config_like.get("instrument_weights") or {}
    if symbol in iw:
        # Unknown sleeve — attribute by largest quadrant weight presence is weak; use stocks default for QDII backups
        from quadbalance.asset_universe import QDII_BACKUP_SYMBOLS

        if symbol in QDII_BACKUP_SYMBOLS:
            return "stocks"
    return None


def material_idle_cash(settlement_cash: float, total_value: float) -> bool:
    threshold = max(0.01 * total_value, 1000.0)
    return settlement_cash > threshold


def compute_guidance(
    *,
    lock: StrategyLock | None,
    shares: dict[str, float],
    settlement_cash: float,
    prices: dict[str, float],
    qdii_symbols: set[str] | None = None,
) -> GuidanceResult:
    if lock is None:
        return GuidanceResult(alert=False, reasons=["No active strategy lock"])

    snap = lock.snapshot
    target_q = snap.get("quadrant_weights") or {}
    instrument_weights: dict[str, float] = dict(snap.get("instrument_weights") or {})
    threshold = float(snap.get("rebalance_threshold", 0.05))
    qdii_symbols = qdii_symbols or set()

    missing = [s for s in shares if s not in prices or prices[s] <= 0]
    # Also need prices for underweight targets we might buy
    for s in instrument_weights:
        if s not in prices or prices[s] <= 0:
            if s not in missing:
                missing.append(s)
    if missing:
        return GuidanceResult(
            alert=False,
            incomplete=True,
            missing_prices=missing,
            reasons=["Missing mark prices"],
        )

    fund_value = sum(shares.get(s, 0.0) * prices[s] for s in shares)
    total = fund_value + settlement_cash
    if total <= 0:
        return GuidanceResult(alert=False, reasons=["Portfolio value is zero"])

    # Actual quadrant values
    actual_q_val = {"stocks": 0.0, "bonds": 0.0, "gold": 0.0, "cash": 0.0}
    for sym, qty in shares.items():
        q = _quadrant_for_symbol(sym, snap)
        if q:
            actual_q_val[q] += qty * prices[sym]
    # Settlement cash counts toward total but not cash-sleeve fulfillment
    actual_q = {q: actual_q_val[q] / total for q in actual_q_val}
    drift = {q: actual_q.get(q, 0.0) - float(target_q.get(q, 0.0)) for q in ("stocks", "bonds", "gold", "cash")}

    over_threshold = any(abs(d) > threshold + 1e-12 for d in drift.values())
    cash_sleeve_target = float(instrument_weights.get(CASH_SYMBOL, target_q.get("cash", 0.0)))
    cash_sleeve_actual = (shares.get(CASH_SYMBOL, 0.0) * prices.get(CASH_SYMBOL, 0.0)) / total
    idle = material_idle_cash(settlement_cash, total) and cash_sleeve_actual + 1e-12 < cash_sleeve_target

    if not over_threshold and not idle:
        return GuidanceResult(alert=False, quadrant_drift=drift, reasons=["Within threshold"])

    reasons: list[str] = []
    if over_threshold:
        reasons.append("Quadrant drift exceeds rebalance threshold")
    if idle:
        reasons.append("Material idle settlement cash with underweight cash sleeve")

    # Instrument targets
    target_val = {s: total * w for s, w in instrument_weights.items()}
    current_val = {s: shares.get(s, 0.0) * prices[s] for s in set(shares) | set(instrument_weights)}

    legs: list[TradeLeg] = []
    warnings: list[str] = []
    cash = settlement_cash

    # 1) Deploy settlement cash — prioritize cash sleeve if underweight
    buy_needs: list[tuple[str, float]] = []
    for sym, tv in target_val.items():
        gap = tv - current_val.get(sym, 0.0)
        if gap > 1e-6:
            buy_needs.append((sym, gap))
    buy_needs.sort(key=lambda x: (0 if x[0] == CASH_SYMBOL else 1, -x[1]))

    if cash > 1e-6 and buy_needs:
        # First fill cash sleeve if underweight
        for sym, need in buy_needs:
            if cash <= 1e-6:
                break
            if idle and sym != CASH_SYMBOL and any(s == CASH_SYMBOL for s, _ in buy_needs):
                # still allow others after cash sleeve prioritized via sort
                pass
            take = min(cash, need)
            if take <= 0:
                continue
            px = prices[sym]
            legs.append(TradeLeg("buy", sym, take, take / px, "settlement cash"))
            cash -= take
            current_val[sym] = current_val.get(sym, 0.0) + take
            if sym in qdii_symbols:
                warnings.append(f"QDII buy {sym}: check daily quota / access")

    # Refresh buy/sell needs after cash deployment
    overweight = []
    underweight = []
    for sym, tv in target_val.items():
        gap = current_val.get(sym, 0.0) - tv
        if gap > 1e-6:
            overweight.append((sym, gap))
        elif gap < -1e-6:
            underweight.append((sym, -gap))

    # Prefer non-QDII sells first
    overweight.sort(key=lambda x: (1 if x[0] in qdii_symbols else 0, -x[1]))
    total_over = sum(g for _, g in overweight) or 1.0
    raised = 0.0
    sell_legs: list[TradeLeg] = []
    for sym, gap in overweight:
        # Pro-rata by overweight value (already the gap)
        sell_amt = gap
        px = prices[sym]
        sell_legs.append(TradeLeg("sell", sym, sell_amt, sell_amt / px, "overweight"))
        raised += sell_amt
        current_val[sym] = current_val.get(sym, 0.0) - sell_amt

    # Buys with raised cash
    underweight.sort(key=lambda x: -x[1])
    total_need = sum(n for _, n in underweight) or 1.0
    scale = min(1.0, raised / total_need) if total_need > 0 else 0.0
    buy_legs: list[TradeLeg] = []
    for sym, need in underweight:
        buy_amt = need * scale
        if buy_amt <= 1e-6:
            continue
        px = prices[sym]
        buy_legs.append(TradeLeg("buy", sym, buy_amt, buy_amt / px, "rebalance"))
        if sym in qdii_symbols:
            warnings.append(f"QDII buy {sym}: check daily quota / access")

    # If only idle-cash case and we already added cash-sleeve buy, may skip sells
    if idle and not over_threshold:
        legs = [L for L in legs if L.side == "buy"]
        return GuidanceResult(
            alert=True,
            reasons=reasons,
            quadrant_drift=drift,
            legs=legs,
            warnings=warnings,
        )

    legs = legs + sell_legs + buy_legs
    return GuidanceResult(
        alert=True,
        reasons=reasons,
        quadrant_drift=drift,
        legs=legs,
        warnings=list(dict.fromkeys(warnings)),
    )


def config_from_lock_snapshot(lock: StrategyLock) -> StrategyConfig:
    """Best-effort StrategyConfig rebuild from snapshot (for helpers)."""
    c = lock.snapshot.get("config") or {}
    return StrategyConfig(
        allocation_name=c.get("allocation_name", lock.config_id.split("_")[0]),
        stocks=float(c.get("stocks", 0.25)),
        bonds=float(c.get("bonds", 0.25)),
        gold=float(c.get("gold", 0.25)),
        cash=float(c.get("cash", 0.25)),
        bond_variant=c.get("bond_variant", "B1"),
        dca_method=c.get("dca_method", "proportional"),
        rebalance_threshold=float(c.get("rebalance_threshold", 0.05)),
        stock_sub_split=c.get("stock_sub_split", "60-40"),
        enable_qdii_quota=bool(c.get("enable_qdii_quota", True)),
        qdii_daily_caps=c.get("qdii_daily_caps"),
    )
