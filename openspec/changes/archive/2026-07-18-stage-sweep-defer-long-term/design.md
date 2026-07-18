## Context

`run_sweep` already parallelizes per-config work with `ProcessPoolExecutor`, and `_run_one_config` already has a weak metric screen before stress. After that screen, however, every surviving candidate still:

1. runs full short-horizon stress (`run_stress_tests`)
2. runs `evaluate_acceptance`
3. runs `run_long_term_stress_tests` (LT1–LT3) unconditionally when `screening_only=False`

Microbenchmarks on cached data (~1973 trading days) show approximate costs per candidate:

| Stage | ~seconds |
|-------|----------|
| `simulate` + metrics | 0.8 |
| full stress (incl. S4/S5/S7 resims) | 2.4 |
| LT1–LT3 | 8.9 |

On recent full sweeps the metric screen passes essentially all candidates, so LT dominates wall time. Existing main specs already require LT for the locked configuration only and forbid using LT to change ranking; current code drifted from that contract.

## Goals / Non-Goals

**Goals:**

- Restore deferred LT: run LT1–LT3 once for the locked configuration after primary validation + short-horizon stress succeed for that config.
- Keep per-candidate path as: simulate → metrics → (optional early screen) → stress → acceptance row.
- Preserve lock document / artifact content for LT when a lock exists.
- Keep sweep ranking independent of LT outcomes.
- Record stage metadata on sweep rows for auditability.
- Raise worker utilization where safe (same machine, independent configs).

**Non-Goals:**

- Rewriting / vectorizing `simulate()` (separate performance change).
- Changing stress scenario definitions, thresholds, or acceptance criteria.
- Changing lock selection keys.
- Shrinking the sweep grid.
- Making LT part of pass/fail for sweep ranking.

## Decisions

### 1. Defer LT to post-lock, not “every stress-passing candidate”

Run LT only for the configuration selected by `prefer_lock_candidate` after the parallel sweep finishes.

Rationale: matches existing specs; maximizes prune (1 LT run vs N); user intent (“only after backtest + stress pass”) is satisfied because lock selection already requires primary validation success, which includes short-horizon stress.

Alternatives considered:

- Run LT for every candidate that passes stress: still correct staging, but can remain expensive if many pass.
- Run LT for top-K by return: faster than all-passers, but arbitrary and not required by lock semantics.

### 2. Remove LT from `_run_one_config` worker path

Workers return stress/acceptance results without calling `run_long_term_stress_tests`. After the best lock bundle is chosen, the parent process runs LT once and attaches `validation.long_term_results` before lock document generation.

Rationale: avoids shipping LT work through every process; keeps pickle/CPU load lower; single deterministic attach point for reporting.

Alternatives considered:

- Keep LT inside worker gated by a flag: more complex payload; still risks accidental enablement for all configs.

### 3. Keep the existing metric screen; do not invent a stricter screen in this change

Leave early metric thresholds as-is. Speed win comes from LT deferral, not from rejecting more candidates.

Rationale: tighter screens can change which configs reach stress/lock and need separate product discussion. Specs already cover staged intent via lock-only LT.

### 4. Worker count: use CPU count with a modest ceiling

Replace `min(4, cpu_count)` with something like `min(cpu_count or 2, 8)` (or env override if already patterned elsewhere). Document that prices are still pickled per task; shared-memory initializer is out of scope unless profiling shows serialize cost dominates after LT deferral.

Rationale: machine often has >4 cores; LT deferral already removes the heaviest work, so raising workers is a cheap secondary win.

### 5. Stage labels on sweep rows

Ensure each row records a stage such as `screened-out` vs `deep-validated` (existing field intent). Lock-path LT is not a per-row stage; it belongs on the lock validation object / artifacts.

## Risks / Trade-offs

- [No config passes validation] → No LT artifacts / lock LT section. Acceptable; same as today when no lock is written.
- [Tests assume per-candidate LT] → Update orchestration tests to assert LT runs once post-lock.
- [Higher worker count increases RAM] → Cap workers; prices payload ~0.35MB each is small vs sim CPU.
- [Someone wants LT comparison across all passers] → Out of scope; would need an explicit `--full-long-term` flag later.

## Migration Plan

1. Stop calling `run_long_term_stress_tests` inside per-config deep path.
2. After lock selection, run LT for locked config and attach results before `generate_lock_document` / artifact writers.
3. Adjust tests; run targeted pytest then a full `uv run quadbalance --output output` smoke.
4. Rollback: re-enable per-config LT call (not recommended).

## Open Questions

- None blocking implementation. Optional follow-up: `--full-long-term` for research sweeps.
