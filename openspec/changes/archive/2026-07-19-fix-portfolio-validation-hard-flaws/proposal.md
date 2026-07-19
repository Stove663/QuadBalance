## Why

Locked strategy `20-25-30-25_B1_uw_5pct_s40-60` looks green because validation soft-passes `review-required`, comfort metrics sit on a truncated 2018+ window, and QDII/suitability/retirement gates hide execution and purchasing-power failure. Investors can treat `locked` as verified safety when it is not.

## What Changes

- Restore long-history price-matrix alignment so QDII backups never truncate `effective_start` to 2018-06-08; re-lock only after history ≤2013-08-01 is restored
- **BREAKING:** Strategy lock eligibility requires either empty material `needs_review` or an explicit recorded human sign-off; open Criterion-3 reviews no longer imply “ready”
- **BREAKING:** Inflation-escalating withdrawal (`seq_inflation`) classified `thesis-broken` vetoes lock / upgrades long-term scenario classification
- Pass real QDII fill, weight-gap, and pending-day metrics into suitability (remove hardcoded perfect execution)
- Add QDII execution gates beyond fill rate (pending days / average weight gap / post-rebalance deviation)
- Unify Risk Overview vs Risk Map red/yellow semantics; stop greenwashing behavior stress that never triggers on shallow historical MDD
- Document formula-based vs path-simulated stresses; strengthen unrecovered end-sample drawdown handling
- Document or replace constant 3% CPI for historical real-return metrics
- **BREAKING (simulation fidelity):** Model OTC settlement lag (T+1-style) and non-zero short-hold redemption where applicable
- Re-evaluate stocks sub-split ranking under restored history and cross-border stress (risk budget vs return-max)

## Capabilities

### New Capabilities

- `strategy-lock-integrity`: Lock eligibility, human sign-off, overview/map consistency, and investor-facing honesty rules for locked artifacts

### Modified Capabilities

- `strategy-validation`: Harden gates for `needs_review`, QDII execution quality, unrecovered drawdown, behavior-stress triggering, stress mechanism labeling
- `portfolio-backtest`: Enforce backup-excluded alignment matrix; OTC settlement lag; short-hold redemption fees
- `suitability-explainability`: Require real execution-friction inputs (no perfect-fill defaults)
- `long-term-macro-regime-stress`: `seq_inflation` thesis-broken must fail lock / escalate scenario classification
- `asset-universe`: Non-zero redemption rates / holding-period fee schedule for simulation symbols
- `stocks-subsplit-sweep`: Ranking/risk-budget guidance when overseas tilt amplifies CB stress
- `run-artifacts`: Lock document fields for sign-off, CPI assumption, stress mechanism type, QDII quality gates

## Impact

- Code: `data.py` / price loading, `sweep.py`, `single_run.py`, `simulator.py`, `fees.py`, `instrument_pool.py`, `validation.py`, `metrics.py`, `behavior_stress.py`, `long_term_stress.py`, `reporting*.py`, `artifacts.py`, UI lock path
- Artifacts: regenerated `strategy-lock.md`, sweep CSV columns, suitability payloads
- Tests: criterion3 review-vs-fail, QDII matrix start date, suitability inputs, LT seq_inflation veto, T+1 / redemption, risk panel consistency
- **Breaking:** Existing “passed with reviews” locks and soft suitability results become invalid until re-run; historical metrics will change under longer history + fees + settlement
