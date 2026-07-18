## Context

Sweep acceptance currently conflates three different signals into `failure_reasons`:

1. Primary metrics gates (MDD, worst year, return vs benchmarks).
2. Stress / path / behavior / cross-border classifications of `fail` or `thesis-broken`.
3. Stress / path / behavior / cross-border classifications of `review-required`.

Governance text already says review-required means documented annual review, not automatic allocation rejection. Implementation ignores that: every review hit fails `validation.passed`. Separately, CB3 classification uses scenario-definition fields (`capital_mobility_constraint_months=24`) that always trip `>=18 → thesis-broken`, so CB3 can never pass for any portfolio.

Observed 396/396 sweep: every config fails CB3 + several universal review items; many also fail MDD-never-recovered (out of scope here).

## Goals / Non-Goals

**Goals:**

- Make `validation.passed` depend only on hard criteria: primary metrics + `fail` / `thesis-broken` stress-family results.
- Keep `review-required` visible via a dedicated `needs_review` list (CSV + lock disclosure).
- Make CB3 (and CB classification generally) outcome-based: portfolio return, frozen usable weight, and similar measured fields—not always-true scenario parameters.

**Non-Goals:**

- Changing MDD never-recovered / recovery-day thresholds.
- Deferring long-term stress (separate change: `stage-sweep-defer-long-term`).
- Softening CB3 shock magnitudes or removing CB scenarios.
- Changing S1–S7 pass math beyond the review-vs-fail split.

## Decisions

### 1. Acceptance: review-required does not fail pass

**Choice:** In `evaluate_acceptance`, append review-required findings to `ValidationResult.needs_review` (new field). Only `fail` / `thesis-broken` (and primary criteria 1–5 / NAV recovery) go to `failure_reasons` and set `passed=False`.

**Alternatives:**

- Keep review as fail but exclude CB1/CB2/S20 only — rejected; governance already defines the three-tier model globally.
- Introduce a third verdict (`passed_with_review`) — deferred; `passed=True` + non-empty `needs_review` is enough for sweep/lock.

### 2. Product-risk review: same split

**Choice:** `product_risk.worst_classification == "review-required"` or `weighted_score >= 40` move to `needs_review`, not hard fail. Only `thesis-broken` product risk hard-fails.

### 3. CB classification: outcome metrics only for thesis-broken

**Choice:** Rewrite `_classify` so `thesis-broken` requires at least one portfolio outcome breach, e.g.:

- `portfolio_return < -0.30`, or
- `frozen_asset_weight >= 0.30`, or
- liquid / usable return below a severe floor (if already computed).

Scenario-duration fields (`liquidity_impairment_months`, `capital_mobility_constraint_months`) may still annotate reasons and may contribute to `review-required`, but MUST NOT alone force `thesis-broken`.

**Implication for CB3:** With typical QDII sleeve weights, CB3 becomes `review-required` (long impairment + moderate return hit) unless frozen weight or return breaches severe thresholds. Severe external freeze with large QDII weight can still be `thesis-broken`.

**Alternatives:**

- Special-case CB3 to always `review-required` — rejected; hides real severe outcomes.
- Remove duration from classifier entirely — weaker; duration still useful for review tier.

### 4. Sweep CSV / lock document

**Choice:** Add `needs_review` column (semicolon-joined). Lock document already summarizes review vs thesis-broken; ensure it reads `needs_review` / classifications rather than treating review as failure.

### 5. Persistent correlation / S13 liquidity note

**Choice:** The S13-specific append `"persistent correlation/liquidity stress indicates prolonged liquidity impairment"` currently always lands in `failure_reasons`. Reclassify: if the underlying S13 result is only `review-required`, put this note in `needs_review`; if S13 is `fail`/`thesis-broken`, keep as failure (or omit duplicate and rely on the S13 fail line).

## Risks / Trade-offs

- [Many configs suddenly “pass”] → Mitigation: lock must list `needs_review`; governance cooldown unchanged; operators still see CB1–CB3 / S20.
- [CB3 no longer ever thesis-broken for low-QDII portfolios] → Intended; thesis-broken reserved for severe portfolio impact. Document in lock when CB3 is review-only.
- [Tests asserting review → fail] → Update unit/integration tests around `evaluate_acceptance` and cross-border classify.
- [MDD never-recovered still zeros many configs] → Expected; call out as follow-up, do not silently soften here.

## Migration Plan

1. Land code + tests.
2. Re-run a small subset then full sweep; compare pass count and top `needs_review` reasons.
3. No data migration; CSV schema gains a column (backward-compatible for readers that ignore unknown columns).

## Open Questions

- None blocking implementation. Exact CB review thresholds can keep current bands (`return < -0.15`, `frozen >= 0.10`, `liquidity_impairment_months >= 6`) after removing duration-only thesis-broken path.
