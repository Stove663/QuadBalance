## 1. Project Setup

- [x] 1.1 Initialize uv project with pyproject.toml and src layout
- [x] 1.2 Add dependencies: akshare, pandas, numpy

## 2. Data Layer

- [x] 2.1 Implement ETF price fetcher with akshare and parquet cache
- [x] 2.2 Implement price matrix alignment across instruments

## 3. Simulation Core

- [x] 3.1 Implement config types (allocation, bond, DCA, threshold variants)
- [x] 3.2 Implement portfolio simulator (base, DCA, rebalance)
- [x] 3.3 Implement core metrics calculator

## 4. Validation Suite

- [x] 4.1 Implement benchmark comparison (CSI300, 60/40, cash)
- [x] 4.2 Implement stress test scenarios S1-S6
- [x] 4.3 Implement acceptance criteria evaluator
- [x] 4.4 Implement strategy lock document generator

## 5. Integration

- [x] 5.1 Implement parameter sweep orchestrator
- [x] 5.2 Implement CLI entry point
- [x] 5.3 Run full validation sweep and verify output
