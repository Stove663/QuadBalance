## Why

A full 396-config sweep currently yields 0 passes even when candidates clear drawdown and return gates. Two Criterion 3 defects make passage impossible by construction: (1) CB3 always classifies `thesis-broken` because its scenario hard-codes `capital_mobility_constraint_months=24`, which the classifier treats as `>=18 → thesis-broken` regardless of portfolio outcome; (2) `evaluate_acceptance` treats every `review-required` stress/path/behavior/cross-border result as a hard failure, contradicting governance language that review-required means disclosed annual review—not automatic rejection.

## What Changes

- **BREAKING** (acceptance semantics): `review-required` classifications no longer fail `validation.passed`. Only `fail` / `thesis-broken` (and existing primary metrics criteria) block pass.
- Surface `review-required` findings as a first-class `needs_review` (or equivalent) list on the validation result and in sweep CSV / strategy-lock disclosure—not as `failure_reasons`.
- Fix CB3 (and related cross-border) classification so scenario-definition parameters that are always true for that scenario cannot alone force `thesis-broken`; classification MUST depend on portfolio outcomes (return, frozen weight, usable liquidity) relative to thresholds.
- Keep severe CB3 outcomes reportable; severe cases may still be `thesis-broken` when portfolio metrics breach thresholds, or `review-required` otherwise.
- Out of scope: MDD never-recovered rule, LT staging, shrinking the sweep space, rewriting stress scenario shock magnitudes.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `strategy-validation`: Separate hard-fail vs review-required acceptance treatment for stress/path/behavior/cross-border results; require outcome-based (non-tautological) CB3 classification.

## Impact

- Code: `src/quadbalance/validation.py` (`evaluate_acceptance`, `ValidationResult`), `src/quadbalance/cross_border_stress.py` (`_classify`), sweep CSV row builder, strategy-lock reporting sections/tests.
- Specs: `openspec/specs/strategy-validation/spec.md` acceptance and cross-border boundary language.
- Behavior: configs that only have review-required stress hits can pass and become lock-eligible; lock document must still list review items. Full sweep pass rate expected to rise above zero once this lands (MDD recovery may still fail many configs—separate follow-up).
