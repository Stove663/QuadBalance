## Context

Post-hard-flaws sweeps commonly yield many `validation.passed` rows and **zero** naturally `lockable` configs: universal material reviews (CB1–CB3, path P1, S20, product) fire for every China 场外 + QDII sleeve. Today `sweep.py` ranks via `prefer_lock_candidate`, runs LT on at most three soft-passes, then either writes nothing or auto-locks the single best soft-pass when `--sign-off-*` is provided. Return-seeking users need a deliberate shortlist with friction tradeoffs, not a silent one-shot lock.

Stakeholders: personal lock consumers, CLI sweep operators, eventual workbench lock picker.

Constraints: keep `passed` vs `lockable` honesty; reuse existing sign-off + single-config fill paths; LT cost remains capped.

## Goals / Non-Goals

**Goals:**

- Build a fixed three-slot **return-seeking shortlist** when natural `lockable` is empty after sweep (+ optional LT attempts).
- Prefer lower QDII `pending_cash_days` when annualized return delta is within a small edge (align with existing 50bp stock-split edge unless tuned).
- Force a step-down allocation slot (`25-25-25-25` family) so users see the ~1pp return vs friction trade.
- Emit shortlist artifacts; lock only after explicit candidate pick + `lockable` (sign-off when material reviews remain).

**Non-Goals:**

- Demoting universal structural reviews to non-material / inventing natural `lockable`.
- Multi-profile shortlist engines (accumulation vs retirement) in v1 — v1 is return-seeking preference only; profile flag may still bias secondary sorts later.
- Auto-locking without user pick when shortlist path runs.
- Redesigning the asset universe to extinguish CB/product reds.

## Decisions

### D1: Shortlist runs only when natural lockable is empty

**Decision:** If any config is `lockable` after deep validation (+ LT veto handling), keep today’s behavior: lock that config (prefer_lock_candidate among lockables). Shortlist path activates only when the lockable set is empty and at least one soft-pass remains.

**Alternatives:** Always emit shortlist — noisier for rare clean locks; rejected for v1.

### D2: Three fixed roles (not top-3 by return)

**Decision:**

| Slot | Role | Selection rule (v1 return-seeking) |
|------|------|--------------------------------------|
| 1 | `primary` | Among soft-passes in the top return band (e.g. top quintile or within 50bp of max return), minimize `pending_cash_days`; apply existing split risk-budget when comparing splits |
| 2 | `max_return_contrast` | Max `annualized_return` in the **same allocation_name** as primary (bond/DCA/split may differ); skip if identical to primary |
| 3 | `step_down` | Best pending (then return) among soft-passes with allocation `25-25-25-25` and stock split matching primary’s split when available; else best `25-25-25-25` soft-pass |

Bond variants MUST NOT fill multiple slots solely by B1/B2/B3 differences unless they serve distinct roles above.

**Alternatives:** Pure Pareto front — harder to explain; rejected. Return/stable/middle triad — conflicts with user’s return preference; rejected for this preference profile.

### D3: Same-return pending preference in `prefer_lock_candidate`

**Decision:** When `|Δ annualized_return| < STOCK_SPLIT_RETURN_EDGE_BP` (0.50pp, reuse constant or shared `RETURN_EDGE_BP`), prefer lower `pending_cash_days`. Apply after lockable preference, alongside/after stock-split risk-budget as documented ranking keys.

**Alternatives:** Separate 20bp edge for pending — slightly tighter for B2 vs B3 (~16bp); optional tune. Default reuse 50bp for one knob.

### D4: Artifacts before lock document

**Decision:** Write `lock-shortlist.json` + `lock-shortlist.md` under the sweep output dir. Do **not** write active `strategy-lock.md` until user selects a shortlist `config_id` and the configuration becomes `lockable` (sign-off CLI/API). LT: run for shortlist members that lack LT results, still capped (reuse `MAX_LT_LOCK_ATTEMPTS` or expand to cover the three slots only).

**Alternatives:** Embed shortlist only in CSV columns — weak UX; rejected.

### D5: CLI pick path

**Decision:** Extend CLI: after sweep with shortlist, `--lock-config-id <id>` + `--sign-off-reviewer` / `--sign-off-rationale` activates lock for that shortlist (or other passing) row, running single-config fill when artifacts missing. Omitting pick leaves shortlist only (exit non-zero or clear “no lock” message — prefer clear message, exit 0 for sweep success with shortlist written).

**Alternatives:** Interactive TTY picker — defer to workbench; not v1 CLI.

### D6: Preference profile flag (stub)

**Decision:** v1 hard-codes return-seeking shortlist roles. Optional `shortlist_preference=return_pending` constant/flag for future `balanced` / `preservation` role sets without redesigning artifacts.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Step-down slot empty (no `25-25` soft-pass) | Fall back to next-lower stock weight / highest-cash passed row; document fallback in artifact |
| Max-return contrast ≈ primary (same row) | Omit slot 2 or mark `skipped`; still require slot 1 + 3 when possible |
| Users treat shortlist as “approved” | Integrity requirement: shortlist MUST state `lockable: false` per row until sign-off |
| LT cost for three configs | Cap LT to shortlist members only; parallel if already supported |
| Ranking thrash vs old prefer_lock_candidate | Keep lockable-first; pending tie-break only inside return edge |

## Migration Plan

1. Ship shortlist writers + ranking changes behind normal release.
2. Re-run sweep; expect `lock-shortlist.*` and no auto soft `strategy-lock.md` without `--lock-config-id` + sign-off.
3. Invalidate prior superseded locks already marked; user picks from new shortlist.
4. Rollback: revert to single prefer_lock_candidate + optional force sign-off lock.

## Open Questions

- Exact top-band definition: top quintile vs “within 50bp of max return”? **Default: within 50bp of max return among soft-passes** (simpler, matches edge constant).
- Should workbench UI pick land in this change or follow-up? **Follow-up OK; CLI pick sufficient for apply.**
