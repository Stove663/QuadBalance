## Context

Phase 1 delivers a modular engine (`run_sweep`, validation, reporting, `output/artifacts/*.json`) used only via CLI. The personal workflow now needs a localhost NiceGUI workbench that can run validation, lock a target strategy immutably, record real trades, and suggest rebalances when drift exceeds the locked threshold—without rewriting the simulator or coupling UI to internal stress modules.

Stakeholders: single personal user. Constraints: minutes-long runs are acceptable; browser-only; no brokerage automation; ledger is amount + shares only.

## Goals / Non-Goals

**Goals:**

- NiceGUI UI to set profile/config, run full sweep or single-config validation, show progress/logs, and display results from artifacts + lock markdown/CSV, including **backtest NAV and drawdown charts** and **tabular stress summaries**.
- Export **equity/NAV and drawdown series** (and a compact stress-summary JSON when available) into the run artifact bundle for GUI consumption without re-simulation.
- Per-run output directories (`output/<run_id>/`) so locks and history are not destroyed by the next run.
- SQLite registry for immutable strategy locks (one active; prior locks retained) with a **self-contained config snapshot** (full weights + instruments).
- Personal ledger reconstructing positions, including **opening snapshot** for existing holdings; compare to active lock targets. **Mark prices load automatically** (cache-first + Refresh); users do not type NAVs.
- Clear separation of **settlement cash** vs **cash-sleeve (money-market fund) holdings**.
- Rebalance guidance that alerts by default only when any quadrant weight deviation exceeds the locked `rebalance_threshold`, then lists sell/buy amounts and approximate shares using a documented quadrant→instrument split rule, including deploying idle settlement cash into an underweight cash sleeve.
- Corporate-action handling via akshare dividend/split data: auto share adjustments for splits; dividend cash vs reinvest per user default; all system-applied entries reviewable/correctable.
- Engine `run_single` (name TBD) emitting the same artifact contract as a locked validation path.

**Non-Goals:**

- Multi-user auth, remote hosting, or SaaS deployment.
- Tax lots, cost-basis optimization, or fee-accurate trade sizing (guidance amounts are approximate; fees ignored in v1).
- Inferring each fund account’s dividend election from the broker (data sources expose per-fund dividend amounts, not per-investor cash-vs-reinvest choice).
- Settlement lag / T+N / 在途份额 modeling.
- Auto-executing trades or broker APIs.
- Merging simulated `events.json` into the real ledger.
- Hard-blocking guidance on QDII daily caps (warnings only in v1).
- Cancel-in-flight for long sweeps (v1: concurrency guard only; wait until finish/fail).
- DCA calendar reminders, one-click “apply guidance to ledger”, and DB backup automation (document manual backup only).
- Per-fund mini NAV chart walls, live ledger historical market-value charts (v1), and turning every stress scenario into a multi-line NAV trend chart.
- Replacing CSV/markdown Phase 1 reports.
- Emulating the engine’s **annual** rebalance *check schedule* in the live UI—live guidance is on-demand and threshold-gated whenever the user opens it.

## Decisions

1. **UI: NiceGUI over Streamlit**  
   Async-friendly long runs and multi-page structure fit better; stays in Python next to the engine.  
   *Alternatives:* Streamlit (faster prototype, weaker long-task UX); FastAPI+SPA (overkill for single user).

2. **Persistence split: files for runs, SQLite for locks + ledger**  
   Keep `output/<run_id>/` as the run truth source (reuse `run-artifacts`). SQLite holds `strategy_locks` and `ledger_entries` only. Default DB: `./data/quadbalance.db`. Gitignore `data/` (and keep ignoring `output/`).  
   *Alternatives:* all-files (weak lock history/query); Postgres (unnecessary ops).

3. **Run identity and non-destructive outputs**  
   Every UI-triggered sweep or single-config run writes to a new `output/<run_id>/` (timestamp + short id). The legacy CLI may still default to `output/` for back-compat, but the workbench MUST NOT reuse a single shared folder that overwrites prior artifacts. Locks store `run_dir` **and** a full snapshot so UI can display targets even if the directory is later deleted; if artifacts are missing, results deep-links degrade gracefully.

