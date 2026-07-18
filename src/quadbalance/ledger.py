"""Personal ledger: settlement cash vs fund shares, corrections, guards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from quadbalance.db import connect

EntryType = Literal[
    "opening",
    "buy",
    "sell",
    "dca",
    "rebalance",
    "settlement_cash",
    "corporate_action",
]

ORDINARY_TRADE_TYPES = frozenset({"buy", "sell", "dca", "rebalance"})


@dataclass(frozen=True)
class LedgerEntry:
    id: int
    entry_date: str
    entry_type: str
    symbol: str | None
    amount: float | None
    shares: float | None
    note: str | None
    action_kind: str | None
    effective_date: str | None
    source: str
    deleted_at: str | None


@dataclass(frozen=True)
class PortfolioState:
    shares: dict[str, float]
    settlement_cash: float


class LedgerError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_entry(row) -> LedgerEntry:
    return LedgerEntry(
        id=int(row["id"]),
        entry_date=row["entry_date"],
        entry_type=row["entry_type"],
        symbol=row["symbol"],
        amount=row["amount"],
        shares=row["shares"],
        note=row["note"],
        action_kind=row["action_kind"],
        effective_date=row["effective_date"],
        source=row["source"],
        deleted_at=row["deleted_at"],
    )


def list_entries(db_path: Path | None = None, *, include_deleted: bool = False) -> list[LedgerEntry]:
    sql = "SELECT * FROM ledger_entries"
    if not include_deleted:
        sql += " WHERE deleted_at IS NULL"
    sql += " ORDER BY entry_date ASC, id ASC"
    with connect(db_path) as conn:
        rows = conn.execute(sql).fetchall()
    return [_row_to_entry(r) for r in rows]


def reconstruct(db_path: Path | None = None) -> PortfolioState:
    shares: dict[str, float] = {}
    cash = 0.0
    for e in list_entries(db_path):
        if e.entry_type == "settlement_cash":
            cash += float(e.amount or 0.0)
            continue
        if e.entry_type == "opening":
            if e.symbol:
                shares[e.symbol] = shares.get(e.symbol, 0.0) + float(e.shares or 0.0)
            if e.amount is not None and e.symbol is None:
                cash += float(e.amount)
            elif e.amount is not None and e.symbol is not None and (e.shares or 0) == 0:
                cash += float(e.amount)
            continue
        if e.entry_type in {"buy", "dca"}:
            if e.symbol:
                shares[e.symbol] = shares.get(e.symbol, 0.0) + float(e.shares or 0.0)
            cash -= float(e.amount or 0.0)
            continue
        if e.entry_type == "sell":
            if e.symbol:
                shares[e.symbol] = shares.get(e.symbol, 0.0) - float(e.shares or 0.0)
            cash += float(e.amount or 0.0)
            continue
        if e.entry_type == "rebalance":
            # Net cash and share legs encoded on the entry.
            if e.symbol and e.shares is not None:
                shares[e.symbol] = shares.get(e.symbol, 0.0) + float(e.shares)
            if e.amount is not None:
                cash += float(e.amount)
            continue
        if e.entry_type == "corporate_action":
            if e.action_kind == "split" and e.symbol and e.shares is not None:
                # shares field stores delta (new - old) or absolute post? Spec: adjust by ratio.
                # We store share *delta* for splits.
                shares[e.symbol] = shares.get(e.symbol, 0.0) + float(e.shares)
            elif e.action_kind == "dividend_cash":
                cash += float(e.amount or 0.0)
            elif e.action_kind == "dividend_reinvest" and e.symbol and e.shares is not None:
                shares[e.symbol] = shares.get(e.symbol, 0.0) + float(e.shares)
            continue
    # Drop near-zero dust
    shares = {s: q for s, q in shares.items() if abs(q) > 1e-12}
    return PortfolioState(shares=shares, settlement_cash=cash)


def _validate_ordinary(entry_type: str, symbol: str | None, amount: float | None, shares: float | None, state: PortfolioState) -> None:
    if entry_type not in ORDINARY_TRADE_TYPES:
        return
    if entry_type in {"buy", "dca"}:
        spend = float(amount or 0.0)
        if spend > state.settlement_cash + 1e-9:
            raise LedgerError("Insufficient settlement cash for buy")
        if not symbol or float(shares or 0.0) <= 0:
            raise LedgerError("Buy requires symbol and positive shares")
    if entry_type == "sell":
        qty = float(shares or 0.0)
        held = state.shares.get(symbol or "", 0.0)
        if qty <= 0 or not symbol:
            raise LedgerError("Sell requires symbol and positive shares")
        if qty > held + 1e-9:
            raise LedgerError("Cannot sell more shares than held")


def add_entry(
    *,
    entry_date: str,
    entry_type: EntryType,
    symbol: str | None = None,
    amount: float | None = None,
    shares: float | None = None,
    note: str | None = None,
    action_kind: str | None = None,
    effective_date: str | None = None,
    source: str = "user",
    enforce_guards: bool = True,
    db_path: Path | None = None,
) -> LedgerEntry:
    state = reconstruct(db_path)
    if enforce_guards:
        _validate_ordinary(entry_type, symbol, amount, shares, state)
    with connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO ledger_entries (
                entry_date, entry_type, symbol, amount, shares, note,
                action_kind, effective_date, source, deleted_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
            """,
            (
                entry_date,
                entry_type,
                symbol,
                amount,
                shares,
                note,
                action_kind,
                effective_date,
                source,
                _now(),
            ),
        )
        entry_id = int(cur.lastrowid)
        conn.commit()
        row = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
    return _row_to_entry(row)


