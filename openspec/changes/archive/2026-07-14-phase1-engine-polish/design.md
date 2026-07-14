## Context

Phase 1 MVP already sweeps allocation / bond / DCA / rebalance dimensions, classifies investor-profile suitability, and locks a passing configuration. Remaining polish gaps are hard-coded Stocks sub-weights (`STOCK_SUB_WEIGHTS = 60/40`), built-in-only profile thresholds, incomplete lock tie-breaking (only suitability rank bump when `--intended-profile` is set), and report outputs that are human-readable but not yet shaped as stable machine intermediates for later GUI/ledger phases.

## Goals / Non-Goals

**Goals:**

- Make Stocks domestic/QDII sub-split a first-class sweep parameter (60/40, 50/50, 40/60).
- Allow profile-threshold overrides for a run while keeping built-in defaults as baseline.
- Define and implement deterministic multi-key lock selection among primary-passing configs.
- Emit versioned JSON intermediate artifacts for locked-run config, events, metrics, and suitability.

**Non-Goals:**

- Building a GUI or production ledger UI.
- Changing primary instruments or adding new asset classes.
- Expanding lifecycle scenario set beyond what suitability already uses.
- Replacing CSV/markdown reports.

## Decisions

### 1. Stock sub-split modeled on `StrategyConfig`

- Add `stock_sub_split: Literal["60-40", "50-50", "40-60"]` (or equivalent) on `StrategyConfig`.
- Resolve to concrete domestic/QDII weights via a small mapping table; default `"60-40"`.
- Include a short token in `config_id` (e.g. `_s60-40`) so IDs remain unique across the new dimension.
- Route all weight resolution (`instrument_weights`, `qdii_target_weight`, `sub_weight`) through the config instance rather than the global constant alone.
- Keep module-level `STOCK_SUB_WEIGHTS` as the default variant mapping for backward-compatible imports.

**Alternatives considered:** global monkey-patch of `STOCK_SUB_WEIGHTS` during sweep — rejected because it is not concurrency-safe and hides config identity.

### 2. Sweep cardinality

- Add the three stock-split variants to `generate_sweep_configs()`.
- Accept the 3× increase in sweep size; no sampling for MVP unless runtime becomes painful in practice.
- Add an explicit `stock_sub_split` column on `SweepRow` / CSV.

**Alternatives considered:** only lock-candidate subsample for stock splits — rejected because comparative QDII friction analysis needs full coverage.

### 3. Profile threshold overrides

- Keep `DEFAULT_INVESTOR_PROFILES` immutable.
- Load optional YAML/JSON override file via CLI (e.g. `--profile-thresholds PATH`) that deep-merges numeric fields (`min_real_return`, `max_drawdown`, `max_underwater_years`, QDII friction/recovery limits) by `profile_id`.
- Pass effective `tuple[InvestorProfile, ...]` through sweep/validation/reporting rather than reading globals ad hoc.
- Record effective thresholds in lock document and artifacts.

**Alternatives considered:** environment variables per field — rejected as brittle; full profile replacement files — accepted as the file format, with merge semantics so partial overrides work.

### 4. Lock selection ranking

Documented key order:

1. Suitability rank for intended profile (only if provided): suitable=2, caution=1, unsuitable=0
2. Higher annualized return
3. Lower absolute maximum drawdown
4. Higher QDII fill rate
5. Lexicographic `config_id` ascending

Replace `_select_first_pass` single-bump behavior with a comparator that walks all keys. First primary-passing candidate initializes the leader; every later passer competes.

**Alternatives considered:** Pareto front of return/drawdown — postponed; multi-key order is enough for deterministic MVP selection.

### 5. Run artifacts layout and schema

Emit under `{output}/artifacts/`:

| File | Contents |
|------|----------|
| `config.json` | Locked config + effective profile thresholds + schema_version |
| `events.json` | Chronological simulation events for locked config |
| `metrics.json` | Core/QDII/rebalance/lifecycle summary metrics |
| `suitability.json` | Per-profile classification, reasons, effective thresholds |

- `schema_version: 1` on every file.
- Prefer extracting event records from the existing simulator path (extend return value or a structured side channel) rather than parsing markdown.
- If full event capture needs a small simulator refactor, keep the public CLI UX unchanged.

**Alternatives considered:** single monolithic `run.json` — rejected for easier partial consumers; Parquet — deferred until ledger volume justifies it.

### 6. Module boundaries

| Concern | Module |
|---------|--------|
| Split variants + mapping | `asset_universe` / `config` |
| Sweep expansion | `sweep_space`, `sweep` |
| Threshold load/merge | `profile_thresholds` (+ small loader) |
| Lock ranking | `sweep` |
| Artifact writers | new `artifacts.py` (or `reporting` subdirectory helper) called from CLI/reporting orchestration |

## Risks / Trade-offs

- [3× sweep runtime] → Mitigation: keep caching; optional future `--stock-sub-split` filter flag if needed after measurement.
- [Event capture gaps if simulator only returns NAV frame] → Mitigation: add a structured event list in the simulation result in the same change.
- [Override files silently ignore unknown keys] → Mitigation: validate profile ids and known fields; fail fast on unknown profile ids.
- [Artifact schema churn before Phase 2] → Mitigation: explicit `schema_version` and additive-only evolution until v2.

## Migration Plan

1. Implement config/sweep/simulator changes; update unit tests for IDs and weights.
2. Implement threshold loader and thread effective profiles through classification.
3. Replace lock selection comparator; document keys in strategy-lock markdown.
4. Emit artifact bundle; keep existing CSV/markdown paths.
5. No data migration: prior `output/` files are overwritten by normal re-runs.

## Open Questions

- Should CLI expose `--stock-sub-split` to restrict sweep for faster iteration, or always run all three in MVP?
- Exact JSON event field names vs reuse of any existing internal trade log structures — finalize during implementation against simulator code.
- Whether override file format is YAML, JSON, or both for v1 (recommend JSON to match artifacts; YAML if already a dependency).
