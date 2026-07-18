## 1. Cross-border classification

- [x] 1.1 Update `_classify` in `cross_border_stress.py` so scenario-duration fields alone cannot force `thesis-broken`
- [x] 1.2 Keep duration-based reasons and `review-required` bands; reserve `thesis-broken` for outcome breaches (severe return / frozen weight)
- [x] 1.3 Add unit tests: CB3 with moderate QDII weight is not auto-`thesis-broken`; severe frozen weight still is

## 2. Acceptance review vs fail split

- [x] 2.1 Add `needs_review: list[str]` to `ValidationResult`
- [x] 2.2 In `evaluate_acceptance`, route `review-required` stress/path/behavior/cross-border/product-risk findings to `needs_review` only
- [x] 2.3 Keep `fail` / `thesis-broken` (and primary metrics / NAV recovery) as `failure_reasons` that set `passed=False`
- [x] 2.4 Reclassify the S13 prolonged-liquidity impairment note into `needs_review` when S13 is not a hard fail
- [x] 2.5 Add unit tests covering pass-with-review and fail-on-thesis-broken

## 3. Sweep / lock output

- [x] 3.1 Add `needs_review` column to sweep CSV row builder
- [x] 3.2 Ensure strategy-lock / reporting sections surface `needs_review` without treating it as failure
- [x] 3.3 Update any tests that assumed review-required implies `validation_passed=False`

## 4. Verify

- [x] 4.1 Run targeted unit tests for validation + cross-border
- [x] 4.2 Optionally re-run a small sweep subset and confirm pass count can be >0 when only review items remain (note: MDD never-recovered may still fail many configs)