4. **Lock model: append-only history, single `is_active`, strong snapshot**  
   Activating a new lock sets previous active to inactive; never delete. Snapshot MUST include: allocation weights, bond variant, DCA method, rebalance threshold, stock sub-split, **resolved instrument weights / symbols**, enablement flags, and metrics/suitability summary. Do not rely on `config_id` alone against a mutable `asset_universe`.  
   From a sweep run, the user MAY lock either the engine-preferred candidate **or** another **passing** configuration from that run. If the chosen configuration does not already have a full artifact bundle (equity curve, etc.) in that run directory, the workbench MUST run **single-config validation** for that configuration into the run (or a linked run) **before** activating the lock—do not invent charts from sweep CSV scalars alone.

4b. **What may be locked**  
   Only configurations with `validation.passed == true` may become the active strategy lock. Configurations that are screened out or hard-failed MUST NOT be lockable. `needs_review` findings on an otherwise passing configuration remain visible in results; they do not by themselves block lock if `passed` is true. Non-passing rows may be inspected but not locked.
5. **Cash model: two buckets**  
   - **Settlement cash**: uninvested cash (bank/settlement), tracked via ledger `cash` / deposit-withdraw style entries; used first by rebalance guidance.  
   - **Cash sleeve**: money-market (or cash-quadrant) **fund shares**, part of portfolio market value and target weights.  
   Portfolio total for weights = Σ(fund shares × price) + settlement cash. Buying funds spends settlement cash and adds shares; selling funds adds settlement cash and reduces shares.

6. **Opening snapshot**  
   Ledger supports an `opening` (or equivalent) entry type / bulk flow to set initial shares per symbol and settlement cash as of a date, so existing portfolios can bootstrap without fake historical buys.

6b. **Ledger corrections**  
   Users MAY edit or delete ledger entries (including correcting amounts, shares, dates, symbols, and types). Reconstruction always replays the current entry set in order. Optional note field records why a correction was made; v1 does not require a separate immutable audit table beyond retaining the corrected row state (deleted rows are removed or soft-deleted—prefer soft-delete with `deleted_at` if easy).

6b2. **Ledger guards**  
   On normal buy/sell/DCA/rebalance paths, the system MUST reject (hard block) sells that would drive share balance negative and buys that would drive settlement cash negative. Opening snapshots and explicit corrections MAY set balances that would otherwise be unreachable only when the user is editing historical state intentionally; the UI MUST make that path distinct from day-to-day trade entry.

6c. **Corporate actions from data sources (partial automation)**  
   Current price fetch only loads 单位净值; NAV already reflects ex-dividend drops but **does not change share counts**. akshare can supply per-fund **拆分详情** and **分红送配详情** (e.g. `fund_open_fund_info_em` indicators, or `fund_cf_em` / `fund_fh_em`).  
   - **Splits / 折算**: system MAY auto-create reviewable `corporate_action` ledger legs that multiply shares by the published ratio on the effective date for symbols held that day.  
   - **Dividends**: system applies using a **user default policy** (cash → increase settlement cash by shares×per-unit dividend; or reinvest → increase shares by cash/NAV estimate). The market feed cannot know the user’s broker election, so defaults + correction UI are mandatory.  
   - Application runs on Refresh prices / explicit “Sync corporate actions”; never silently rewrite without a visible entry. Failed or ambiguous events stay listed for manual resolution.  
   - **Idempotency**: sync MUST NOT duplicate legs for the same `(symbol, action_kind, effective_date)` (or equivalent natural key); re-sync updates or skips existing applied actions.

7. **Single-config path reuses validation/reporting pipeline**  
   Factor shared “validate one config → write artifacts + reports” from sweep’s locked path; sweep continues to search the space then calls the same writer. UI「试跑」→ single-config;「全面验证」→ `run_sweep` into a fresh `run_id` dir.

7b. **Chart data via artifacts, not UI re-simulation**  
   Persist from `SimulationResult.daily_values` (and derived drawdown) into e.g. `artifacts/equity_curve.json` with `schema_version`, dates, NAV/equity levels, and drawdown fraction series. Optionally emit `artifacts/stress_summary.json` listing scenario id, key metrics, and pass/review/fail classification for table/traffic-light UI. Workbench charts **read these files only**. Charting library: NiceGUI-friendly (ECharts or Plotly)—implementation choice. Stress UI defaults to sortable table + color status; optional bar chart is non-blocking polish.

