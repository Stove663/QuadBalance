## Why

Phase 1 already delivers sweep validation, strategy lock documents, and machine-readable run artifacts, but the only way to use them is the CLI. For a single personal user trying to find and then *follow* a suitable four-quadrant portfolio, that friction is high: every tune requires shell commands, lock history is overwrite-prone files, and there is no place to record real buys/sells or get threshold-based rebalance guidance aligned with the locked strategy.

## What Changes

- Add a **local NiceGUI browser workbench** (no accounts, localhost) to configure investor profile and strategy parameters, run validation without the CLI, and review lock / suitability / sweep results.
- Write each workbench run to **`output/<run_id>/`** so prior artifacts and lock references are not overwritten; locks also store a **self-contained config+instrument snapshot**.
- Add a **single-configuration validation path** so parameter tweaks can complete faster than a full sweep while emitting the same artifact shape.
- Persist an **immutable strategy-lock history** in SQLite: each new lock archives the previous active lock; active lock defines the live target portfolio; user may lock the preferred sweep candidate **or** another **passing** config from that run (running single-config first when that row lacks full artifacts). Non-passing configs are not lockable.
- Backtest paths use **engine default capital/contribution** in v1 with an on-screen illustrative disclaimer; custom capital in the UI is deferred.
- Add a **personal ledger** of amount + fund share flows (including **opening snapshot**, buy / sell / DCA / rebalance, and **settlement cash** distinct from the cash-sleeve fund) sufficient to reconstruct holdings; simulated backtest events never auto-write into the ledger. **NAVs/prices update automatically** via the engine price path (cache-first, as-of date, optional Refresh); users do not maintain prices by hand.
- Support **ledger corrections** (edit/delete entries) so mistaken trades can be fixed without rebuilding the database. Ordinary trade paths **hard-block** oversell and cash-insufficient buys.
- Apply **fund corporate actions** using akshare dividend/split feeds where possible: splits adjust shares automatically (with reviewable system entries); dividends apply per a user default (cash vs reinvest) because the data source cannot know the broker account’s payout election—user may correct. Sync is **idempotent** on `(symbol, action_kind, effective_date)`.
- Add **rebalance guidance**: compare ledger holdings (marked at current prices) to the active lock’s target weights; **by default alert only when any quadrant deviation exceeds the locked rebalance threshold**, then show concrete sell/buy amounts (and approximate shares) using a documented instrument-split rule (settlement cash first—including **deploying idle settlement cash into the cash-sleeve when that sleeve is underweight** and cash is **material**: `> max(1% of portfolio, 1000 CNY)`; approximate, fees ignored). Optional force-preview may exist later; default remains threshold-gated.
- Add **validation result charts** in the workbench (Slice A): backtest **NAV/equity curve** and **drawdown curve** for the evaluated/locked configuration, fed from exported series artifacts—not by re-running simulation in the UI. Stress-test outcomes remain primarily **tables / traffic-light summaries** (optional simple bar comparison later); live ledger market-value history charts are deferred.
- Update project scope language: Phase 2 is this personal browser workbench (research + minimal ledger + guidance), not a GUI shell deferred indefinitely from ledger work. No live brokerage integration or automated trading.

## Capabilities

### New Capabilities

- `browser-workbench`: Local NiceGUI app for profile/config forms, full sweep and single-config runs with progress/logs, result viewing from run artifacts and human reports, including NAV and drawdown charts and tabular stress summaries.
- `strategy-lock-registry`: SQLite-backed immutable lock history and a single active lock that anchors live targets for ledger and guidance.
- `personal-ledger`: Amount + share entry ledger (including opening snapshot and corrections), settlement vs cash-sleeve, automatic marks, corporate-action application from market data with user-correctable defaults, position reconstruction, and drift display versus the active lock.
- `rebalance-guidance`: Threshold-gated rebalance suggestions (sell what/how much, buy what/how much) from holdings, prices, and locked targets.
- `single-config-validation`: Engine API to validate one `StrategyConfig` (plus profile options) and write the same artifact/report contract as a locked sweep path, without scanning the full sweep space.

### Modified Capabilities

- `investment-strategy`: Revise phased-scope requirements so GUI + minimal ledger are in-scope Phase 2 deliverables via the personal workbench, while keeping no brokerage automation.
- `run-artifacts`: Add equity/NAV and drawdown series artifacts (and optional compact stress summary JSON) so the workbench can chart and tabulate without re-simulating.

## Impact

- New dependency: NiceGUI (and SQLite via stdlib or a thin helper).
- New package surface under `src/quadbalance/` for lock registry, ledger, guidance, and single-config runner; NiceGUI entrypoint (e.g. `quadbalance-ui` or similar).
- Reuses existing `run_sweep`, `StrategyConfig`, profile thresholds, and `artifacts/` JSON; extends artifacts with equity/drawdown series for charts; must not rewrite the core simulator for UI concerns.
- Data layout: workbench runs under `output/<run_id>/`; locks and ledger in `./data/quadbalance.db` (gitignore `data/`).
- Tests for lock immutability, strong snapshots, settlement vs cash-sleeve math, opening bootstrap, threshold gating + instrument split rules, equity-curve artifact presence, and single-config artifact parity.
