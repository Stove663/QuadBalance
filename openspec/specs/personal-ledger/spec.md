# personal-ledger

## Purpose

Define the minimal personal ledger for recording real trades and holdings, reconstructing positions, marking prices, and comparing drift against the active strategy lock.

## Requirements

### Requirement: Amount and share ledger entries

The personal ledger SHALL record dated entries with types that include at least: opening, buy, sell, DCA, rebalance, settlement-cash movement, and corporate_action. Fund entries MUST support cash amount and/or share quantity fields sufficient to reconstruct positions. The ledger MUST NOT automatically ingest simulated backtest events from run artifacts.

#### Scenario: Manual buy recorded

- **WHEN** the user records a buy with symbol, date, amount, and shares
- **THEN** the entry is stored in the ledger
- **AND** reconstructed holdings for that symbol increase by the recorded shares
- **AND** settlement cash decreases by the recorded amount when an amount is provided

#### Scenario: Backtest events not auto-imported

- **WHEN** a validation run writes `artifacts/events.json`
- **THEN** those events are not inserted into the personal ledger unless the user explicitly records separate real trades

### Requirement: Settlement cash versus cash sleeve

The ledger MUST distinguish **settlement cash** (uninvested cash available to spend) from **cash-sleeve holdings** (shares of the locked cash-quadrant / money-market instrument). Portfolio market value for weight calculations MUST equal the sum of marked fund holdings plus settlement cash. Cash-sleeve shares contribute to the cash quadrant weight; settlement cash also contributes to total value and is treated as unallocated cash for guidance spending, not as cash-sleeve target fulfillment unless the user holds the cash-sleeve instrument.

#### Scenario: Settlement cash does not count as cash-sleeve shares

- **WHEN** the user holds only settlement cash and no cash-sleeve fund shares
- **THEN** reconstructed cash-sleeve share balance is zero
- **AND** settlement cash balance is positive
- **AND** total portfolio value includes the settlement cash

### Requirement: Opening snapshot bootstrap

The ledger SHALL allow recording an opening snapshot (as of a date) that sets initial share balances per symbol and/or initial settlement cash so an existing real-world portfolio can be bootstrapped without fabricating a full trade history.

#### Scenario: Opening shares establish holdings

- **WHEN** the user records an opening snapshot with 500 shares of a symbol and settlement cash of 10,000
- **THEN** reconstructed holdings show 500 shares for that symbol
- **AND** reconstructed settlement cash is 10,000 before any later entries

### Requirement: Ledger entry corrections

The system SHALL allow the user to edit or delete existing ledger entries so mistaken trades and opening data can be corrected. After a correction, reconstructed holdings MUST reflect the updated entry set. Corporate-action entries created by the system MUST also be editable or deletable.

#### Scenario: Delete mistaken buy

- **WHEN** the user deletes a previously recorded buy of 100 shares
- **THEN** reconstructed holdings no longer include those 100 shares
- **AND** settlement cash is restored as implied by reversing that entry’s cash effect

#### Scenario: Edit share quantity

- **WHEN** the user changes a buy entry from 100 shares to 95 shares
- **THEN** reconstructed holdings use 95 shares for that entry

### Requirement: Trade entry guards

On ordinary buy, sell, DCA, and rebalance entry paths, the system MUST reject submissions that would make any symbol’s share balance negative or make settlement cash negative. Opening-snapshot and correction flows MAY adjust historical state outside these guards when clearly presented as corrections.

#### Scenario: Oversell rejected

- **WHEN** holdings include 100 shares of a symbol
- **AND** the user attempts to record a sell of 150 shares on the ordinary trade path
- **THEN** the system rejects the entry
- **AND** holdings remain 100 shares

#### Scenario: Buy without cash rejected

- **WHEN** settlement cash is 0
- **AND** the user attempts to record a buy that spends cash on the ordinary trade path
- **THEN** the system rejects the entry

### Requirement: Corporate actions from market data

The system SHALL use market data feeds (akshare fund split and dividend details, or equivalent) to detect splits and dividends for held symbols. On price refresh or an explicit sync action, the system MUST create reviewable `corporate_action` ledger entries rather than silently mutating balances without a ledger trail.

- **Splits / 折算**: the system SHALL propose or apply share adjustments using the published ratio for shares held as of the effective date.
- **Dividends**: the system SHALL apply using a user-configurable default policy of either cash (increase settlement cash by shares × per-unit dividend) or reinvest (increase shares using an estimated NAV). Because feeds do not expose the user’s broker payout election, the default policy is required and the user MUST be able to correct resulting entries.
- **Idempotency**: syncing the same corporate action twice MUST NOT create duplicate ledger effects for the same symbol, action kind, and effective date.

#### Scenario: Split adjusts shares via ledger entry

- **WHEN** a held fund publishes a 1:2 split effective on a date
- **AND** corporate actions are synced
- **THEN** a corporate_action entry adjusts share quantity by the published ratio
- **AND** the entry is visible and correctable in the ledger

#### Scenario: Dividend uses user default policy

- **WHEN** a held fund pays a cash dividend per share
- **AND** the user’s default policy is cash
- **AND** corporate actions are synced
- **THEN** settlement cash increases by shares × dividend amount via a corporate_action entry

#### Scenario: Re-sync does not duplicate

- **WHEN** a corporate action for a symbol and effective date was already applied
- **AND** the user syncs corporate actions again
- **THEN** no second economic effect is applied for that same action key

### Requirement: Position reconstruction

The system SHALL reconstruct current share balances per symbol and settlement cash by applying ledger entries in date order (and a stable secondary order when timestamps tie). Holdings display MUST use these reconstructed balances.

#### Scenario: Sell reduces shares and raises settlement cash

- **WHEN** holdings include 1000 shares of a symbol
- **AND** the user records a sell of 200 shares for a stated amount
- **THEN** reconstructed holdings show 800 shares for that symbol
- **AND** settlement cash increases by that amount

### Requirement: Automatic mark prices for holdings

Holdings market values MUST be computed as share balances times automatically obtained mark prices from the engine price path (cached market data). The user MUST NOT be required to type or periodically update NAVs by hand. The holdings view MUST show an as-of date (or equivalent timestamp) for the marks in use and MUST offer an action to refresh prices from the network/cache update path.

#### Scenario: Values update without manual NAV entry

- **WHEN** the user has recorded share holdings and opens the holdings view
- **THEN** market values are computed using automatically loaded mark prices
- **AND** the UI shows an as-of date for those marks
- **AND** the user is not asked to enter NAVs manually

#### Scenario: Manual price refresh

- **WHEN** the user triggers Refresh prices
- **THEN** the system attempts to update mark prices via the engine price-loading path
- **AND** subsequent holdings values use the refreshed marks when available

### Requirement: Drift versus active lock

When an active strategy lock exists, the ledger view SHALL show actual weights (using current available prices) versus the locked target instrument or quadrant weights and indicate absolute drift per quadrant. Actual weights MUST use total value including settlement cash.

#### Scenario: Drift shown against active lock

- **WHEN** an active lock defines target weights
- **AND** ledger holdings and prices are available
- **THEN** the UI shows actual versus target weights and per-quadrant absolute drift
