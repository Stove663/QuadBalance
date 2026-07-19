## 1. Ranking: same-return pending preference

- [x] 1.1 Extend `lock_selection.prefer_lock_candidate` (and bundle normalization) to carry `pending_cash_days` and prefer lower pending when `|Δ annualized_return| < RETURN_EDGE_BP` (reuse 50bp constant)
- [x] 1.2 Document pending preference in ranking keys surfaced to reporting (`reporting_sections` / lock selection notes)
- [x] 1.3 Unit tests: near-tie return → lower pending wins; ≥50bp return edge → higher return may win

## 2. Shortlist builder

- [x] 2.1 Add `lock_shortlist.py` (or equivalent) implementing roles `primary`, `max_return_contrast`, `step_down` per design D2 (top band = within 50bp of max soft-pass return; step-down = `25-25-25-25`)
- [x] 2.2 Pros/cons helper: shared universal material reviews vs differential metrics (return, pending, split, unrecovered/S14 extras)
- [x] 2.3 Unit tests: B2-style primary over B3 when inside edge; contrast = max return same allocation; step-down forced `25-25`; omit contrast when identical to primary

## 3. Artifacts

- [x] 3.1 Write `lock-shortlist.json` with `schema_version` and per-role fields (`config_id`, metrics, `lockable: false`, material reviews, pros/cons)
- [x] 3.2 Write `lock-shortlist.md` human companion from the same payload
- [x] 3.3 Wire artifact paths into sweep output dir helpers / constants

## 4. Sweep + CLI lock path

- [x] 4.1 When natural `lockable` is empty after LT attempts, build shortlist from soft-passes and write artifacts instead of auto-locking a single soft-pass on sign-off alone
- [x] 4.2 Add CLI `--lock-config-id` (with existing `--sign-off-reviewer` / `--sign-off-rationale`) to pick shortlist/passing row, run single-config fill if needed, then activate lock only if `lockable`
- [x] 4.3 Ensure shortlist membership never sets `lockable` or writes active `strategy-lock.md` without pick + lockable gate
- [x] 4.4 Integration-style test: fake soft-pass pool → shortlist files present, no active lock; then pick + sign-off → lock written

## 5. Verify

- [x] 5.1 Run targeted pytest for lock selection + shortlist
- [x] 5.2 Smoke: optional dry-run against existing `output/sweep_results.csv` logic (or fixture) to confirm three roles populate for return-seeking shape
