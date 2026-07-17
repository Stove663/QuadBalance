# nav-recovery-time-metric Specification

## Purpose
Define the NAV recovery-time metric used in strategy summaries and lock documents.
## Requirements
### Requirement: NAV recovery time metric
The system SHALL compute the number of trading days required for the portfolio NAV to recover to the peak that preceded the maximum drawdown.

If the portfolio does not recover within the test window, the metric SHALL be reported as unrecovered rather than assigned a synthetic duration.

#### Scenario: recovered path reports a finite recovery time
- **WHEN** a portfolio NAV reaches a new peak, falls into the maximum drawdown, and later returns to at least the pre-drawdown peak
- **THEN** the system SHALL report the trading-day recovery duration from that peak to the first recovery date

#### Scenario: unrecovered path is reported explicitly
- **WHEN** the portfolio NAV does not recover to the pre-drawdown peak by the end of the test window
- **THEN** the system SHALL report the path as unrecovered rather than inventing a recovery duration

### Requirement: NAV recovery time is reportable
The system SHALL expose the NAV recovery-time value in strategy summaries so it can be inspected alongside other risk metrics.

#### Scenario: report includes recovery time
- **WHEN** a strategy summary or lock document is generated
- **THEN** the summary SHALL include the NAV recovery-time metric or an unrecovered state indicator

