"""Per-symbol transaction fee lookup for backtest simulation."""

from __future__ import annotations

from quadbalance.config import (
    CASH_SYMBOL,
    GOLD_SYMBOL,
    QDII_SYMBOL,
    STOCK_SUB_WEIGHTS,
)
from quadbalance.instrument_pool import ALL_INSTRUMENTS, TradeFees

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
    """Return redemption fee rate (decimal) for symbol. v1: always 0% for long-hold."""
    return _trade_fees(symbol).redemption_rate


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
        "v1 simulation uses static per-symbol purchase fees (1-discount platform rates). "
        "Redemption fees are modeled as 0% (assumes holdings exceed short-term penalty windows "
        "at annual rebalance). Management fees are embedded in NAV.",
        "",
        "| Code | Name | Purchase | Redemption (v1) |",
        "|------|------|----------|-----------------|",
    ]
    for code, name, purchase, redemption in primary_fee_rows():
        lines.append(
            f"| {code} | {name} | {purchase:.2%} | {redemption:.2%} |"
        )
    lines.append("")
    return "\n".join(lines)