8. **Guidance: quadrant gate, then instrument split**  
   - Gate: any quadrant absolute drift vs locked `rebalance_threshold`. **Also** surface 闲钱归位 when settlement cash is **material** and the cash sleeve is under target—even if other quadrants are within threshold.  
   - **Material idle cash (v1)**: settlement cash > **max(1% of total portfolio value, 1000 CNY)** (using current marks). Below that, do not alert solely for idle cash.  
   - When open: target each instrument to `total_value × instrument_weight` from the **lock snapshot**.  
   - Spend **settlement cash** first toward underweight instruments (pro-rata by buy need), **prioritizing the cash-sleeve instrument when it is underweight and settlement cash is available**.  
   - Then sell overweight instruments **pro-rata by overweight value within the portfolio** (each overweight symbol sells in proportion to how far it is above its own target). Prefer selling non-QDII before QDII when both are overweight by a material amount (stable rule: sort overweight sells with QDII last).  
   - Buy remaining underweights pro-rata.  
   - QDII caps: annotate warnings only.  
   - Amounts ignore fees and minimum purchase sizes; UI labels guidance as approximate.

8b. **Backtest capital is illustrative in v1**  
   Single-config and sweep continue to use engine constants (`BASE_CAPITAL`, `MONTHLY_CONTRIBUTION`, etc.). The workbench MUST disclose that backtest NAV/path charts are **illustrative engine defaults**, not the user’s live portfolio size. Exposing custom capital/DCA amount in the UI is deferred.
9. **Live vs backtest rebalance schedule**  
   Backtest strategy may check annually; workbench guidance is **on-demand**. Threshold semantics match the locked threshold; calendar schedule does not.

10. **Prices for marks and guidance (automatic, not user-typed)**  
    Users enter trades/shares only; they do **not** manually maintain NAVs. Marks and guidance use the same price-loading path as the engine (akshare + on-disk cache).  
    UX: load cached marks quickly when opening holdings/guidance; show **as-of date** per quote set; provide an explicit **Refresh prices** action to re-fetch/update cache. Missing symbols → incomplete guidance, no invented prices. No background daemon required in v1 (refresh on view + on demand).

11. **Package layout**  
    `lock_registry`, `ledger`, `rebalance_guidance`, `single_run` (or careful extract from `sweep.py`), thin `ui` package; entry `quadbalance-ui`.

12. **Background runs vs ProcessPoolExecutor**  
    Sweep already uses a process pool. UI invokes engine APIs on a **dedicated worker thread** (or async wrapper) with a mutex; progress = coarse stage logs (start/config batch/complete), not per-process UI callbacks in v1. Do not nest a second process pool from the UI layer. Cancellation is out of scope for v1. Verify NiceGUI + Python 3.14 compatibility during dependency add (spike if install fails).

## Risks / Trade-offs

- [Long sweep blocks UX] → Progress/logs + disable double-submit; single-config path for iteration.  
- [Guidance differs from simulator tick-by-tick] → Document as advisory; fixed split rules + unit tests on toy portfolios.  
- [Price staleness] → Show as-of date; refuse complete guidance if required prices missing.  
- [Run dir deleted but lock remains] → Strong snapshot keeps targets; artifact viewers show “run files missing”.  
- [Settlement vs sleeve cash confusion] → Explicit UI labels and ledger types; tests for weight math; guidance deploys idle settlement into underweight cash sleeve.  
- [Dividend election unknown] → User default policy + correctable corporate-action entries; do not invent broker settings.  
- [SQLite cwd confusion] → Default `./data/quadbalance.db`; document backup.  
- [Process pool + UI] → Worker thread + coarse logs; no cancel in v1.  
- [Scope creep] → Slice A (run+lock+run_id) before Slice B (ledger+guidance).

## Migration Plan

- Additive: existing CLI `quadbalance` unchanged in default behavior (may still write `output/`).  
- Workbench always uses `output/<run_id>/`.  
- New NiceGUI dependency; empty SQLite on first launch; gitignore `data/`.  
- Rollback: stop using UI; engine and CLI remain valid.

## Open Questions

- Whether “force preview within threshold” ships in v1 or later (default remains threshold-gated either way)—**defer to later** unless implementation is trivial.  
- Profile threshold override UX (simple fields vs JSON paste)—implement minimal JSON/file path reuse from CLI for v1 if full form is costly.  
- Custom backtest capital / monthly contribution in the UI—**deferred**; v1 uses engine constants with an illustrative disclaimer.
