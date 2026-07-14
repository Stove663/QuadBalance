## 1. Stock Sub-Split Configuration

- [x] 1.1 Add stock sub-split variant type and weight mapping (60/40, 50/50, 40/60) to config/asset universe helpers
- [x] 1.2 Extend `StrategyConfig` with `stock_sub_split`, include it in `config_id`, and resolve instrument/QDII weights from the config instance
- [x] 1.3 Expand `generate_sweep_configs()` to include all three stock sub-split variants
- [x] 1.4 Add `stock_sub_split` field to sweep CSV rows and strategy-lock reporting
- [x] 1.5 Add unit tests for distinct config IDs and instrument target weights per sub-split

## 2. Profile Threshold Overrides

- [x] 2.1 Add loader that deep-merges JSON threshold overrides onto built-in `DEFAULT_INVESTOR_PROFILES`
- [x] 2.2 Validate profile ids and known numeric fields; fail fast on unknown profile ids
- [x] 2.3 Thread effective profiles through suitability classification, sweep, and reporting
- [x] 2.4 Add CLI `--profile-thresholds PATH` flag
- [x] 2.5 Disclose effective/overridden thresholds in strategy-lock.md
- [x] 2.6 Add tests for merge behavior and classification changes under stricter overrides

## 3. Deterministic Lock Selection

- [x] 3.1 Replace first-pass selection with multi-key comparator: suitability rank (if intended profile), return, |MDD|, QDII fill rate, config_id
- [x] 3.2 Ensure no-intended-profile path skips suitability rank and still yields a stable lock
- [x] 3.3 Document ranking keys in strategy-lock.md selection notes
- [x] 3.4 Add tests covering ties at each key and lexicographic final tie-break

## 4. Simulation Events for Artifacts

- [x] 4.1 Extend simulator (or lifecycle path used for lock) to emit a structured chronological event list
- [x] 4.2 Cover base position, DCA, rebalance, pending-cash, and lifecycle withdrawal/liquidity events needed by specs
- [x] 4.3 Add tests asserting event ordering and key fields for a small fixture simulation

## 5. Run Artifact Bundle

- [x] 5.1 Add artifact writer module emitting `artifacts/config.json`, `events.json`, `metrics.json`, `suitability.json` with `schema_version: 1`
- [x] 5.2 Wire artifact emission into the successful run orchestration for the locked configuration
- [x] 5.3 Ensure CSV and markdown outputs continue to be produced unchanged in role
- [x] 5.4 Add tests that verify bundle presence, schema_version, and suitability parity with lock classifications

## 6. Validation

- [x] 6.1 Update or add integration coverage for sweep cardinality including stock sub-split column
- [x] 6.2 Run unit/integration test suite and fix regressions
- [x] 6.3 Run `openspec validate phase1-engine-polish --strict` (or project-equivalent) and resolve issues
