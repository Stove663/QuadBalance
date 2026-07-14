## Why

The current engine still treats the Stocks quadrant sub-split as a fixed assumption, which limits sweep coverage and makes it harder to validate whether a different domestic/QDII mix changes robustness under quota constraints. We also need the change to be explicit in OpenSpec so the later design, tasks, and implementation stay aligned.

## What Changes

- Add sweepable Stocks quadrant domestic/QDII sub-split variants so the engine can compare alternative mixes during validation.
- Keep the existing 60/40 split as the default baseline while allowing other documented variants in the same sweep.
- Record the selected stock sub-split in run output and strategy-lock reporting so configurations remain uniquely identifiable.
- Update validation coverage and reports to reflect the new sweep dimension without changing the overall four-quadrant strategy scope.

## Capabilities

### New Capabilities
- `stocks-subsplit-sweep`: Introduce sweep variants for the Stocks quadrant domestic/QDII sub-allocation and report them in validation output.

### Modified Capabilities
- `asset-universe`: Extend the Stocks quadrant mapping to support multiple documented domestic/QDII split variants in addition to the default 60/40 baseline.
- `investment-strategy`: Allow the strategy configuration to carry an explicit stock sub-split selection for validation and lock reporting.
- `portfolio-backtest`: Include the stock sub-split as part of configuration identity and sweep evaluation.
- `strategy-validation`: Compare candidate configurations across the additional stock sub-split dimension and surface it in lock selection/reporting.

## Impact

Affected code includes the asset-universe helpers, strategy configuration, sweep generation, validation reporting, and tests. The change adds one more sweep dimension but does not alter the core four-quadrant portfolio model or introduce new external dependencies.