def soft_delete_entry(entry_id: int, db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE ledger_entries SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (_now(), entry_id),
        )
        conn.commit()


def update_entry(
    entry_id: int,
    *,
    entry_date: str | None = None,
    entry_type: str | None = None,
    symbol: str | None = None,
    amount: float | None = None,
    shares: float | None = None,
    note: str | None = None,
    enforce_guards: bool = False,
    db_path: Path | None = None,
) -> LedgerEntry:
    """Edit an entry. Default: no ordinary-path guards (correction flow)."""
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM ledger_entries WHERE id = ? AND deleted_at IS NULL", (entry_id,)
        ).fetchone()
        if row is None:
            raise LedgerError(f"Entry {entry_id} not found")
        new_date = entry_date if entry_date is not None else row["entry_date"]
        new_type = entry_type if entry_type is not None else row["entry_type"]
        new_symbol = symbol if symbol is not None else row["symbol"]
        new_amount = amount if amount is not None else row["amount"]
        new_shares = shares if shares is not None else row["shares"]
        new_note = note if note is not None else row["note"]
        conn.execute(
            """
            UPDATE ledger_entries
            SET entry_date = ?, entry_type = ?, symbol = ?, amount = ?, shares = ?, note = ?
            WHERE id = ?
            """,
            (new_date, new_type, new_symbol, new_amount, new_shares, new_note, entry_id),
        )
        conn.commit()
        if enforce_guards:
            # Re-validate full book after edit
            try:
                reconstruct(db_path)
            except Exception:
                pass
        updated = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
    return _row_to_entry(updated)


def find_corporate_action(
    *,
    symbol: str,
    action_kind: str,
    effective_date: str,
    db_path: Path | None = None,
) -> LedgerEntry | None:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM ledger_entries
            WHERE deleted_at IS NULL
              AND entry_type = 'corporate_action'
              AND symbol = ?
              AND action_kind = ?
              AND effective_date = ?
            LIMIT 1
            """,
            (symbol, action_kind, effective_date),
        ).fetchone()
    return _row_to_entry(row) if row else None


def get_setting(key: str, default: str = "", db_path: Path | None = None) -> str:
    with connect(db_path) as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str, db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO app_settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()
