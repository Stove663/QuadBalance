## MODIFIED Requirements

### Requirement: Stress test scenarios

The validation suite MUST include six stress scenarios applied to the locked candidate configuration:

| ID | Scenario | Parameters |
|----|----------|------------|
| S1 | A-share crash | Stocks -40% in one year, other quadrants at historical median |
| S2 | Stock-bond dual kill | Stocks -20%, Bonds 0%, Gold +10%, Cash +2% |
| S3 | CNY depreciation | CNY -10% vs USD; Gold +8%, QDII Stocks +12% (USD terms), domestic assets flat in CNY |
| S4 | Prolonged low rates | Bonds annual return capped at 2% for 5 consecutive calendar years (path simulation) |
| S5 | QDII premium | 513500 purchases at 5% premium to NAV on every buy |
| S6 | Gold crash | Gold -20% in one year, other quadrants at historical median |
| S7 | Prolonged low QDII quota | QDII daily cap reduced to 10 CNY for entire simulation |

#### Scenario: Stress scenario S1 applied

- **WHEN** stress scenario S1 is executed on the candidate configuration
- **THEN** portfolio return for the stress year is computed
- **AND** compared to the -40% Stocks input shock

#### Scenario: Stress scenario S4 five-year path

- **WHEN** stress scenario S4 is applied
- **THEN** the engine re-runs full portfolio simulation on a modified price path
- **AND** bond instrument annual returns are capped at 2% for 5 consecutive calendar years
- **AND** the report shows 5-year cumulative portfolio return, worst single year in the window, and annualized return over the window

#### Scenario: Stress scenario S4 pass criterion

- **WHEN** S4 five-year path simulation completes with cumulative portfolio return of -8%
- **AND** the conservative floor is -10% (25% bonds weight × 2% × 5 years)
- **THEN** S4 is marked as passed

#### Scenario: Stress scenario S5 QDII premium

- **WHEN** stress scenario S5 is applied
- **THEN** every 513500 purchase in simulation pays 5% above NAV
- **AND** the report shows impact on total return vs baseline

#### Scenario: Stress scenario S7 low QDII quota

- **WHEN** stress scenario S7 is applied
- **THEN** every QDII purchase attempt uses a 10 CNY daily cap
- **AND** the report shows delta in total return and QDII fill rate vs baseline

## ADDED Requirements

### Requirement: S4 path details in strategy lock document

The strategy lock document MUST include an S4 Five-Year Path section reporting: shock window years, 5-year cumulative portfolio return, worst single year in window, annualized return over window, and pass/fail status.

#### Scenario: Lock document S4 path section

- **WHEN** a locked configuration completes validation with S4 path simulation
- **THEN** strategy-lock.md includes the S4 Five-Year Path section with all four metrics
- **AND** lists the 5 calendar years used as the shock window
