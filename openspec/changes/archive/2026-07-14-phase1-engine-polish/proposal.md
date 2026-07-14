## Why

Phase 1 core engine is functionally complete, but several MVP gaps remain hard-coded: Stocks domestic/QDII sub-split is fixed at 60/40, investor profile thresholds cannot be overridden, strategy-lock tie-breaking among passing candidates is underspecified beyond a single rank bump, and run outputs are not yet shaped as stable intermediate artifacts for later GUI and ledger phases. Closing these now keeps the engine modular without starting Phase 2/3 UI work.

## What Changes

- Add Stocks quadrant domestic/QDII sub-split variants to the parameter sweep (at least 60/40 default, 50/50, and 40/60), with configuration IDs and strategy-lock disclosure reflecting the chosen split.
- Make investor profile thresholds loadable/overridable (file or CLI), keeping current defaults as built-in baseline.
- Refine suitability-aware strategy lock selection with an explicit, deterministic multi-key ranking when multiple configurations pass validation.
- Emit stable intermediate run artifacts (structured snapshots of config, trades/cashflows, metrics, and suitability) suitable for future ledger ingestion and GUI consumption, while keeping CSV + markdown as the primary human-facing Phase 1 outputs.

## Capabilities

### New Capabilities

- `run-artifacts`: Define stable intermediate artifact schemas and emission rules for a validation run (configuration snapshot, simulation ledger-like events, metrics, suitability) so later GUI/ledger phases can ingest without rewriting the engine.

### Modified Capabilities

- `asset-universe`: Treat Stocks domestic/QDII sub-split as a sweepable parameter with documented variants; default remains 60/40.
- `investment-strategy`: Allow investor profile threshold overrides; treat stock sub-split as a locked mechanical parameter when selected.
- `portfolio-backtest`: Simulate each stock sub-split variant; ensure config identity includes the split; support emission of intermediate artifacts.
- `strategy-validation`: Expand sweep coverage and lock-document fields for stock sub-split; refine multi-pass lock selection ranking; evaluate suitability using effective (default or overridden) profile thresholds.

## Impact

- Code: `asset_universe.py`, `config.py`, `sweep_space.py`, `sweep.py`, `simulator.py`, `profile_thresholds.py`, `metrics.py`, `validation.py`, `reporting.py`, `cli.py`, and related tests.
- CLI: options for intended-profile (existing), profile-threshold overrides, and artifact output directory/format flags as needed.
- Outputs: existing `sweep_results.csv` / `strategy-lock.md` extended; new intermediate artifact files under `output/` (or a dedicated artifacts subdirectory).
- Non-goals: no GUI, no production ledger accounting, no change to Phase 2/3 product scope beyond preparing ingestible artifacts.
