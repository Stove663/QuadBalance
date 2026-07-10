## ADDED Requirements

### Requirement: QDII execution quality in validation output

The validation suite SHALL include QDII execution metrics in backtest output for every configuration. The strategy lock document MUST summarize QDII fill rate and maximum pending cash for the locked configuration.

#### Scenario: Lock document includes QDII friction summary

- **WHEN** a configuration passes validation with QDII quota simulation enabled
- **THEN** strategy-lock.md includes a QDII Execution section with fill rate and max pending cash
- **AND** notes if average actual QDII weight deviates from target by more than 2 percentage points of total portfolio

### Requirement: Low QDII quota stress scenario

The validation suite MUST include stress scenario S7: prolonged QDII low quota. Parameters: primary QDII daily cap reduced to 10 CNY for the entire simulation period. The scenario SHALL report impact on total return and QDII fill rate vs baseline.

#### Scenario: S7 low quota stress applied

- **WHEN** stress scenario S7 is executed on the candidate configuration
- **THEN** every QDII purchase attempt uses a 10 CNY daily cap
- **AND** the report shows delta in annualized return and QDII fill rate vs baseline
