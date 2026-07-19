# rebalance-guidance

## Purpose

Define threshold-gated rebalance alerts and advisory sell/buy guidance based on ledger holdings, automatic mark prices, and the active strategy lock.

## Requirements

### Requirement: Threshold-gated rebalance alert

Rebalance guidance SHALL compare actual quadrant weights (from ledger holdings and settlement cash marked at current prices) to the active lock’s target quadrant weights using the locked `rebalance_threshold`. By default the system MUST suppress actionable rebalance alerts when every quadrant’s absolute drift is within the threshold. The system MUST raise a rebalance alert when any quadrant’s absolute drift exceeds the threshold. Live guidance is on-demand and MUST NOT require waiting for an annual calendar check used in backtests.

In addition, when settlement cash is **material** and the locked cash-sleeve instrument is under its target weight, the system MUST surface guidance to deploy idle settlement cash into the cash-sleeve even if all quadrant drifts are otherwise within threshold (闲钱归位). Settlement cash is material when it is greater than **max(1% of total portfolio value, 1000 CNY)** using current marks.

#### Scenario: Within threshold stays quiet

- **WHEN** an active lock has rebalance threshold ±5%
- **AND** every quadrant’s absolute weight drift is ≤ 5%
- **AND** settlement cash is not material under the max(1%, 1000 CNY) rule
- **THEN** the default guidance state does not present an actionable rebalance alert

#### Scenario: Beyond threshold alerts

- **WHEN** an active lock has rebalance threshold ±5%
- **AND** Stocks actual weight is 12 percentage points above target
- **THEN** the system presents an actionable rebalance alert

#### Scenario: Idle settlement cash deploys to cash sleeve

- **WHEN** every quadrant’s absolute drift is within the rebalance threshold
- **AND** settlement cash is material under the max(1%, 1000 CNY) rule
- **AND** the cash-sleeve instrument is under its locked target weight
- **THEN** the system presents guidance that includes buying the cash-sleeve instrument with settlement cash

#### Scenario: Immaterial idle cash does not alert alone

- **WHEN** every quadrant’s absolute drift is within the rebalance threshold
- **AND** settlement cash is below the material threshold
- **THEN** the system does not present an actionable alert solely for idle cash

### Requirement: Concrete sell and buy guidance with split rules

When an actionable rebalance alert is active, the system SHALL produce a suggested order list that states which symbols to sell and buy, the cash amount for each leg, and an approximate share quantity using current prices. Guidance MUST:

1. Use instrument targets from the **active lock snapshot** (`total_value × instrument_weight`).
2. Prefer spending **settlement cash** before proposing sells.
3. When the cash-sleeve instrument is underweight, prioritize deploying settlement cash into that instrument (闲钱归位) before or as part of other underweight buys.
4. Allocate remaining buys to underweight instruments pro-rata by buy need.
5. Allocate sells across overweight instruments pro-rata by overweight value, ordering non-QDII sells before QDII sells when both appear.
6. Treat amounts as approximate (fees and minimum purchase sizes ignored in v1).
7. Remain advisory only and MUST NOT execute trades or write ledger entries automatically.

#### Scenario: Overweight sell and underweight buy listed

- **WHEN** rebalance is alerted because Stocks are overweight and Bonds are underweight beyond threshold
- **THEN** the guidance lists sell instructions for overweight stock instruments with amounts and approximate shares
- **AND** lists buy instructions for underweight bond instruments with amounts and approximate shares

#### Scenario: Settlement cash applied before sells

- **WHEN** rebalance is alerted and settlement cash is available
- **AND** one or more instruments are underweight
- **THEN** guidance applies settlement cash to underweight buys before proposing sells to fund those buys

#### Scenario: Cash sleeve prioritized for idle settlement cash

- **WHEN** settlement cash is available
- **AND** the cash-sleeve instrument is underweight
- **THEN** guidance includes a buy of the cash-sleeve funded from settlement cash

#### Scenario: Guidance does not mutate ledger

- **WHEN** the user views rebalance guidance
- **THEN** no ledger entries are created until the user explicitly records trades

### Requirement: Guidance uses automatic marks

Rebalance guidance MUST use the same automatically obtained mark prices as the holdings view (engine price path with cache). The guidance panel MUST show the marks’ as-of date and MUST allow the same refresh-prices action. The user MUST NOT enter NAVs to obtain guidance.

#### Scenario: Guidance without typing NAVs

- **WHEN** an actionable rebalance alert is evaluated
- **THEN** buy/sell approximate shares are derived from automatic mark prices
- **AND** the UI shows an as-of date for those marks

### Requirement: Missing price blocks complete guidance

If any symbol required to mark holdings or compute guidance lacks a usable price, the system MUST NOT invent prices. It MUST indicate that guidance is incomplete and identify the missing symbols.

#### Scenario: Missing price reported

- **WHEN** a held symbol has no available mark price
- **THEN** guidance reports that it cannot complete
- **AND** names the symbol with the missing price

### Requirement: Active lock required

Rebalance guidance SHALL require an active strategy lock. Without an active lock, the system MUST not emit sell/buy rebalance instructions.

#### Scenario: No lock no guidance

- **WHEN** there is no active strategy lock
- **THEN** the system does not produce threshold-based sell/buy rebalance guidance

### Requirement: QDII cap warnings only

When suggested buys involve QDII symbols, the system MAY attach warnings about daily quota or access constraints. Such warnings MUST NOT by themselves block producing the advisory list in v1.

#### Scenario: QDII buy still listed with warning

- **WHEN** guidance includes a QDII buy leg
- **THEN** the advisory list still includes that buy
- **AND** a quota/access warning may be shown alongside it
