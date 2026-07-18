"""NiceGUI personal browser workbench."""

from __future__ import annotations

import json
import threading
import traceback
from pathlib import Path

from nicegui import run, ui

from quadbalance.asset_universe import CASH_SYMBOL
from quadbalance.config import StrategyConfig
from quadbalance.corporate_actions import set_dividend_policy, sync_corporate_actions
from quadbalance.data import fetch_prices
from quadbalance.ledger import add_entry, list_entries, reconstruct, soft_delete_entry
from quadbalance.lock_registry import activate_lock, get_active_lock
from quadbalance.paths import allocate_run_dir, default_db_path
from quadbalance.portfolio_templates import ALLOCATION_VARIANTS
from quadbalance.rebalance_guidance import compute_guidance
from quadbalance.single_run import run_single_config
from quadbalance.sweep import run_sweep

_run_lock = threading.Lock()
_run_busy = False
_log_lines: list[str] = []
DB = default_db_path()


def _log(msg: str) -> None:
    _log_lines.append(msg)
    if len(_log_lines) > 200:
        del _log_lines[:-200]


def _latest_marks(symbols: list[str]) -> tuple[dict[str, float], str | None]:
    prices: dict[str, float] = {}
    as_of = None
    for sym in symbols:
        try:
            series = fetch_prices(sym, use_cache=True)
            if series is None or series.empty:
                continue
            prices[sym] = float(series.iloc[-1])
            as_of = series.index[-1].strftime("%Y-%m-%d")
        except Exception as exc:  # noqa: BLE001
            _log(f"price fetch failed for {sym}: {exc}")
    return prices, as_of


def _build_config_from_form(
    allocation_name: str,
    bond_variant: str,
    dca_method: str,
    rebalance_pct: float,
    stock_sub_split: str,
) -> StrategyConfig:
    stocks, bonds, gold, cash = ALLOCATION_VARIANTS[allocation_name]
    return StrategyConfig(
        allocation_name=allocation_name,
        stocks=stocks,
        bonds=bonds,
        gold=gold,
        cash=cash,
        bond_variant=bond_variant,  # type: ignore[arg-type]
        dca_method=dca_method,  # type: ignore[arg-type]
        rebalance_threshold=rebalance_pct / 100.0,
        stock_sub_split=stock_sub_split,  # type: ignore[arg-type]
    )


