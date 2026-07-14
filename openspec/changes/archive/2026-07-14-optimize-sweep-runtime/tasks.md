## 1. Staged Sweep Evaluation

- [x] 1.1 Add a sweep evaluation mode that runs baseline simulation, metrics, suitability, and fast stress for all candidate configurations
- [x] 1.2 Add shortlist selection logic that ranks fast-pass candidates before running full stress
- [x] 1.3 Run exact full stress only for shortlisted candidates and the final lock candidate by default
- [x] 1.4 Ensure the final strategy-lock document and run artifacts are generated from exact full-stress validation results
- [x] 1.5 Add tests proving non-shortlisted candidates do not run S4/S5/S7 exact stress simulations

## 2. Deferrable No-Rebalance Premium

- [x] 2.1 Add an option to skip no-rebalance simulation during broad sweep screening
- [x] 2.2 Preserve `rebalance_premium` output semantics when no-rebalance simulation is enabled or deferred and later computed
- [x] 2.3 Compute no-rebalance premium for shortlisted candidates or the final lock candidate when required by reporting
- [x] 2.4 Add tests covering skipped, deferred, and exact no-rebalance premium behavior

## 3. S4 Window-Scoped Path Evaluation

- [x] 3.1 Add an explicit S4 evaluation mode for full-history exact path simulation versus window-scoped simulation
- [x] 3.2 Implement window-scoped S4 using only the selected low-rate window when that mode is enabled
- [x] 3.3 Record the S4 evaluation mode in validation or reporting output so results are auditable
- [x] 3.4 Add tests comparing exact and window-scoped S4 behavior on controlled price data

## 4. Approximate S5/S7 Exploratory Stress

- [x] 4.1 Add a stress mode option with exact and approximate values
- [x] 4.2 Implement approximate S5 QDII premium impact estimation without rerunning the full simulation
- [x] 4.3 Implement approximate S7 low-quota impact estimation from existing QDII metrics without rerunning the full simulation
- [x] 4.4 Ensure approximate stress results are not used for final exact lock validation unless explicitly configured
- [x] 4.5 Add tests verifying exploratory approximate stress avoids extra simulations and final validation uses exact stress

## 5. Simulation Result Reuse

- [x] 5.1 Define a stable simulation cache key for config, rebalance mode, stress variant, and relevant simulation options
- [x] 5.2 Add per-sweep simulation result reuse for baseline, no-rebalance, S5, S7, and S4 variants where inputs are equivalent
- [x] 5.3 Ensure cached results do not leak across incompatible price matrices, backup prices, or mode settings
- [x] 5.4 Add tests proving repeated equivalent simulation requests reuse cached results and incompatible requests do not

## 6. Verification

- [x] 6.1 Add or update unit tests for sweep runtime modes and stress mode selection
- [x] 6.2 Add regression tests ensuring final exact validation results match pre-optimization behavior for default full mode
- [x] 6.3 Run the existing test suite
- [x] 6.4 Document runtime mode defaults in code-level help or CLI-facing configuration if applicable
