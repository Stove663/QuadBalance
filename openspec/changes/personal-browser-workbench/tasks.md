## 1. Dependencies and scaffolding

- [x] 1.1 Add NiceGUI dependency and a `quadbalance-ui` (or equivalent) console script entrypoint; verify install on the project’s Python version
- [x] 1.2 Create module stubs: lock registry, ledger, rebalance guidance, single-config runner, and `ui` package
- [x] 1.3 Default SQLite path `./data/quadbalance.db`; gitignore `data/`; document manual DB backup in README later

## 2. Run directories and single-configuration validation

- [x] 2.1 Add `output/<run_id>/` allocation helper for workbench runs (timestamp + short id)
- [x] 2.2 Extract or wrap shared “validate one config → artifacts + reports” logic from the sweep lock path
- [x] 2.3 Extend artifact writers to emit `equity_curve.json` (NAV/equity + drawdown series) and `stress_summary.json` when stress results exist
- [x] 2.4 Implement single-config entrypoint that skips full sweep enumeration and writes into a given run directory
- [x] 2.5 Ensure full sweep invoked from the workbench also writes into a fresh `run_id` directory (CLI default may remain `output/`)
- [x] 2.6 Add tests for artifact presence/schema_version parity including equity-curve and stress-summary fields

## 3. Strategy lock registry

- [x] 3.1 Implement SQLite schema and helpers for append-only locks with single `is_active`
- [x] 3.2 Persist self-contained snapshot (weights, instruments, threshold, metrics/suitability summary) plus `run_dir`
- [x] 3.3 Support locking preferred or user-selected **passing** `config_id`; if artifacts missing, run single-config before activate; reject non-passing locks
- [x] 3.4 Add tests for relock archiving, snapshot targets without re-run, graceful missing `run_dir`, and non-passing lock rejection

## 4. Personal ledger

- [x] 4.1 Implement ledger entry types: opening, buy, sell, DCA, rebalance, settlement-cash movement, corporate_action
- [x] 4.2 Distinguish settlement cash vs cash-sleeve fund shares in reconstruction and totals
- [x] 4.3 Implement opening snapshot bootstrap and ordered position reconstruction
- [x] 4.4 Implement edit/delete corrections with holdings recomputed from the updated entry set
- [x] 4.5 Hard-block ordinary-path oversell and cash-insufficient buys; keep opening/correction paths distinct
- [x] 4.6 Fetch akshare split/dividend details; sync corporate_action entries idempotently (splits by ratio; dividends per user cash/reinvest default)
- [x] 4.7 Add tests for opening/buy/sell/corrections/guards, settlement vs sleeve, corporate-action idempotency, and no auto-import of artifact events

## 5. Rebalance guidance

- [x] 5.1 Compute actual vs target quadrant weights including settlement cash in total value
- [x] 5.2 Gate actionable alerts on locked `rebalance_threshold` (quiet within threshold; on-demand, not annual calendar)
- [x] 5.3 Surface 闲钱归位 when settlement cash > max(1% of portfolio, 1000 CNY) and cash sleeve is underweight (even if other quadrants are within threshold)
- [x] 5.4 Implement split rules: settlement cash first (cash-sleeve priority); pro-rata buys; pro-rata overweight sells with QDII last; approximate shares
- [x] 5.5 Handle missing prices, missing active lock, and QDII warnings-only
- [x] 5.6 Add unit tests for threshold silence/alert, immaterial idle cash, cash-first, cash-sleeve deploy, and toy multi-instrument split lists

## 6. NiceGUI workbench (Slice A)

- [x] 6.1 Build config/profile form mapped to engine parameters and intended profile
- [x] 6.2 Wire full sweep and single-config run on a worker thread with coarse logs, concurrency guard, and per-`run_id` output (no cancel-in-flight required)
- [x] 6.3 Build results view from artifacts + reports; NAV and drawdown charts from equity_curve with illustrative-capital disclaimer; stress as table/traffic lights; explicit empty state when no config passed
- [x] 6.4 Wire lock preferred / alternate **passing** config (single-config prefetch when needed) into the lock registry

## 7. NiceGUI workbench (Slice B)

- [x] 7.1 Build opening snapshot + ledger entry forms with edit/delete; holdings and drift view (label settlement cash vs cash sleeve)
- [x] 7.2 Wire automatic marks (cache-first) with as-of date and Refresh prices; no manual NAV entry
- [x] 7.3 Wire corporate-action sync + dividend default (cash vs reinvest) settings
- [x] 7.4 Build rebalance guidance panel (threshold-gated alert, 闲钱归位, sell/buy list)
- [x] 7.5 Smoke-test end-to-end:试跑 → lock → opening/trades → refresh/sync → guidance when drifted

## 8. Docs and packaging polish

- [x] 8.1 Document UI start, `output/<run_id>/`, `./data/quadbalance.db` backup, settlement vs cash-sleeve, and dividend default in README
- [x] 8.2 Confirm CLI `quadbalance` remains usable for existing workflows
