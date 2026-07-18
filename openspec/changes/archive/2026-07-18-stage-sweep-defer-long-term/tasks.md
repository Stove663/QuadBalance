## 1. Sweep orchestration

- [x] 1.1 Remove `run_long_term_stress_tests` from the per-candidate `_run_one_config` deep path so workers never run LT1–LT3 by default
- [x] 1.2 After lock selection in `run_sweep`, run LT1–LT3 once for the locked configuration and attach `validation.long_term_results` before lock document / artifact generation
- [x] 1.3 Ensure sweep rows still record `validation_stage` for screened-out vs deep-validated candidates
- [x] 1.4 Raise `ProcessPoolExecutor` worker cap from the hard-coded 4 toward CPU count with a modest safety ceiling

## 2. Tests

- [x] 2.1 Add/adjust unit or integration tests proving non-locked candidates do not invoke long-term stress by default
- [x] 2.2 Add/adjust tests proving a locked configuration receives LT1–LT3 results for strategy-lock reporting
- [x] 2.3 Confirm existing acceptance / ranking tests still ignore LT outcomes when choosing the locked config

## 3. Verification

- [x] 3.1 Run targeted pytest for sweep / lock / long-term reporting
- [x] 3.2 Smoke `uv run quadbalance --output output` and confirm wall time drops vs pre-change behavior while lock docs still include Long-Term Macro Regime Stress when a lock exists
