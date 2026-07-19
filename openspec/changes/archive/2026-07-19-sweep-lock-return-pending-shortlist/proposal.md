## Why

After `fix-portfolio-validation-hard-flaws`, every sweep soft-pass still carries universal material reviews (CB1–CB3, P1, S20, product), so natural `lockable` is zero and the engine either writes nothing or auto-locks a single soft-pass under sign-off. Return-seeking investors need an honest shortlist—not a silent single pick—so they can choose growth vs QDII cash friction with eyes open.

## What Changes

- After a deep sweep, when no configuration is naturally `lockable`, the system MUST build a **three-slot lock shortlist** instead of only preferring one soft-pass.
- Shortlist roles (return-seeking preference profile):
  1. **Primary** — highest-return band, among near-ties prefer lower `pending_cash_days`
  2. **Max-return contrast** — same allocation family peak return (shows what extra pending buys)
  3. **Step-down** — forced lower-friction allocation (e.g. equal-weight `25-25-25-25` with same stock split bias) so the user can trade ~1pp return for less QDII silt
- Same-family bond variants (B1/B2/B3) MUST NOT occupy multiple shortlist slots; keep friction-best + optional peak-return contrast only.
- Emit a shortlist artifact with per-candidate metrics, shared vs differential material reviews, and explicit pros/cons.
- Active strategy lock still requires `lockable` (material reviews empty **or** complete human sign-off). User picks one shortlist row, optionally runs single-config artifact fill, then signs off.
- **Non-goal:** Do not weaken material lock gates or invent natural `lockable` by demoting universal structural reviews.

## Capabilities

### New Capabilities

- `lock-candidate-shortlist`: Build, rank, and present the post-sweep three-slot lock shortlist (roles, tie-break, artifact shape, user pick → lock path).

### Modified Capabilities

- `strategy-lock-registry`: Lock-from-sweep path MUST allow selecting from the shortlist (not only engine-preferred single candidate); sign-off still required when material reviews remain.
- `strategy-lock-integrity`: Document that shortlist presentation does not imply `lockable`; lock write path unchanged (`passed` ≠ `lockable`).
- `stocks-subsplit-sweep`: Extend lock ranking keys with same-return pending-cash preference alongside existing stock-split risk-budget preference.
- `run-artifacts`: Require a machine-readable + human-readable shortlist artifact in the sweep run directory when the shortlist path runs.

## Impact

- Code: `lock_selection.py`, `sweep.py` lock finale, `cli.py` (pick/sign-off), reporting/artifacts writers, possibly workbench lock UX later
- Artifacts: new `lock-shortlist.md` / JSON; `strategy-lock.md` only after user pick + lockable
- Specs: new shortlist capability; deltas on registry, integrity, subsplit ranking, run-artifacts
- Behavior: sweeps with zero natural `lockable` stop auto-writing a lone soft lock without shortlist; CLI/API gains explicit candidate selection
