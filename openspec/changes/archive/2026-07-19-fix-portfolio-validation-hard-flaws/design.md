## Context

Locked config reports “green” while Criterion-3 reviews stay open, QDII fill reads 100% with chronic pending cash, suitability hardcodes perfect execution, and `effective_start` is still `2018-06-08`. Archive change `qdii-backup-price-matrix` already specified backup-excluded alignment and code has `PRICE_MATRIX_SYMBOLS` + `load_backup_prices`, but `collect_required_symbols()` still unions `simulation_symbols()` (QDII pool including `050025`/`006075`) into the **alignment** matrix — regression recreates the truncation.

Stakeholders: strategy lock consumers, suitability UI, sweep ranking, retirement/lifecycle stress readers.

## Goals / Non-Goals

**Goals:**

- Restore `effective_start` ≤ 2013-08-01 for primary/lock paths
- Make lock eligibility honest: material reviews or `seq_inflation` thesis-broken cannot silently ship as ready
- Suitability and QDII gates use measured execution friction
- Risk Overview color semantics match Risk Map for cross-border / path layers
- Behavior stress can fire on non-historical deep paths
- Simulation fidelity: OTC settlement lag + short-hold redemption
- Re-rank stocks sub-split under restored history with explicit risk-budget preference

**Non-Goals:**

- Redesigning quadrant target weights (20/25/30/25) in this change
- Full multi-fund shared QDII platform quota pooling
- Replacing all formula stresses with full path engines in one pass (label + escalate critical ones first)
- Personalized financial advice language beyond mechanical governance

## Decisions

### D1: Alignment symbols = primaries only (fix the regression)

**Decision:** `collect_required_symbols` (and single_run equivalent) MUST pass only primary/alignment symbols to `load_price_matrix*`. QDII backups load exclusively via `backup_symbols` / `load_backup_prices`. Add a hard assertion: intersection of alignment columns with `QDII_BACKUP_SYMBOLS` is empty.

**Alternatives:** Outer-join with NaN skip — rejected; already failed once via silent regression.

### D2: Two-tier lock gate — `passed` vs `lockable`

**Decision:** Keep `validation.passed` for metrics + `fail`/`thesis-broken` hard gates (existing Criterion 1–5 semantics). Introduce `lockable` (or equivalent):

1. `passed == true`
2. AND either `needs_review` empty of **material** findings, OR artifact records `human_signoff` (who, when, rationale, listed open items)

Material findings (block lock without sign-off):

- Any cross-border result `review-required` or worse
- Path stress P* `review-required` or worse
- Short-horizon S14/S15/S20 `review-required`
- Product-level worst `review-required`
- Unrecovered max drawdown at sample end
- Long-term `seq_inflation` `thesis-broken` (also see D3)

UI/CLI MAY still mark validation passed for inspection; strategy-lock write path REQUIRES `lockable`.

**Alternatives:** Fail `passed` on any review — too noisy for sweep ranking; rejected in favor of explicit lock gate.

### D3: `seq_inflation` thesis-broken escalates LT + vetoes lock

**Decision:** If any LT scenario’s sequence-risk profile `seq_inflation` is `thesis-broken`, that LT scenario classification MUST be at least `review-required` and MUST set a lock veto flag (`long_term_lock_veto` / include in material `needs_review`). Sweep lock selection MUST exclude vetoed configs unless human sign-off present.

**Alternatives:** Only surface in notes — status quo; rejected.

### D4: Real QDII inputs everywhere

**Decision:** `classify_suitability` callers MUST pass measured `qdii_fill_rate`, `avg_qdii_weight_gap`, pending-day / friction months from `sim_result.qdii_metrics`. Remove `1.0` / `0.0` defaults in validation acceptance path.

Add soft/hard QDII quality gates for lockable:

- Average |QDII weight gap| sustained > 2pp for ≥ 12 months → material review (already warned; promote)
- Pending-cash days > N (default 252) OR max post-rebalance deviation > threshold → material review
- Fill rate alone MUST NOT clear these gates

### D5: Risk Overview uses same severity source as Risk Map

**Decision:** Overview “Red” counts layers that Risk Map marks red (including CB non-normal with critical usability), not only `thesis-broken`. Document mapping in reporting. “未见明确红色风险” MUST NOT appear when any Risk Map layer is red.

### D6: Behavior stress — dual path

**Decision:** Keep historical behavior rules. ADD evaluation against path-stress / mechanism deep-drawdown proxies (at least P1 peak DD and S14 portfolio return as synthetic MDD surrogate) so rules can classify under deep stress even when historical MDD is shallow. Report both “historical path” and “stress-fed” columns; green Overview behavior requires stress-fed rules not all silent-pass without evaluation.

### D7: CPI honesty for historical real metrics

**Decision:** v1 keep constant `inflation_annual` but MUST record the rate in lock/metrics artifacts and Overview. Optionally accept a CPI series later; this change requires assumption visibility + LT CPI separation note. No silent “real return” without stated CPI.

### D8: OTC settlement lag (T+1-style)

**Decision:** Buys settle shares next trading day (or cash reserved / shares unavailable same day). Sells: proceeds available next trading day for redeployment. Apply to all OTC simulation symbols. Document as approximation of 场外 T+1.

**Alternatives:** Cash-fund only — rejected; all OTC legs share settlement friction.

### D9: Short-hold redemption fees

**Decision:** Replace v1 universal 0% redemption with a simple holding-period schedule: if lot age < 7 days (configurable), apply instrument `redemption_rate` (default small non-zero for equity/bond/gold feeders per catalog; money-market 0). Requires FIFO lot tracking on sells. Update fee assumptions section in lock doc.

### D10: Stocks sub-split ranking preference

**Decision:** After history restore, lock ranking adds a **risk-budget preference**: prefer `60-40` over `40-60` when annualized return delta < 50bp OR when CB material reviews worsen under higher QDII share. Record preference in lock selection ranking keys. Do not delete `40-60` from sweep.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Restored 2013 history worsens MDD / fails old locks | Expected; re-sweep and re-lock; document delta |
| `lockable` breaks UI that auto-locks on `passed` | Update workbench lock path + tests |
| T+1 + fees change all metrics | Ship behind same release; regenerate lock; compare baseline CSV |
| Behavior dual-path confuses readers | Separate columns; Overview uses stress-fed for green |
| Human sign-off abused as rubber stamp | Require listed open items + rationale fields; no empty sign-off |
| FIFO lots slow simulation | Keep lot list per symbol; profile if needed |

## Migration Plan

1. Fix alignment regression + assert tests (`effective_start` ≤ 2013-08-01)
2. Wire real QDII metrics into suitability; add material review rules
3. Implement `lockable` + sign-off artifact; update reporting Overview/Map
4. LT `seq_inflation` veto
5. Behavior dual-path + unrecovered DD material review
6. T+1 settlement + short-hold redemption
7. Sub-split ranking preference
8. Full sweep + regenerate strategy-lock; invalidate prior lock without re-signoff

Rollback: revert to soft-pass lock + 0% redemption + same-day NAV (accept known honesty holes).

## Open Questions

- Exact pending-days threshold N (default 252)? Confirm at apply time via existing lock stats (1128 days → clearly material).
- Sign-off storage: markdown section only vs machine-readable artifact field (prefer both).
- Whether S18 front-loaded crash should also feed behavior rules (recommend yes if cheap).
