## ADDED Requirements

### Requirement: Proxy price perturbation

The data layer SHALL support applying annualized return drift to a specified date range of a price series without affecting dates outside that range. Perturbation MUST preserve the price level at the range boundary to maintain stitch continuity at handoff dates.

#### Scenario: Drift applied only to proxy segment

- **WHEN** a +2% annualized drift is applied to proxy segment ending 2016-12-02
- **THEN** only dates before 2016-12-02 are perturbed
- **AND** the price on 2016-12-02 matches the unperturbed handoff level

### Requirement: S4 bond return cap path modifier

The stress test module SHALL provide a function that clones the price matrix and caps bond instrument annual returns at a specified rate for a consecutive calendar-year window. The modifier MUST support B1, B2, and B3 bond variants by targeting the correct instrument columns.

#### Scenario: B1 bond cap applied for 5 years

- **WHEN** S4 is run for configuration with bond variant B1
- **AND** shock window is 2021–2025
- **THEN** instrument 003358 daily returns are scaled so each calendar year return ≤ 2%
- **AND** non-bond instruments retain original prices outside the scaling logic

### Requirement: Proxy sensitivity orchestration

The sweep orchestrator SHALL run proxy sensitivity analysis for the first configuration that passes acceptance criteria. Sensitivity runs MUST execute after the baseline sweep completes and reuse cached price data.

#### Scenario: Sensitivity runs for locked config only

- **WHEN** full validation completes and configuration `25-25-25-25_B1_prop_5pct` is locked
- **THEN** sensitivity analysis runs for that configuration only
- **AND** does not re-run the 48-configuration parameter sweep

### Requirement: CLI sensitivity flag

The CLI SHALL accept an optional `--full-sensitivity` flag that runs proxy sensitivity for all 48 configurations instead of only the locked configuration.

#### Scenario: Full sensitivity flag

- **WHEN** user runs `uv run quadbalance --full-sensitivity`
- **THEN** proxy_sensitivity.csv contains rows for all 48 configurations × all drift scenarios
