# Design: Investor Profile and Allocation Suitability

## Context

The current system validates portfolio configurations using historical backtests, benchmark comparisons, stress scenarios, QDII execution metrics, real-return metrics, lifecycle stress tests, behavioral boundaries, and governance rules. This is necessary but not sufficient for investment-strategy selection because a valid allocation can still be unsuitable for a particular investor.

The key design shift is to separate:

```text
configuration robustness
    from
investor suitability
```

A configuration can pass primary validation and still be unsuitable for accumulation if expected real return is too low. Conversely, a higher-equity configuration may be suitable for accumulation but unsuitable for retirement withdrawal because its sequence-risk profile is unacceptable.

## Investor Profiles

### Accumulation

Represents an investor with a long horizon and stable contributions.

Primary concerns:

- Long-term real return.
- Purchasing-power growth.
- Ability to tolerate drawdown during DCA.
- Avoiding excessive long-term cash drag.

Indicative constraints:

- Horizon: 10+ years.
- Contributions: stable monthly DCA.
- Withdrawals: none expected.
- Higher tolerance for drawdown and underperformance versus cash.

### Balanced Core

Represents a general-purpose household core allocation.

Primary concerns:

- Moderate real return.
- Controlled drawdown.
- Ability to continue mechanical execution without frequent redesign.
- Reasonable diversification across macro regimes.

Indicative constraints:

- Horizon: 5-10+ years.
- Contributions: stable or moderate DCA.
- Withdrawals: occasional liquidity needs possible.
- Moderate behavioral tolerance.

### Pre-retirement Preservation

Represents an investor nearing withdrawal phase.

Primary concerns:

- Avoiding large drawdowns shortly before retirement.
- Maintaining purchasing power.
- Preserving liquidity.
- Reducing reliance on future contributions.

Indicative constraints:

- Horizon: 3-10 years.
- Contributions: may decline or stop.
- Withdrawals: not yet regular, but liquidity risk increases.
- Lower tolerance for long underwater periods.

### Retirement Withdrawal

Represents an investor drawing from the portfolio.

Primary concerns:

- Sequence-of-returns risk.
- Inflation-adjusted withdrawal sustainability.
- Avoiding depletion.
- Maintaining enough liquid and defensive assets.

Indicative constraints:

- Horizon: ongoing withdrawal phase.
- Contributions: none.
- Withdrawals: annual or monthly inflation-adjusted withdrawals.
- Low tolerance for severe drawdown and depletion.

## Allocation Suitability Evaluation

Suitability should be evaluated after primary validation metrics are available. The system should compute a profile suitability record for each candidate configuration.

Each record includes:

- profile id
- classification: `suitable`, `caution`, or `unsuitable`
- return objective result
- drawdown result
- real-return result
- lifecycle cashflow result
- behavioral tolerance result
- execution-friction result
- human-readable reasons

The scoring should be rule-based and auditable rather than optimized or machine-learned.

## Expanded Allocation Variants

Current sweep variants only test classic or near-classic permanent-portfolio allocations. Suitability assessment needs additional variants to test whether a less defensive allocation is materially better for accumulation.

Proposed additional candidate variants:

| Name | Stocks | Bonds | Gold | Cash | Intended Profile |
|------|--------|-------|------|------|------------------|
| 35-20-20-25 | 35% | 20% | 20% | 25% | Balanced / accumulation tilt |
| 40-20-20-20 | 40% | 20% | 20% | 20% | Accumulation / balanced |
| 45-20-20-15 | 45% | 20% | 20% | 15% | Accumulation |
| 50-20-15-15 | 50% | 20% | 15% | 15% | Growth accumulation |
| 30-25-20-25 | 30% | 25% | 20% | 25% | Conservative growth |
| 20-30-20-30 | 20% | 30% | 20% | 30% | Pre-retirement preservation |
| 15-35-15-35 | 15% | 35% | 15% | 35% | Retirement defense |

These are candidate variants only. A profile result must not silently choose a profile-specific allocation without generating a new strategy lock.

## Lifecycle Simulation Requirement

Suitability conclusions should not use value-curve post-processing to approximate cashflow scenarios. Instead, lifecycle scenarios should be simulated through the trading engine so that contributions, interruptions, withdrawals, QDII quota, pending cash, fees, and rebalancing interact on the same timeline.

Required lifecycle mechanics:

```text
Daily/monthly simulation timeline
├─ carry existing holdings forward
├─ apply contribution if active
├─ apply withdrawal if scheduled
├─ route buys through quota and fee logic
├─ sell assets when cash is insufficient for withdrawal
├─ apply rebalance rules if triggered
└─ record portfolio value, drawdown, depletion, recovery, and real value
```

## Suitability Classification Guidelines

### Accumulation

A configuration is `suitable` when it:

- passes primary validation;
- produces positive real annualized return;
- avoids severe long-run purchasing-power failure;
- does not breach thesis-broken behavioral boundaries;
- shows materially better expected real return than cash.

It is `caution` when it passes validation but has signs of excessive defensiveness, such as low real return or long underperformance versus higher-growth benchmarks.

It is `unsuitable` when it fails primary validation, fails to preserve purchasing power over long rolling windows, or breaches thesis-broken behavioral limits.

### Balanced Core

A configuration is `suitable` when it balances return and drawdown, avoids major real-return failure, and does not depend on fragile execution assumptions.

It is `caution` when either return or behavioral metrics are marginal but not thesis-broken.

### Pre-retirement Preservation

A configuration is `suitable` when drawdown, underwater duration, and liquidity stress remain within tighter boundaries, and DCA interruption or no-DCA scenarios do not materially impair recovery.

It is `unsuitable` when a near-retirement liquidity shock or no-DCA scenario creates unacceptable drawdown or prolonged recovery.

### Retirement Withdrawal

A configuration is `suitable` when withdrawal simulations at 3% and 4% inflation-adjusted rates do not deplete and do not breach thesis-broken drawdown or real terminal wealth boundaries.

It is `caution` when 5% withdrawals fail but 3%-4% pass.

It is `unsuitable` when 4% withdrawal depletes or bear-market retirement start fails.

## Strategy Lock Output

The strategy lock document should include a section similar to:

```text
## Investor Profile Suitability

| Profile | Classification | Key Reasons |
|---------|----------------|-------------|
| Accumulation | caution | Real return acceptable but equity exposure may be low |
| Balanced Core | suitable | Drawdown and real-return objectives pass |
| Pre-retirement | suitable | No-DCA and liquidity scenarios pass |
| Retirement Withdrawal | caution | 5% withdrawal depletes; 4% remains viable |
```

The document should explicitly state that profile classification is a mechanical suitability screen, not personalized financial advice.

## Open Questions

- Should profile thresholds be fixed defaults or configurable per user?
- Should accumulation suitability compare against a higher-equity benchmark in addition to 60/40?
- Should QDII unavailability cause accumulation-specific caution earlier than balanced-core caution?
- Should stock sub-allocation variants, such as A-share/QDII 50/50 or 40/60, be part of this change or a follow-up change?
