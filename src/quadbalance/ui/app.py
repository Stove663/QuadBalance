"""NiceGUI 个人工作台。"""

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
        ui.page_title("QuadBalance 工作台")
        with ui.header().classes("items-center justify-between"):
            ui.label("QuadBalance").classes("text-h5")
            with ui.row():
                ui.link("验证", "/")
                ui.link("持仓与账本", "/ledger")
                ui.link("调仓指引", "/guidance")

        with ui.card().classes("w-full bg-amber-50 border border-amber-200 shadow-sm"):
            with ui.row().classes("items-center gap-3"):
                ui.label("提示").classes("text-bold text-amber-900")
                ui.label("回测路径使用引擎默认本金与定投假设，仅作示意，不等于你的实盘规模。")
        

        active = get_active_lock(DB)
        state = reconstruct(DB)
        portfolio_total = state.settlement_cash
        qdii_total = state.shares.get(CASH_SYMBOL, 0) * 0
        try:
            price_symbols = sorted(set(state.shares) | {CASH_SYMBOL})
            prices, marks_as_of = _latest_marks(price_symbols)
            portfolio_total = state.settlement_cash + sum(
                state.shares.get(s, 0) * prices.get(s, 0) for s in state.shares
            )
            qdii_total = state.shares.get(CASH_SYMBOL, 0) * prices.get(CASH_SYMBOL, 0) if CASH_SYMBOL in prices else 0
        except Exception:  # noqa: BLE001
            prices = {}
            marks_as_of = None

        current_run_dir: Path | None = None
        current_metrics: dict[str, object] = {}
        current_equity: dict[str, object] = {}
        current_stress: dict[str, object] = {}
        current_sweep: object | None = None

        def load_artifacts(run_dir: Path) -> None:
            nonlocal current_run_dir, current_metrics, current_equity, current_stress, current_sweep
            current_run_dir = run_dir
            current_metrics = {}
            current_equity = {}
            current_stress = {}
            current_sweep = None

            metrics_path = run_dir / "artifacts" / "metrics.json"
            eq_path = run_dir / "artifacts" / "equity_curve.json"
            stress_path = run_dir / "artifacts" / "stress_summary.json"
            sweep_csv = run_dir / "sweep_results.csv"

            if metrics_path.exists():
                current_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            if eq_path.exists():
                current_equity = json.loads(eq_path.read_text(encoding="utf-8"))
            if stress_path.exists():
                current_stress = json.loads(stress_path.read_text(encoding="utf-8"))
            if sweep_csv.exists():
                import pandas as pd

                current_sweep = pd.read_csv(sweep_csv)

        def latest_run_dir() -> Path | None:
            candidates = sorted(
                (p for p in allocate_run_dir().parent.iterdir() if p.is_dir()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            return candidates[0] if candidates else None

        candidate = latest_run_dir()
        if candidate is not None:
            try:
                load_artifacts(candidate)
            except Exception:  # noqa: BLE001
                current_run_dir = candidate

        def append_log(msg: str) -> None:
            _log(msg)

        def render_result_summary() -> None:
            result_summary.clear()
            with result_summary:
                ui.label("最近运行摘要").classes("text-subtitle1")
                if not current_metrics:
                    ui.label("暂无最近结果，运行验证后会在这里显示摘要。").classes("text-medium-emphasis")
                    return
                ui.grid(columns=4).classes("w-full gap-4")
                with ui.card().classes("w-full"):
                    ui.label("配置").classes("text-caption")
                    ui.label(str(current_metrics.get("config_id", "无"))).classes("text-bold")
                with ui.card().classes("w-full"):
                    ui.label("年化收益").classes("text-caption")
                    ui.label(f"{float(current_metrics.get('annualized_return', 0)):,.2%}").classes("text-bold")
                with ui.card().classes("w-full"):
                    ui.label("最大回撤").classes("text-caption")
                    ui.label(f"{float(current_metrics.get('max_drawdown', 0)):,.2%}").classes("text-bold")
                with ui.card().classes("w-full"):
                    ui.label("夏普比率").classes("text-caption")
                    ui.label(f"{float(current_metrics.get('sharpe_ratio', 0)):,.2f}").classes("text-bold")

                with ui.row().classes("w-full items-start gap-4"):
                    with ui.card().classes("w-full"):
                        ui.label("净值").classes("text-subtitle2")
                        if current_equity:
                            eq = current_equity
                            ui.echart(
                                {
                                    "xAxis": {
                                        "type": "category",
                                        "data": eq["dates"][:: max(1, len(eq["dates"]) // 200)],
                                    },
                                    "yAxis": {"type": "value"},
                                    "series": [
                                        {
                                            "type": "line",
                                            "showSymbol": False,
                                            "data": eq["equity"][:: max(1, len(eq["equity"]) // 200)],
                                        }
                                    ],
                                }
                            ).classes("w-full h-64")
                        else:
                            ui.label("暂无净值曲线").classes("text-medium-emphasis")
                    with ui.card().classes("w-full"):
                        ui.label("回撤").classes("text-subtitle2")
                        if current_equity:
                            eq = current_equity
                            ui.echart(
                                {
                                    "xAxis": {
                                        "type": "category",
                                        "data": eq["dates"][:: max(1, len(eq["dates"]) // 200)],
                                    },
                                    "yAxis": {"type": "value"},
                                    "series": [
                                        {
                                            "type": "line",
                                            "showSymbol": False,
                                            "data": eq["drawdown"][:: max(1, len(eq["drawdown"]) // 200)],
                                        }
                                    ],
                                }
                            ).classes("w-full h-64")
                        else:
                            ui.label("暂无回撤曲线").classes("text-medium-emphasis")

                with ui.row().classes("w-full items-start gap-4"):
                    with ui.card().classes("w-full"):
                        ui.label("压力测试摘要").classes("text-subtitle2")
                        if current_stress:
                            rows = [
                                {
                                    "id": s.get("id"),
                                    "kind": s.get("kind"),
                                    "classification": s.get("classification"),
                                }
                                for s in current_stress.get("scenarios", [])
                            ]
                            if rows:
                                ui.table(
                                    columns=[
                                        {"name": "id", "label": "场景编号", "field": "id"},
                                        {"name": "kind", "label": "类别", "field": "kind"},
                                        {"name": "classification", "label": "结论", "field": "classification"},
                                    ],
                                    rows=rows,
                                    row_key="id",
                                ).classes("w-full")
                            if current_stress.get("needs_review"):
                                ui.markdown("**需要复核：** " + "; ".join(current_stress["needs_review"]))
                        else:
                            ui.label("暂无压力测试摘要").classes("text-medium-emphasis")
                    with ui.card().classes("w-full"):
                        ui.label("扫描验证结果").classes("text-subtitle2")
                        if current_sweep is not None:
                            import pandas as pd

                            df = current_sweep if isinstance(current_sweep, pd.DataFrame) else None
                            if df is not None:
                                if "validation_passed" in df.columns and not df["validation_passed"].any():
                                    ui.label("没有配置通过验证。").classes("text-negative")
                                ui.table(
                                    columns=[{"name": c, "label": c, "field": c} for c in df.columns[:8]],
                                    rows=df.head(20).to_dict("records"),
                                    row_key="config_id" if "config_id" in df.columns else df.columns[0],
                                ).classes("w-full")
                        else:
                            ui.label("暂无扫描结果").classes("text-medium-emphasis")

        def render_overview() -> None:
            overview_host.clear()
            with overview_host:
                with ui.card().classes("w-full bg-gradient-to-r from-slate-50 to-white border border-slate-200 shadow-sm"):
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.column().classes("gap-1"):
                            ui.label("仪表盘总览").classes("text-h5 text-slate-900")
                            ui.label("查看当前策略状态、最近结果和可执行动作。")
                        with ui.row().classes("items-center gap-3"):
                            if active:
                                ui.label("●").classes("text-positive text-h6")
                                ui.label("已锁定").classes("text-positive text-bold")
                            elif current_metrics:
                                ui.label("●").classes("text-warning text-h6")
                                ui.label("已验证未锁定").classes("text-warning text-bold")
                            else:
                                ui.label("●").classes("text-negative text-h6")
                                ui.label("待验证").classes("text-negative text-bold")

                    with ui.row().classes("w-full gap-4 mt-4 items-stretch"):
                        with ui.card().classes("w-full bg-white border border-slate-200 shadow-sm"):
                            ui.label("当前策略").classes("text-caption text-slate-500")
                            if active:
                                ui.label(active.config_id).classes("text-bold text-slate-900 text-lg")
                                ui.label(f"画像：{active.intended_profile}").classes("text-slate-700")
                                ui.label("状态：已锁定，可进入调仓指引").classes("text-positive text-bold")
                            else:
                                ui.label("尚未锁定策略").classes("text-negative text-bold text-lg")
                            ui.label("先运行验证并锁定通过配置，再进入调仓流程。").classes("text-slate-600")
                        with ui.card().classes("w-full bg-white border border-slate-200 shadow-sm"):
                            ui.label("最近验证结果").classes("text-caption text-slate-500")
                            if current_metrics:
                                with ui.row().classes("w-full gap-3"):
                                    with ui.card().classes("w-full bg-emerald-50 border-0"):
                                        ui.label("年化收益").classes("text-xs text-emerald-700")
                                        ui.label(f"{float(current_metrics.get('annualized_return', 0)):,.2%}").classes("text-bold text-xl text-emerald-900")
                                    with ui.card().classes("w-full bg-rose-50 border-0"):
                                        ui.label("最大回撤").classes("text-xs text-rose-700")
                                        ui.label(f"{float(current_metrics.get('max_drawdown', 0)):,.2%}").classes("text-bold text-xl text-rose-900")
                                    with ui.card().classes("w-full bg-sky-50 border-0"):
                                        ui.label("夏普比率").classes("text-xs text-sky-700")
                                        ui.label(f"{float(current_metrics.get('sharpe_ratio', 0)):,.2f}").classes("text-bold text-xl text-sky-900")
                            else:
                                ui.label("暂无结果").classes("text-medium-emphasis")
                        with ui.card().classes("w-full bg-white border border-slate-200 shadow-sm"):
                            ui.label("账本概览").classes("text-caption text-slate-500")
                            ui.label(f"结算现金：{state.settlement_cash:,.2f}").classes("text-slate-900")
                            ui.label(f"组合总额：{portfolio_total:,.2f}").classes("text-bold text-slate-900 text-lg")
                            ui.label(f"现金份额：{state.shares.get(CASH_SYMBOL, 0):,.4f}").classes("text-slate-700")
                            ui.separator()
                            ui.label(f"最近价格时间：{marks_as_of or 'n/a'}").classes("text-slate-500")
                        with ui.card().classes("w-full bg-white border border-slate-200 shadow-sm"):
                            ui.label("风险提示").classes("text-caption text-slate-500")
                            if current_stress.get("needs_review"):
                                ui.label("存在需要复核项").classes("text-negative text-bold")
                                ui.markdown("；".join(current_stress["needs_review"]))
                            elif active:
                                ui.label("当前无显著告警").classes("text-positive text-bold")
                            else:
                                ui.label("等待锁定与验证结果").classes("text-slate-600")

                    with ui.row().classes("w-full items-start gap-4 mt-4"):
                        with ui.card().classes("w-full bg-white border border-slate-200 shadow-sm"):
                            ui.label("验证参数").classes("text-subtitle1 text-slate-800")
                            ui.markdown("选择策略参数后执行扫描验证或单配置试跑。")
                            for label, value in [
                                ("目标画像", intended.value),
                                ("资产配置", allocation.value),
                                ("债券方案", bond.value),
                                ("定投方式", dca.value),
                                ("再平衡阈值", f"{rebal.value}%"),
                                ("股票子分配", split.value),
                            ]:
                                with ui.row().classes("w-full items-center justify-between py-1 border-b border-slate-100"):
                                    ui.label(label).classes("text-slate-500")
                                    ui.label(str(value)).classes("text-slate-900 text-bold")
                        with ui.card().classes("w-full bg-white border border-slate-200 shadow-sm"):
                            ui.label("核心操作").classes("text-subtitle1 text-slate-800")
                            ui.button("全面验证（扫描）", on_click=lambda: run_job("sweep")).props("color=primary")
                            ui.button("试跑当前配置", on_click=lambda: run_job("single")).props("color=secondary")
                            if active is None:
                                ui.button("查看调仓指引", on_click=lambda: ui.notify("需要先锁定一个通过验证的配置。", type="warning"))
                                ui.label("需要先锁定一个通过验证的配置。").classes("text-medium-emphasis")
                            else:
                                ui.button("查看调仓指引", on_click=lambda: ui.navigate.to("/guidance"))
                                ui.label("可直接进入调仓页查看最新告警。").classes("text-positive")

                    with ui.card().classes("w-full bg-slate-900 text-white shadow-lg"):
                        with ui.row().classes("w-full items-center justify-between"):
                            ui.label("运行状态").classes("text-subtitle1")
                            ui.label(status_text).classes("text-bold")
                        ui.label(f"最近价格时间：{marks_as_of or 'n/a'}").classes("text-slate-300")
                        ui.log(max_lines=60).classes("w-full h-40 bg-slate-950 text-white")

        intended = ui.select(
            ["accumulation", "balanced_core", "pre_retirement_preservation", "retirement_withdrawal"],
            value="balanced_core",
            label="目标画像",
        )
        allocation = ui.select(list(ALLOCATION_VARIANTS.keys()), value="25-25-25-25", label="资产配置")
        bond = ui.select(["B1", "B2", "B3"], value="B1", label="债券方案")
        dca = ui.select(["proportional", "underweight"], value="proportional", label="定投方式")
        rebal = ui.number(label="再平衡阈值 %", value=5, min=1, max=20)
        split = ui.select(["60-40", "50-50", "40-60"], value="60-40", label="股票子分配")
        status_text = "空闲"
        overview_host = ui.column().classes("w-full")
        result_summary = ui.column().classes("w-full")
        render_overview()
        render_result_summary()

        async def run_job(kind: str) -> None:
            global _run_busy
            nonlocal status_text
            if not _run_lock.acquire(blocking=False):
                ui.notify("已有任务正在运行", type="warning")
                return
            _run_busy = True
            status_text = f"正在执行 {kind}…"
            render_overview()
            append_log(f"开始 {kind}…")

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
                    status_text = "已取消"
                    return
                append_log(f"输出 → {run_dir}")
                append_log("完成")
                status_text = f"完成：{run_dir}"
                load_artifacts(run_dir)
                render_result_summary()
                render_overview()
            except Exception as exc:  # noqa: BLE001
                append_log(traceback.format_exc())
                status_text = f"失败：{exc}"
                ui.notify(str(exc), type="negative")
                render_overview()
            finally:
                _run_busy = False
                _run_lock.release()

        current_run_dir = current_run_dir or latest_run_dir()
        if current_run_dir is not None:
            try:
                load_artifacts(current_run_dir)
            except Exception:  # noqa: BLE001
                pass
        render_overview()
        render_result_summary()
        if active:
            ui.label(f"当前锁定：{active.config_id}").classes("text-positive")

    @ui.page("/ledger")
    def ledger_page() -> None:
        ui.page_title("持仓与账本 — QuadBalance")
        with ui.header().classes("items-center justify-between"):
            ui.label("持仓与账本").classes("text-h5")
            with ui.row():
                ui.link("验证", "/")
                ui.link("持仓与账本", "/ledger")
                ui.link("调仓指引", "/guidance")

        host = ui.column().classes("w-full gap-4")

        def refresh() -> None:
            host.clear()
            state = reconstruct(DB)
            symbols = sorted(set(state.shares) | {CASH_SYMBOL})
            prices, as_of = _latest_marks(symbols)
            total = state.settlement_cash + sum(state.shares.get(s, 0) * prices.get(s, 0) for s in state.shares)
            lock = get_active_lock(DB)
            with host:
                with ui.card().classes("w-full bg-gradient-to-r from-slate-50 to-white border border-slate-200 shadow-sm"):
                    ui.label("账本总览").classes("text-h6 text-slate-900")
                    with ui.row().classes("w-full gap-4 mt-3"):
                        with ui.card().classes("w-full bg-emerald-50 border-0"):
                            ui.label("结算现金").classes("text-xs text-emerald-700")
                            ui.label(f"{state.settlement_cash:,.2f}").classes("text-bold text-xl text-emerald-900")
                        with ui.card().classes("w-full bg-sky-50 border-0"):
                            ui.label("现金份额").classes("text-xs text-sky-700")
                            ui.label(f"{state.shares.get(CASH_SYMBOL, 0):,.4f}").classes("text-bold text-xl text-sky-900")
                        with ui.card().classes("w-full bg-indigo-50 border-0"):
                            ui.label("总资产").classes("text-xs text-indigo-700")
                            ui.label(f"{total:,.2f}").classes("text-bold text-xl text-indigo-900")
                        with ui.card().classes("w-full bg-slate-50 border-0"):
                            ui.label("价格时间").classes("text-xs text-slate-600")
                            ui.label(as_of or "n/a").classes("text-bold text-xl text-slate-900")
                    if lock and total > 0:
                        ui.label("相对当前锁定存在漂移，请到调仓指引页查看告警。").classes("text-warning")
                    ui.button("刷新价格", on_click=lambda: (refresh(), ui.notify("价格已刷新"))).props("color=primary")

                with ui.card().classes("w-full bg-white border border-slate-200 shadow-sm"):
                    ui.label("持仓明细").classes("text-subtitle1 text-slate-800")
                    rows = [
                        {"symbol": s, "shares": q, "price": prices.get(s), "value": q * prices.get(s, 0)}
                        for s, q in state.shares.items()
                    ]
                    ui.table(
                        columns=[
                            {"name": "symbol", "label": "标的", "field": "symbol"},
                            {"name": "shares", "label": "份额", "field": "shares"},
                            {"name": "price", "label": "价格", "field": "price"},
                            {"name": "value", "label": "市值", "field": "value"},
                        ],
                        rows=rows,
                        row_key="symbol",
                    ).classes("w-full")

                with ui.card().classes("w-full bg-white border border-slate-200 shadow-sm"):
                    ui.label("开仓 / 交易录入").classes("text-subtitle1 text-slate-800")
                    with ui.row().classes("w-full gap-4"):
                        etype = ui.select(
                            ["opening", "buy", "sell", "dca", "rebalance", "settlement_cash"],
                            value="buy",
                            label="类型",
                        )
                        date = ui.input("日期 YYYY-MM-DD", value="2024-01-01")
                        symbol = ui.input("标的代码（若为结算现金开仓则留空）")
                        amount = ui.number("金额", value=0)
                        shares = ui.number("份额", value=0)
                        note = ui.input("备注")
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
                            ui.notify("已保存", type="positive")
                            refresh()
                        except Exception as exc:  # noqa: BLE001
                            ui.notify(str(exc), type="negative")
                    ui.button("新增记录", on_click=save_entry).props("color=primary")

                with ui.card().classes("w-full bg-white border border-slate-200 shadow-sm"):
                    ui.label("账本记录").classes("text-subtitle1 text-slate-800")
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
                            {"name": "id", "label": "编号", "field": "id"},
                            {"name": "date", "label": "日期", "field": "date"},
                            {"name": "type", "label": "类型", "field": "type"},
                            {"name": "symbol", "label": "标的", "field": "symbol"},
                            {"name": "amount", "label": "金额", "field": "amount"},
                            {"name": "shares", "label": "份额", "field": "shares"},
                        ],
                        rows=erows,
                        row_key="id",
                    ).classes("w-full")
                    with ui.row().classes("items-end gap-3"):
                        del_id = ui.number("删除记录编号", value=0)
                        policy = ui.select(["cash", "reinvest"], value="cash", label="默认分红处理")
                    def do_delete() -> None:
                        soft_delete_entry(int(del_id.value or 0), db_path=DB)
                        refresh()
                    def sync_ca() -> None:
                        set_dividend_policy(policy.value, db_path=DB)
                        prices_now, _ = _latest_marks(list(reconstruct(DB).shares.keys()))
                        applied = sync_corporate_actions(prices=prices_now, db_path=DB)
                        ui.notify(f"已应用 {len(applied)} 条公司行动", type="positive")
                        refresh()
                    with ui.row().classes("gap-2"):
                        ui.button("软删除记录", on_click=do_delete)
                        ui.button("同步公司行动", on_click=sync_ca).props("color=secondary")

        refresh()

    @ui.page("/guidance")
    def guidance_page() -> None:
        ui.page_title("调仓指引 — QuadBalance")
        with ui.header().classes("items-center justify-between"):
            ui.label("调仓指引").classes("text-h5")
            with ui.row():
                ui.link("验证", "/")
                ui.link("持仓与账本", "/ledger")
                ui.link("调仓指引", "/guidance")

        lock = get_active_lock(DB)
        if lock is None:
            with ui.card().classes("w-full bg-white border border-slate-200 shadow-sm"):
                ui.label("当前没有活跃锁定，请先锁定一个通过验证的配置。").classes("text-negative text-bold")
                ui.label("返回首页运行验证并锁定策略后，这里会显示调仓建议。\n").classes("text-slate-600")
            return

        state = reconstruct(DB)
        symbols = sorted(set(state.shares) | set((lock.snapshot.get("instrument_weights") or {}).keys()))
        prices, as_of = _latest_marks(symbols)

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

        with ui.card().classes("w-full bg-gradient-to-r from-slate-50 to-white border border-slate-200 shadow-sm"):
            ui.label("调仓总览").classes("text-h6 text-slate-900")
            with ui.row().classes("w-full gap-4 mt-3"):
                with ui.card().classes("w-full bg-indigo-50 border-0"):
                    ui.label("锁定配置").classes("text-xs text-indigo-700")
                    ui.label(lock.config_id).classes("text-bold text-indigo-900")
                with ui.card().classes("w-full bg-sky-50 border-0"):
                    ui.label("价格时间").classes("text-xs text-sky-700")
                    ui.label(as_of or "n/a").classes("text-bold text-sky-900")
                with ui.card().classes("w-full bg-emerald-50 border-0"):
                    ui.label("闲置现金").classes("text-xs text-emerald-700")
                    ui.label(f"{state.settlement_cash:,.2f}").classes("text-bold text-emerald-900")
                with ui.card().classes("w-full bg-slate-50 border-0"):
                    ui.label("象限漂移").classes("text-xs text-slate-600")
                    ui.label(str(result.quadrant_drift)).classes("text-bold text-slate-900")

        with ui.card().classes("w-full bg-white border border-slate-200 shadow-sm mt-4"):
            if result.incomplete:
                ui.label("指引不完整").classes("text-negative text-h6")
                ui.label("缺少价格：" + ", ".join(result.missing_prices)).classes("text-slate-700")
                return

            if not result.alert:
                ui.label("当前没有需要执行的调仓告警。")
                ui.label("持仓和现金仍在阈值内，继续保持观察。\n").classes("text-positive")
                if result.warnings:
                    ui.markdown("警告：" + "; ".join(result.warnings))
                return

            ui.label("可执行调仓告警").classes("text-negative text-h6")
            ui.markdown("原因：" + "; ".join(result.reasons))
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
                    {"name": "side", "label": "方向", "field": "side"},
                    {"name": "symbol", "label": "标的", "field": "symbol"},
                    {"name": "amount", "label": "金额", "field": "amount"},
                    {"name": "approx_shares", "label": "约份额", "field": "approx_shares"},
                    {"name": "note", "label": "备注", "field": "note"},
                ],
                rows=rows,
                row_key="symbol",
            ).classes("w-full")
            if result.warnings:
                ui.markdown("警告：" + "; ".join(result.warnings))


def main() -> None:
    create_app()
    ui.run(title="QuadBalance", reload=False, show=True)


if __name__ in {"__main__", "__mp_main__"}:
    main()