def create_app() -> None:
    @ui.page("/")
    def index() -> None:
        ui.page_title("QuadBalance Workbench")
        with ui.header().classes("items-center justify-between"):
            ui.label("QuadBalance").classes("text-h5")
            with ui.row():
                ui.link("验证", "/")
                ui.link("持仓与账本", "/ledger")
                ui.link("调仓指引", "/guidance")

        ui.markdown(
            "**回测路径为引擎默认本金/定投假设，仅作示意，不等于你的实盘规模。**"
        ).classes("text-orange-700")

        intended = ui.select(
            ["accumulation", "balanced_core", "pre_retirement_preservation", "retirement_withdrawal"],
            value="balanced_core",
            label="Intended profile",
        )
        allocation = ui.select(list(ALLOCATION_VARIANTS.keys()), value="25-25-25-25", label="Allocation")
        bond = ui.select(["B1", "B2", "B3"], value="B1", label="Bond variant")
        dca = ui.select(["proportional", "underweight"], value="proportional", label="DCA")
        rebal = ui.number(label="Rebalance threshold %", value=5, min=1, max=20)
        split = ui.select(["60-40", "50-50", "40-60"], value="60-40", label="Stock sub-split")
        log_box = ui.log(max_lines=80).classes("w-full h-40")
        status = ui.label("")
        results_host = ui.column().classes("w-full")

        def append_log(msg: str) -> None:
            _log(msg)
            log_box.push(msg)

        def render_results(run_dir: Path) -> None:
            results_host.clear()
            with results_host:
                ui.label(f"Run: {run_dir}").classes("text-bold")
                metrics_path = run_dir / "artifacts" / "metrics.json"
                eq_path = run_dir / "artifacts" / "equity_curve.json"
                stress_path = run_dir / "artifacts" / "stress_summary.json"
                sweep_csv = run_dir / "sweep_results.csv"
                if metrics_path.exists():
                    m = json.loads(metrics_path.read_text(encoding="utf-8"))
                    ui.markdown(
                        f"**{m.get('config_id')}** · ann {m.get('annualized_return', 0):.2%} · "
                        f"MDD {m.get('max_drawdown', 0):.2%} · Sharpe {m.get('sharpe_ratio', 0):.2f}"
                    )
                if eq_path.exists():
                    eq = json.loads(eq_path.read_text(encoding="utf-8"))
                    ui.label("Backtest NAV (illustrative capital)").classes("text-subtitle1")
                    ui.echart(
                        {
                            "xAxis": {"type": "category", "data": eq["dates"][::max(1, len(eq['dates']) // 200)]},
                            "yAxis": {"type": "value"},
                            "series": [
                                {
                                    "type": "line",
                                    "showSymbol": False,
                                    "data": eq["equity"][::max(1, len(eq["equity"]) // 200)],
                                }
                            ],
                        }
                    ).classes("w-full h-64")
                    ui.label("Drawdown").classes("text-subtitle1")
                    ui.echart(
                        {
                            "xAxis": {"type": "category", "data": eq["dates"][::max(1, len(eq["dates"]) // 200)]},
                            "yAxis": {"type": "value"},
                            "series": [
                                {
                                    "type": "line",
                                    "showSymbol": False,
                                    "data": eq["drawdown"][::max(1, len(eq["drawdown"]) // 200)],
                                }
                            ],
                        }
                    ).classes("w-full h-48")
                if stress_path.exists():
                    st = json.loads(stress_path.read_text(encoding="utf-8"))
                    ui.label("Stress summary").classes("text-subtitle1")
                    rows = [
                        {
                            "id": s.get("id"),
                            "kind": s.get("kind"),
                            "classification": s.get("classification"),
                        }
                        for s in st.get("scenarios", [])
                    ]
                    if rows:
                        ui.table(columns=[
                            {"name": "id", "label": "Scenario", "field": "id"},
                            {"name": "kind", "label": "Kind", "field": "kind"},
                            {"name": "classification", "label": "Class", "field": "classification"},
                        ], rows=rows, row_key="id").classes("w-full")
                    if st.get("needs_review"):
                        ui.markdown("**Needs review:** " + "; ".join(st["needs_review"]))
                if sweep_csv.exists():
                    import pandas as pd

                    df = pd.read_csv(sweep_csv)
                    if "validation_passed" in df.columns and not df["validation_passed"].any():
                        ui.label("No configuration passed validation.").classes("text-negative")
                    ui.table(
                        columns=[{"name": c, "label": c, "field": c} for c in df.columns[:8]],
                        rows=df.head(50).to_dict("records"),
                        row_key="config_id" if "config_id" in df.columns else df.columns[0],
                    ).classes("w-full")

                lock_cfg_id = ui.input("Lock config_id (must have passed)", placeholder="from sweep/single")
                if metrics_path.exists():
                    lock_cfg_id.value = json.loads(metrics_path.read_text())["config_id"]

                def do_lock() -> None:
                    from quadbalance.config import StrategyConfig
                    from quadbalance.portfolio_templates import ALLOCATION_VARIANTS as AV

                    # Prefer artifacts config.json
                    cfg_path = run_dir / "artifacts" / "config.json"
                    if not cfg_path.exists():
                        ui.notify("Missing artifacts; run single-config first", type="negative")
                        return
                    raw = json.loads(cfg_path.read_text(encoding="utf-8"))
                    # Ensure this is the requested id — if different, run_single first
                    wanted = (lock_cfg_id.value or "").strip()
                    if wanted and wanted != raw.get("config_id"):
                        # rebuild from allocation name embedded in config_id is hard; require matching artifacts
                        ui.notify("Selected config differs from artifacts; run single-config for that id first", type="warning")
                        return
                    passed = True
                    if sweep_csv.exists():
                        import pandas as pd

                        sdf = pd.read_csv(sweep_csv)
                        row = sdf[sdf["config_id"] == raw["config_id"]]
                        if not row.empty and not bool(row.iloc[0].get("validation_passed", True)):
                            passed = False
                    if not passed:
                        ui.notify("Cannot lock a non-passing configuration", type="negative")
                        return
                    stocks, bonds, gold, cash = (
                        float(raw["stocks"]),
                        float(raw["bonds"]),
                        float(raw["gold"]),
                        float(raw["cash"]),
                    )
                    config = StrategyConfig(
                        allocation_name=raw["allocation_name"],
                        stocks=stocks,
                        bonds=bonds,
                        gold=gold,
                        cash=cash,
                        bond_variant=raw["bond_variant"],
                        dca_method=raw["dca_method"],
                        rebalance_threshold=float(raw["rebalance_threshold"]),
                        stock_sub_split=raw.get("stock_sub_split", "60-40"),
                        enable_qdii_quota=bool(raw.get("enable_qdii_quota", True)),
                        qdii_daily_caps=raw.get("qdii_daily_caps"),
                    )
                    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
                    suit_path = run_dir / "artifacts" / "suitability.json"
                    suit = json.loads(suit_path.read_text(encoding="utf-8")) if suit_path.exists() else {}
                    activate_lock(
                        config=config,
                        run_dir=run_dir,
                        validation_passed=True,
                        intended_profile=intended.value,
                        metrics_summary=metrics,
                        suitability_summary=suit,
                        config_artifact=raw,
                        db_path=DB,
                    )
                    ui.notify(f"Locked {config.config_id}", type="positive")

                ui.button("Lock as current strategy", on_click=do_lock)

        async def run_job(kind: str) -> None:
            global _run_busy
            if not _run_lock.acquire(blocking=False):
                ui.notify("A run is already active", type="warning")
                return
            _run_busy = True
            status.text = "Running…"
            append_log(f"Starting {kind}…")

            intended_profile = intended.value
            form_args: tuple[str, str, str, float, str] | None = None
            if kind != "sweep":
                form_args = (
                    allocation.value,
                    bond.value,
                    dca.value,
                    float(rebal.value or 5),
                    split.value,
                )

            try:
                def work() -> Path:
                    run_dir = allocate_run_dir()
                    _log(f"Output → {run_dir}")
                    if kind == "sweep":
                        run_sweep(
                            output_dir=run_dir,
                            intended_profile=intended_profile,
                        )
                    else:
                        assert form_args is not None
                        cfg = _build_config_from_form(*form_args)
                        run_single_config(
                            cfg,
                            run_dir,
                            intended_profile=intended_profile,
                        )
                    return run_dir

                run_dir = await run.io_bound(work)
                if run_dir is None:
                    status.text = "Cancelled"
                    return
                append_log(f"Output → {run_dir}")
                append_log("Complete")
                status.text = f"Done: {run_dir}"
                render_results(run_dir)
            except Exception as exc:  # noqa: BLE001
                append_log(traceback.format_exc())
                status.text = f"Failed: {exc}"
                ui.notify(str(exc), type="negative")
            finally:
                _run_busy = False
                _run_lock.release()

        with ui.row():
            ui.button("全面验证 (sweep)", on_click=lambda: run_job("sweep")).props("color=primary")
            ui.button("试跑当前配置", on_click=lambda: run_job("single"))

        active = get_active_lock(DB)
        if active:
            ui.label(f"Active lock: {active.config_id}").classes("text-positive")

    @ui.page("/ledger")
    def ledger_page() -> None:
        ui.page_title("Ledger — QuadBalance")
        with ui.header().classes("items-center justify-between"):
            ui.label("持仓与账本")
            with ui.row():
                ui.link("验证", "/")
                ui.link("持仓与账本", "/ledger")
                ui.link("调仓指引", "/guidance")

        host = ui.column().classes("w-full")

        def refresh() -> None:
            host.clear()
            state = reconstruct(DB)
            symbols = sorted(set(state.shares) | {CASH_SYMBOL})
            prices, as_of = _latest_marks(symbols)
            with host:
                ui.label(f"Marks as-of: {as_of or 'n/a'}").classes("text-caption")
                ui.button(
                    "Refresh prices",
                    on_click=lambda: (refresh(), ui.notify("Prices refreshed")),
                )
                total = state.settlement_cash + sum(
                    state.shares.get(s, 0) * prices.get(s, 0) for s in state.shares
                )
                ui.markdown(
                    f"**Settlement cash:** {state.settlement_cash:,.2f} · "
                    f"**Cash sleeve shares ({CASH_SYMBOL}):** {state.shares.get(CASH_SYMBOL, 0):,.4f} · "
                    f"**Total:** {total:,.2f}"
                )
                lock = get_active_lock(DB)
                if lock and total > 0:
                    tw = lock.snapshot.get("quadrant_weights") or {}
                    # rough drift display
                    ui.label("Drift vs active lock (see Guidance for alerts)")
                rows = [
                    {"symbol": s, "shares": q, "price": prices.get(s), "value": q * prices.get(s, 0)}
                    for s, q in state.shares.items()
                ]
                ui.table(
                    columns=[
                        {"name": "symbol", "label": "Symbol", "field": "symbol"},
                        {"name": "shares", "label": "Shares", "field": "shares"},
                        {"name": "price", "label": "Price", "field": "price"},
                        {"name": "value", "label": "Value", "field": "value"},
                    ],
                    rows=rows,
                    row_key="symbol",
                ).classes("w-full")

                ui.separator()
                ui.label("Opening / trade entry")
                etype = ui.select(
                    ["opening", "buy", "sell", "dca", "rebalance", "settlement_cash"],
                    value="buy",
                    label="Type",
                )
                date = ui.input("Date YYYY-MM-DD", value="2024-01-01")
                symbol = ui.input("Symbol (empty for settlement cash opening)")
                amount = ui.number("Amount", value=0)
                shares = ui.number("Shares", value=0)
                note = ui.input("Note")

                def save_entry() -> None:
                    try:
                        add_entry(
                            entry_date=date.value or "2024-01-01",
                            entry_type=etype.value,  # type: ignore[arg-type]
                            symbol=(symbol.value or None) or None,
                            amount=float(amount.value or 0) or None,
                            shares=float(shares.value or 0) or None,
                            note=note.value or None,
                            enforce_guards=etype.value not in {"opening", "settlement_cash"},
                            db_path=DB,
                        )
                        ui.notify("Saved", type="positive")
                        refresh()
                    except Exception as exc:  # noqa: BLE001
                        ui.notify(str(exc), type="negative")

                ui.button("Add entry", on_click=save_entry)

                ui.separator()
                ui.label("Entries")
                ents = list_entries(DB)
                erows = [
                    {
                        "id": e.id,
                        "date": e.entry_date,
                        "type": e.entry_type,
                        "symbol": e.symbol,
                        "amount": e.amount,
                        "shares": e.shares,
                    }
                    for e in ents
                ]
                ui.table(
                    columns=[
                        {"name": "id", "label": "ID", "field": "id"},
                        {"name": "date", "label": "Date", "field": "date"},
                        {"name": "type", "label": "Type", "field": "type"},
                        {"name": "symbol", "label": "Symbol", "field": "symbol"},
                        {"name": "amount", "label": "Amount", "field": "amount"},
                        {"name": "shares", "label": "Shares", "field": "shares"},
                    ],
                    rows=erows,
                    row_key="id",
                ).classes("w-full")
                del_id = ui.number("Delete entry id", value=0)

                def do_delete() -> None:
                    soft_delete_entry(int(del_id.value or 0), db_path=DB)
                    refresh()

                ui.button("Soft-delete entry", on_click=do_delete)

                ui.separator()
                policy = ui.select(["cash", "reinvest"], value="cash", label="Dividend default")

                def sync_ca() -> None:
                    set_dividend_policy(policy.value, db_path=DB)
                    prices_now, _ = _latest_marks(list(reconstruct(DB).shares.keys()))
                    applied = sync_corporate_actions(prices=prices_now, db_path=DB)
                    ui.notify(f"Applied {len(applied)} corporate actions", type="positive")
                    refresh()

                ui.button("Sync corporate actions", on_click=sync_ca)

        refresh()

    @ui.page("/guidance")
    def guidance_page() -> None:
        ui.page_title("Guidance — QuadBalance")
        with ui.header().classes("items-center justify-between"):
            ui.label("调仓指引")
            with ui.row():
                ui.link("验证", "/")
                ui.link("持仓与账本", "/ledger")
                ui.link("调仓指引", "/guidance")

        lock = get_active_lock(DB)
        if lock is None:
            ui.label("No active lock — lock a passing configuration first.")
            return
        state = reconstruct(DB)
        symbols = sorted(set(state.shares) | set((lock.snapshot.get("instrument_weights") or {}).keys()))
        prices, as_of = _latest_marks(symbols)
        ui.label(f"Active lock: {lock.config_id} · marks as-of {as_of or 'n/a'}")
        from quadbalance.config import StrategyConfig

        cfg = None
        try:
            from quadbalance.rebalance_guidance import config_from_lock_snapshot

            cfg = config_from_lock_snapshot(lock)
            qdii = {s for s in symbols if cfg.is_qdii_symbol(s)}
        except Exception:  # noqa: BLE001
            qdii = set()
        result = compute_guidance(
            lock=lock,
            shares=state.shares,
            settlement_cash=state.settlement_cash,
            prices=prices,
            qdii_symbols=qdii,
        )
        if result.incomplete:
            ui.label("Guidance incomplete — missing prices: " + ", ".join(result.missing_prices))
            return
        if not result.alert:
            ui.label("No actionable rebalance alert (within threshold / no material idle cash).").classes(
                "text-positive"
            )
        else:
            ui.label("Actionable rebalance alert").classes("text-negative text-h6")
            ui.markdown("Reasons: " + "; ".join(result.reasons))
            rows = [
                {
                    "side": L.side,
                    "symbol": L.symbol,
                    "amount": round(L.amount, 2),
                    "approx_shares": None if L.approx_shares is None else round(L.approx_shares, 4),
                    "note": L.note,
                }
                for L in result.legs
            ]
            ui.table(
                columns=[
                    {"name": "side", "label": "Side", "field": "side"},
                    {"name": "symbol", "label": "Symbol", "field": "symbol"},
                    {"name": "amount", "label": "Amount", "field": "amount"},
                    {"name": "approx_shares", "label": "≈Shares", "field": "approx_shares"},
                    {"name": "note", "label": "Note", "field": "note"},
                ],
                rows=rows,
                row_key="symbol",
            ).classes("w-full")
            if result.warnings:
                ui.markdown("Warnings: " + "; ".join(result.warnings))
        ui.markdown(f"Quadrant drift: `{result.quadrant_drift}`")


def main() -> None:
    create_app()
    ui.run(title="QuadBalance", reload=False, show=True)


if __name__ in {"__main__", "__mp_main__"}:
    main()
