## Why

`uv run quadbalance --output output` evaluates every sweep candidate with the full validation stack. Long-term macro regime stress (LT1–LT3) alone costs ~9s per config and is currently run for all deep-validated candidates, even though existing specs already require LT only for the locked configuration and LT does not affect sweep ranking. Restoring staged evaluation removes wasted work and makes full sweeps practical again.

## What Changes

- Stage the sweep pipeline so each candidate runs expensive work only after cheaper gates pass:
  1. historical simulation + core metrics
  2. short-horizon / execution stress (S1–S21 family)
  3. acceptance / lock ranking
  4. long-term macro regime stress **only for the locked configuration**
- Stop running LT1–LT3 for every sweep candidate by default (restore behavior already required by `strategy-validation` / `long-term-macro-regime-stress`).
- Record a clear `validation_stage` (or equivalent) on each sweep row so screened-out vs deep-validated vs lock-path work is auditable.
- Optionally raise parallel worker utilization for the independent per-config stage (implementation detail; no CLI contract change required).

## Capabilities

### New Capabilities

- *(none)*

### Modified Capabilities

- `strategy-validation`: Require staged sweep evaluation; defer long-term macro regime stress until after primary validation and lock selection; keep LT out of ranking.
- `long-term-macro-regime-stress`: Clarify that synthetic LT path simulation runs for the locked configuration after short-horizon stress succeeds, not for the full candidate grid.

## Impact

- Primary code: `src/quadbalance/sweep.py` (`_run_one_config`, `run_sweep`)
- Reporting / lock path: ensure locked config still receives LT results for `strategy-lock.md` and artifacts
- Tests: sweep orchestration / lock-document integration tests that currently assume per-candidate LT
- Runtime: expected large reduction in wall time on full sweeps (LT dominates when all candidates pass the weak metric screen)
- No change to scenario definitions, acceptance thresholds, or lock ranking keys
