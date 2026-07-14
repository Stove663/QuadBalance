## Context

The current validation engine already models the Stocks quadrant as a domestic/QDII split, but the split is effectively treated as a single hard-coded baseline in the sweep path. That makes it difficult to compare whether alternative domestic/QDII mixes improve robustness, quota behavior, or lock selection stability. This change remains within the existing spec-driven workflow and should not introduce new external dependencies or alter the four-quadrant portfolio model.

## Goals / Non-Goals

**Goals:**
- Make the Stocks quadrant domestic/QDII split an explicit sweep dimension.
- Preserve the existing 60/40 mix as the default baseline.
- Ensure configuration identity, reporting, and lock selection can distinguish split variants.
- Keep the implementation minimal and aligned with existing asset-universe, strategy, and validation structures.

**Non-Goals:**
- No new portfolio quadrants or new asset classes.
- No changes to the broader validation acceptance rules beyond including the new sweep dimension.
- No GUI, ledger, or persistence layer work.
- No redesign of the quota model or other backtest mechanics unrelated to the split choice.

## Decisions

1. **Represent the split as a first-class configuration parameter.**
   The sweep should treat the Stocks domestic/QDII mix like other variant dimensions rather than deriving it implicitly from the asset universe. This keeps config identity stable and makes reporting simpler.
   - Alternative considered: derive the split from a lookup table only at simulation time. Rejected because it makes run identity and lock reporting harder to reason about.

2. **Keep the default split unchanged.**
   The 60/40 domestic/QDII split remains the baseline so existing behavior is preserved for current locked or candidate configurations.
   - Alternative considered: shift the default to a more balanced split. Rejected because it would introduce unnecessary churn in existing expectations and outputs.

3. **Expose the split in sweep and lock outputs.**
   Results and strategy-lock reporting should carry the chosen split so downstream consumers can compare configurations without reconstructing them from implicit rules.
   - Alternative considered: omit split details from reporting to keep files smaller. Rejected because that obscures which candidate was validated.

4. **Reuse existing validation flow rather than introducing a separate sweep path.**
   The change should integrate into the current parameter sweep and selection pipeline so that all existing metrics, constraints, and reports continue to apply consistently.
   - Alternative considered: create a dedicated sub-split validation pass. Rejected because it duplicates logic and would fragment acceptance criteria.

## Risks / Trade-offs

- [More sweep combinations] → The added split variants increase total configurations and runtime; mitigate by keeping the variant set small and using existing caching.
- [Reporting complexity] → More configuration fields can make CSV and markdown outputs wider; mitigate by documenting the new field clearly and keeping labels concise.
- [Implicit assumptions elsewhere] → Some helpers may still assume a single stock split; mitigate by threading the split through config and adding focused tests around identity and target weights.

## Migration Plan

1. Add the split variant to configuration and sweep generation while preserving the default baseline.
2. Update validation/reporting code to surface the split explicitly.
3. Extend tests to cover unique configuration IDs, target weights, and reporting rows.
4. Run the existing validation suite to confirm no regressions in unrelated behavior.

Rollback is straightforward: remove the extra split variants and revert the reporting/config changes while leaving the base 60/40 behavior intact.

## Open Questions

- Should the initial variant set remain fixed at the current three options, or should it be data-driven from config in the future?
- Do we want strategy-lock markdown to show the split only in the selected configuration section, or also in the sweep summary table?
