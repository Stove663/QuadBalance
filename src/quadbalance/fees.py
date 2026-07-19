"""Per-symbol transaction fee lookup for backtest simulation."""

from __future__ import annotations

from quadbalance.config import (
    CASH_SYMBOL,
    GOLD_SYMBOL,
    QDII_SYMBOL,
    STOCK_SUB_WEIGHTS,
)
from quadbalance.instrument_pool import ALL_INSTRUMENTS, TradeFees

SHORT_HOLD_DAYS = 7

# Symbols that may appear in simulation (primaries + QDII backups)
SIMULATION_SYMBOLS: frozenset[str] = frozenset(
    {
        *STOCK_SUB_WEIGHTS.keys(),
        "050025",
        "006075",
        "003358",
        "003327",
        GOLD_SYMBOL,
        CASH_SYMBOL,
    }
)


def purchase_fee_rate(symbol: str) -> float:
    """Return purchase fee rate (decimal) for symbol."""
    return _trade_fees(symbol).purchase_rate


def redemption_fee_rate(symbol: str) -> float:
    """Return short-hold redemption fee rate (decimal) for symbol."""
    return _trade_fees(symbol).redemption_rate


def short_hold_redemption_rate(symbol: str, holding_days: int) -> float:
    """Apply short-hold redemption only when lot age is below the window."""
    if holding_days < SHORT_HOLD_DAYS:
        return redemption_fee_rate(symbol)
    return 0.0


def _trade_fees(symbol: str) -> TradeFees:
    if symbol not in ALL_INSTRUMENTS:
        raise KeyError(f"No fee schedule for symbol {symbol}")
    return ALL_INSTRUMENTS[symbol].trade_fees


def primary_fee_rows() -> list[tuple[str, str, float, float]]:
    """Primary instruments and fee rates for strategy-lock reporting."""
    from quadbalance.instrument_pool import primary_instruments

    rows: list[tuple[str, str, float, float]] = []
    for inst in primary_instruments():
        rows.append(
            (inst.code, inst.name, inst.trade_fees.purchase_rate, inst.trade_fees.redemption_rate)
        )
    return rows


def format_fee_assumptions_markdown() -> str:
    """Transaction fee assumptions for strategy lock document."""
    lines = [
        "## Transaction Fee Assumptions",
        "",
        "Simulation uses static per-symbol purchase fees (1-discount platform rates). "
        f"Short-hold redemption applies when a sold FIFO lot is younger than {SHORT_HOLD_DAYS} days "
        "(equity/QDII/gold typically 0.50%, bonds 0.10%, money-market cash 0%). "
        "Seasoned lots incur 0% short-hold redemption. Management fees are embedded in NAV.",
        "",
        "| Code | Name | Purchase | Short-hold Redemption |",
        "|------|------|----------|------------------------|",
    ]
    for code, name, purchase, redemption in primary_fee_rows():
        lines.append(
            f"| {code} | {name} | {purchase:.2%} | {redemption:.2%} |"
        )
    lines.append("")
    return "\n".join(lines)
