# nav-recovery-time-validation Specification

## Purpose
TBD - created by archiving change nav-recovery-time-hard-threshold. Update Purpose after archive.
## Requirements
### Requirement: hard recovery-time gate
The system SHALL reject a strategy when its NAV recovery time exceeds the configured maximum recovery duration.

#### Scenario: recovery time within the threshold passes
- **WHEN** a strategy's NAV recovery time is less than or equal to the configured maximum
- **THEN** the strategy SHALL pass the recovery-time validation gate

#### Scenario: recovery time above the threshold fails
- **WHEN** a strategy's NAV recovery time is greater than the configured maximum
- **THEN** the strategy SHALL fail validation

### Requirement: unrecovered paths fail validation
The system SHALL fail validation when the portfolio NAV does not recover to the prior peak before the end of the test window.

#### Scenario: unrecovered path is rejected
- **WHEN** the equity curve never regains the peak preceding the maximum drawdown within the test period
- **THEN** the strategy SHALL fail the hard recovery-time gate

