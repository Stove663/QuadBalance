## MODIFIED Requirements

### Requirement: Project scope alignment

The strategy SHALL align with the project goal of supporting a personal long-term investment workflow: a core engine for expected return, backtest, and stress testing (Phase 1); a local personal browser workbench that includes validation UI, immutable strategy-lock registry, minimal personal ledger, and threshold-gated rebalance guidance (Phase 2); and optional later deepening of ledger/execution tooling without requiring brokerage automation.

The first-phase implementation remains the data-driven backtesting, deterministic stress testing, and suitability assessment engine. Phase 2 MAY proceed once those engine capabilities and run artifacts exist.

The codebase SHALL remain modular across data loading, configuration, simulation, metrics, suitability evaluation, reporting, scenario definitions, lock registry, ledger, and guidance so the workbench can consume the engine without rewriting it.

Report outputs SHALL keep CSV plus markdown as human-facing engine reports, with JSON run artifacts as the primary machine interface for the workbench.

The MVP engine assumptions remain: daily backtest frequency, fixed-amount DCA, threshold-based rebalancing that uses new cash first, rule-driven suitability classification, and a backtest window of 15+ years when available.

#### Scenario: Scope includes personal workbench phase

- **WHEN** the project is planned or reviewed
- **THEN** the core engine remains the Phase 1 deliverable
- **AND** Phase 2 is defined as the personal browser workbench including minimal ledger and rebalance guidance
- **AND** the strategy work does not require live brokerage integration or automated trading

#### Scenario: Workbench consumes artifacts without engine rewrite

- **WHEN** Phase 2 workbench features are added
- **THEN** they consume stable run artifacts and engine entrypoints
- **AND** they do not require rewriting the core simulation engine
