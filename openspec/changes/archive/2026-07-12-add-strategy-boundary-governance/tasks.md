# Tasks: Add Strategy Boundary Governance

## 1. Real-return and rolling-window metrics

- [x] Add CPI input support or documented CPI assumption plumbing for validation runs.
- [x] Compute CPI-adjusted annualized return.
- [x] Compute CPI-adjusted terminal wealth.
- [x] Compute worst rolling 1-year, 3-year, and 5-year nominal returns.
- [x] Compute worst rolling 1-year, 3-year, and 5-year real returns.
- [x] Compute longest underwater duration.
- [x] Compute rolling 3-year and 5-year underperformance counts versus cash-only benchmark.
- [x] Compute rolling 3-year and 5-year underperformance counts versus 60/40 benchmark.
- [x] Add new metrics to detailed validation output.
- [x] Add selected metrics to sweep_results.csv.

## 2. Extended macro stress scenarios

- [x] Add S8 stagflation stress.
- [x] Add S9 global liquidity shock stress.
- [x] Add S10 CNY appreciation stress.
- [x] Add S11 domestic inflation shock stress.
- [x] Add S12 multi-year quadrant stagnation stress.
- [x] Report nominal and real outcomes for inflation-aware scenarios.
- [x] Keep macro boundary stress output separate from execution-friction stress output.

## 3. Boundary classification

- [x] Define `normal`, `review-required`, and `thesis-broken` classifications.
- [x] Implement behavioral review triggers.
- [x] Implement thesis-broken triggers.
- [x] Classify macro stress outputs.
- [x] Classify real-return and purchasing-power failures.
- [x] Aggregate classifications by boundary category.
- [x] Emit strategy boundary report for the locked configuration.

## 4. Lifecycle cashflow tests

- [x] Add no-DCA locked-strategy simulation variant.
- [x] Add DCA interruption variants for 12, 24, and 36 months.
- [x] Add bear-market DCA interruption after drawdown exceeds 10%.
- [x] Add retirement withdrawal simulations at 3%, 4%, and 5% inflation-adjusted annual withdrawals.
- [x] Add bear-market retirement start scenario.
- [x] Add one-time 20% liquidity withdrawal during drawdown.
- [x] Report depletion, terminal wealth, real terminal wealth, max drawdown, and recovery time.

## 5. Strategy lock output

- [x] Add Strategy Boundary Summary section to strategy-lock.md.
- [x] Add Real-Return Metrics section to strategy-lock.md.
- [x] Add Behavioral Review Triggers section to strategy-lock.md.
- [x] Add Thesis-Broken Triggers section to strategy-lock.md.
- [x] Add Governance Policy section to strategy-lock.md.
- [x] State that review-required triggers do not automatically change target allocation.
- [x] State that allocation redesign requires new validation.

## 6. Tests and validation

- [x] Add unit tests for rolling-window return calculations.
- [x] Add unit tests for underwater duration.
- [x] Add unit tests for boundary classification thresholds.
- [x] Add tests for S8-S12 scenario definitions.
- [x] Add golden-output or snapshot test for strategy-lock governance sections.
- [x] Run full validation and confirm boundary report is generated for locked configuration.
