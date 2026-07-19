## MODIFIED Requirements

### Requirement: Machine-readable trade fees

Each instrument in the asset universe that participates in backtest simulation MUST declare machine-readable trade fee rates via a `TradeFees` structure containing at minimum: `purchase_rate` (decimal, e.g. 0.0012 for 0.12%) and `redemption_rate` (decimal). Human-readable `purchase_fee` display strings MUST remain for strategy-lock documentation. Equity, bond, and gold feeder instruments used in simulation MUST declare a non-zero short-hold `redemption_rate` consistent with common 场外 short-term redemption penalties unless the product truly has none; money-market cash MAY use 0.0.

#### Scenario: Primary instruments have numeric fee rates

- **WHEN** instrument 110020 is loaded from the instrument pool
- **THEN** its `purchase_rate` is 0.0012
- **AND** its `redemption_rate` is greater than 0.0 for short-hold application

#### Scenario: Cash may remain zero redemption

- **WHEN** instrument 006874 is loaded from the instrument pool
- **THEN** its `purchase_rate` is 0.0
- **AND** its `redemption_rate` MAY be 0.0

#### Scenario: QDII backup instruments have distinct fee rates

- **WHEN** backup 050025 is defined in the stocks QDII pool
- **THEN** its `purchase_rate` is 0.0010
- **WHEN** backup 006075 is defined in the stocks QDII pool
- **THEN** its `purchase_rate` is 0.0
