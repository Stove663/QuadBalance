## 1. Artifact Review

- [x] 1.1 Review proposal.md — confirm scope (strategy spec only, no backtest code in this change)
- [x] 1.2 Review design.md — confirm decisions (60/40 stocks split, ±5% rebalance threshold, 2013–2025 backtest period)
- [x] 1.3 Review specs/investment-strategy/spec.md — confirm mechanical rules match intent
- [x] 1.4 Review specs/asset-universe/spec.md — confirm primary ETF codes and sub-allocations
- [x] 1.5 Review specs/strategy-validation/spec.md — confirm acceptance criteria and stress scenarios

## 2. Validation & Finalization

- [x] 2.1 Run `openspec validate --change china-permanent-portfolio-strategy` and fix any errors
- [x] 2.2 Sync delta specs to main specs with `openspec sync` (after user approval)
- [x] 2.3 Archive change with `openspec archive` once artifacts are approved

## 3. Follow-up Change Preparation (next change: implement-portfolio-backtest)

> Completed in archived change `implement-portfolio-backtest` (2026-07-10).

- [x] 3.1 Create new change `implement-portfolio-backtest` referencing this strategy spec
- [x] 3.2 Scaffold Python project with uv (pyproject.toml, src layout)
- [x] 3.3 Implement ETF price data fetcher (akshare) for instruments 510300, 513500, 511010, 511260, 518880, 511880
- [x] 3.4 Implement portfolio simulator: base position, proportional DCA, annual rebalance
- [x] 3.5 Implement parameter sweep engine (allocation × bond × DCA × threshold variants)
- [x] 3.6 Implement core metrics calculator (return, volatility, max drawdown, Sharpe, positive years, rebalance premium)
- [x] 3.7 Implement benchmark comparison (CSI 300, 60/40, cash-only)
- [x] 3.8 Implement stress test suite (S1–S6 scenarios)
- [x] 3.9 Implement acceptance criteria evaluator and strategy lock document generator
- [x] 3.10 Run full validation sweep and produce strategy lock document for passing configuration
