"""Sync fund splits/dividends into ledger corporate_action entries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from quadbalance.ledger import (
    PortfolioState,
    add_entry,
    find_corporate_action,
    get_setting,
    reconstruct,
    set_setting,
)


def fetch_fund_splits(symbol: str) -> pd.DataFrame:
    """Return split details for an OTC fund; empty if unavailable."""
    try:
        import akshare as ak

        raw = ak.fund_open_fund_info_em(symbol=symbol, indicator="拆分详情")
    except Exception:
        return pd.DataFrame()
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    # Expected columns vary; normalize common Eastmoney labels.
    rename = {}
    for col in df.columns:
        if "拆分折算日" in str(col) or col == "拆分折算日":
            rename[col] = "effective_date"
        if "拆分折算比例" in str(col) or "拆分折算" in str(col):
            rename[col] = "ratio"
    df = df.rename(columns=rename)
    if "effective_date" not in df.columns:
        return pd.DataFrame()
    df["effective_date"] = pd.to_datetime(df["effective_date"], errors="coerce")
    if "ratio" in df.columns:
        df["ratio"] = pd.to_numeric(df["ratio"], errors="coerce")
    return df.dropna(subset=["effective_date"])


def fetch_fund_dividends(symbol: str) -> pd.DataFrame:
    try:
        import akshare as ak

        raw = ak.fund_open_fund_info_em(symbol=symbol, indicator="分红送配详情")
    except Exception:
        return pd.DataFrame()
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    rename = {}
    for col in df.columns:
        c = str(col)
        if "除息" in c:
            rename[col] = "effective_date"
        if "每份分红" in c or c == "分红":
            rename[col] = "per_share"
    df = df.rename(columns=rename)
    if "effective_date" not in df.columns:
        return pd.DataFrame()
    df["effective_date"] = pd.to_datetime(df["effective_date"], errors="coerce")
    if "per_share" in df.columns:
        df["per_share"] = pd.to_numeric(df["per_share"], errors="coerce")
    return df.dropna(subset=["effective_date"])


def _shares_on_date(symbol: str, as_of: str, db_path: Path | None = None) -> float:
    """Reconstruct shares for symbol using only entries on/before as_of."""
    from quadbalance.ledger import list_entries

    shares = 0.0
    for e in list_entries(db_path):
        if e.entry_date > as_of:
            break
        if e.symbol != symbol:
            continue
        if e.entry_type == "opening" and e.shares:
            shares += float(e.shares)
        elif e.entry_type in {"buy", "dca"} and e.shares:
            shares += float(e.shares)
        elif e.entry_type == "sell" and e.shares:
            shares -= float(e.shares)
        elif e.entry_type == "rebalance" and e.shares is not None:
            shares += float(e.shares)
        elif e.entry_type == "corporate_action" and e.shares is not None:
            if e.action_kind in {"split", "dividend_reinvest"}:
                shares += float(e.shares)
    return shares


def sync_corporate_actions(
    *,
    symbols: list[str] | None = None,
    prices: dict[str, float] | None = None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Apply new splits/dividends idempotently.
    Dividend policy from setting `dividend_policy`: 'cash' (default) or 'reinvest'.
    """
    state = reconstruct(db_path)
    held = symbols if symbols is not None else sorted(state.shares.keys())
    policy = get_setting("dividend_policy", "cash", db_path=db_path)
    applied: list[dict[str, Any]] = []
    for symbol in held:
        # Splits
        splits = fetch_fund_splits(symbol)
        for _, row in splits.iterrows():
            eff = row["effective_date"].strftime("%Y-%m-%d")
            if find_corporate_action(symbol=symbol, action_kind="split", effective_date=eff, db_path=db_path):
                continue
            ratio = float(row["ratio"]) if "ratio" in row and pd.notna(row["ratio"]) else None
            if ratio is None or ratio <= 0:
                continue
            held_qty = _shares_on_date(symbol, eff, db_path=db_path)
            if held_qty <= 0:
                continue
            # ratio "每份" meaning new_shares = old * ratio → delta = old * (ratio - 1)
            delta = held_qty * (ratio - 1.0)
            add_entry(
                entry_date=eff,
                entry_type="corporate_action",
                symbol=symbol,
                shares=delta,
                amount=0.0,
                action_kind="split",
                effective_date=eff,
                source="system",
                note=f"split ratio={ratio}",
                enforce_guards=False,
                db_path=db_path,
            )
            applied.append({"symbol": symbol, "kind": "split", "effective_date": eff, "delta_shares": delta})

        dividends = fetch_fund_dividends(symbol)
        for _, row in dividends.iterrows():
            eff = row["effective_date"].strftime("%Y-%m-%d")
            per = float(row["per_share"]) if "per_share" in row and pd.notna(row["per_share"]) else None
            if per is None or per <= 0:
                continue
            kind = "dividend_cash" if policy == "cash" else "dividend_reinvest"
            if find_corporate_action(symbol=symbol, action_kind=kind, effective_date=eff, db_path=db_path):
                continue
            held_qty = _shares_on_date(symbol, eff, db_path=db_path)
            if held_qty <= 0:
                continue
            cash_amt = held_qty * per
            if policy == "cash":
                add_entry(
                    entry_date=eff,
                    entry_type="corporate_action",
                    symbol=symbol,
                    amount=cash_amt,
                    shares=0.0,
                    action_kind="dividend_cash",
                    effective_date=eff,
                    source="system",
                    note=f"dividend {per}/share",
                    enforce_guards=False,
                    db_path=db_path,
                )
            else:
                px = (prices or {}).get(symbol)
                if not px or px <= 0:
                    continue
                reinvest_shares = cash_amt / px
                add_entry(
                    entry_date=eff,
                    entry_type="corporate_action",
                    symbol=symbol,
                    amount=0.0,
                    shares=reinvest_shares,
                    action_kind="dividend_reinvest",
                    effective_date=eff,
                    source="system",
                    note=f"dividend reinvest {per}/share @ {px}",
                    enforce_guards=False,
                    db_path=db_path,
                )
            applied.append({"symbol": symbol, "kind": kind, "effective_date": eff, "amount": cash_amt})
    return applied


def set_dividend_policy(policy: str, db_path: Path | None = None) -> None:
    if policy not in {"cash", "reinvest"}:
        raise ValueError("dividend_policy must be 'cash' or 'reinvest'")
    set_setting("dividend_policy", policy, db_path=db_path)
