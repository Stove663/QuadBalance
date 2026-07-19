## 1. Price-matrix alignment regression (P0)

- [x] 1.1 Change `collect_required_symbols` (and single_run equivalent) to return primary/alignment symbols only; never union QDII backups into alignment
- [x] 1.2 Assert alignment matrix columns ∩ `QDII_BACKUP_SYMBOLS` is empty in `load_price_matrix_with_meta` / `load_market_data`
- [x] 1.3 Add regression test: sweep/single_run path yields `effective_start` ≤ 2013-08-01 and not `2018-06-08`
- [x] 1.4 Confirm backups still load via `backup_prices` and routing works post-handoff

## 2. Real QDII metrics and quality gates (P0)

- [x] 2.1 Remove hardcoded `qdii_fill_rate=1.0` / `avg_qdii_weight_gap=0.0` in `validation.py`; pass measured sim metrics (and sequence_risk when available)
- [x] 2.2 Add material `needs_review` rules for pending-cash days > 252, sustained weight gap > 2pp for 12 months, and max post-rebalance deviation > threshold
- [x] 2.3 Update suitability tests to prove measured friction affects classification
- [x] 2.4 Expose pending-days / weight-gap gate outcomes in sweep CSV

## 3. Lockable vs passed + sign-off (P0)

- [x] 3.1 Add `lockable` computation from material `needs_review` catalog (CB*, P*, S14/S15/S20, product review, unrecovered DD, seq_inflation veto)
- [x] 3.2 Implement human sign-off payload (reviewer, timestamp, rationale, acknowledged items) and wire into artifacts + strategy-lock.md
- [x] 3.3 Block active lock write / UI lock promotion unless `lockable`
- [x] 3.4 Update `test_criterion3_review_vs_fail` (and related): passed-with-review remains allowed; lockable false without sign-off
- [x] 3.5 Add `lockable` column to sweep CSV and lock selection preference for lockable candidates

## 4. Long-term seq_inflation veto (P0)

- [x] 4.1 Escalate LT scenario to at least `review-required` when `seq_inflation` is `thesis-broken`
- [x] 4.2 Emit material lock veto / `needs_review` entry; do not let fixed 4% pass clear it
- [x] 4.3 Add unit tests covering LT1/LT2/LT3 inflation-sequence veto behavior

## 5. Stocks sub-split risk-budget ranking (P0)

- [x] 5.1 Add lock ranking key: prefer `60-40` over `40-60` when return edge < 50bp or extra material CB reviews on overseas-heavier split
- [x] 5.2 Document ranking keys in strategy-lock selection section
- [x] 5.3 Test ranking preference with synthetic candidate pairs

## 6. Risk Overview / Map honesty + CPI + stress labels (P1)

- [x] 6.1 Unify Risk Overview red/yellow with Risk Map severity; forbid “未见明确红色风险” when any map layer is red
- [x] 6.2 Disclose constant CPI assumption in lock Core Metrics / Assumptions
- [x] 6.3 Label formula vs path-simulated stresses in lock stress tables
- [x] 6.4 Treat unrecovered end-sample max drawdown as material `needs_review` always

## 7. Behavior stress dual evaluation (P1)

- [x] 7.1 Evaluate behavior rules against historical path and stress-fed proxies (P1 MDD, S14 return surrogate; optionally S18)
- [x] 7.2 Report historical vs stress-fed columns in strategy-lock behavior section
- [x] 7.3 Stop Overview behavior-green when only historical shallow MDD left rules untriggered and stress-fed was skipped
- [x] 7.4 Add tests for stress-fed trigger with shallow historical MDD

## 8. OTC T+1 settlement (P2)

- [x] 8.1 Track unsettled buy lots and unsettled sale proceeds in simulator
- [x] 8.2 Enforce: new buys not sellable same day; sale cash not redeployable same day
- [x] 8.3 Add focused settlement tests (buy-then-same-day-sell blocked; proceeds next day)

## 9. Short-hold redemption fees (P2)

- [x] 9.1 Set non-zero short-hold `redemption_rate` on equity/bond/gold feeders in instrument pool; cash MAY stay 0
- [x] 9.2 Implement FIFO lot tracking and apply short-hold fee when lot age < default 7 days
- [x] 9.3 Update fee assumptions markdown (no universal 0% redemption claim)
- [x] 9.4 Update fee tests for recent-lot vs seasoned-lot sells

## 10. Re-lock and regression sweep

- [x] 10.1 Run full validation sweep after sections 1–9; capture `effective_start`, MDD, QDII metrics, lockable flags
  - Sweep 2026-07-19: 198 configs → 93 soft-pass, **0 lockable** (`output/sweep_results.csv`)
  - `effective_start=2013-07-29` (not 2018-06-08); end `2026-07-17`
  - Passed MDD median ≈ −8.4% (range −9.7% … −5.1%)
  - Passed QDII: fill_rate=1.0; pending_cash_days median 351 (max 702); `|avg_qdii_weight_gap|` median ≈ 0.8pp
  - Gates: `qdii_pending_days_gate` fail 171/198; `qdii_weight_gap_gate` fail 20/198
  - LT lock attempts (top 3): all soft-pass with material reviews (unrecovered MDD, CB/P/S14–20, QDII pending, max deviation)
- [x] 10.2 Regenerate strategy-lock.md only for a `lockable` config (or with explicit sign-off)
  - No `lockable` config after LT; human sign-off deferred → **no new active lock written** (gate held)
  - Prior `output/strategy-lock.md` remains **superseded** (task 10.3); re-lock later via `--sign-off-reviewer`/`--sign-off-rationale` or a clean lockable candidate
- [x] 10.3 Invalidate / annotate prior 2018-start lock as superseded
- [x] 10.4 Update module-boundary / reporting tests broken by new fields
