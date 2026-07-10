## ADDED Requirements

### Requirement: QDII era reporting in strategy lock

The strategy lock document MUST report QDII simulation era boundaries: proxy era end date (161125 handoff), and the date each backup fund becomes eligible for routing. When the restored backtest start precedes 161125 handoff, the document MUST note that QDII quota enforcement does not apply during the proxy era.

#### Scenario: Era boundaries in lock document

- **WHEN** a configuration passes validation after price-matrix alignment fix
- **THEN** strategy-lock.md includes QDII era dates (proxy end, backup eligibility)
- **AND** states whether quota applied from simulation start or from handoff date

### Requirement: Pre-fix regression check

After implementing price-matrix alignment fix, a full validation sweep MUST be re-run. The sweep output MUST record `effective_start` per configuration. At least one configuration MUST have `effective_start` on or before 2013-08-01 (restored long-history coverage).

#### Scenario: Start date restored

- **WHEN** full sweep completes after qdii-backup-price-matrix implementation
- **THEN** locked configuration effective_start is not 2018-06-08
- **AND** effective_start is on or before 2013-08-01

## MODIFIED Requirements

### Requirement: Backtest primary period

The backtest engine SHALL simulate the candidate strategy over the primary period from 2013-01-01 to the latest available data date. For instruments with listing dates after 2013-01-01, simulation for that instrument MUST begin on its first available trading date, and the effective backtest start date MUST be reported. QDII backup funds MUST NOT constrain the global price-matrix alignment start; only primary alignment symbols and their proxies determine the portfolio effective start.

#### Scenario: Full period simulation

- **WHEN** all primary alignment instruments have data from 2013-01-01
- **THEN** the backtest runs from 2013-01-01 to the latest data date
- **AND** reports total years covered

#### Scenario: Late-listed QDII backup does not truncate matrix

- **WHEN** QDII backup 006075 lists on 2018-06-08
- **AND** primary alignment symbols have data from 2013-07-29
- **THEN** portfolio effective_start is 2013-07-29 (or earliest common alignment date)
- **AND** is not truncated to 2018-06-08 by backup inclusion

#### Scenario: Late-listed QDII primary with proxy

- **WHEN** 161125 primary data begins on 2016-12-02 with 050025 proxy stitched before that date
- **THEN** the Stocks QDII sub-position simulation begins on proxy start date
- **AND** the report notes effective start and handoff date per instrument
