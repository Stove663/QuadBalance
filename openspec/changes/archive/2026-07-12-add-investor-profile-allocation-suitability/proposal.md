# Change: Add Investor Profile and Allocation Suitability

## Why

The current strategy validation framework can determine whether a candidate permanent-portfolio configuration passes historical backtest, stress, execution-friction, and governance checks. However, the strategy still lacks an explicit answer to a higher-level investment question: **suitable for whom, and for which life stage?**

A single 25/25/25/25 permanent portfolio may be appropriate for a conservative investor seeking stability, but it may be overly defensive for a long accumulation horizon and under-modeled for retirement withdrawal use. Without investor-profile suitability checks, the system may lock a mechanically valid strategy that is misaligned with the investor's time horizon, contribution stability, withdrawal needs, real-return objective, or behavioral tolerance.

This change adds profile-aware allocation suitability assessment. It expands the candidate allocation space beyond classic permanent-portfolio variants, evaluates configurations against investor lifecycle profiles, and requires strategy-lock output to state which profiles the locked strategy is suitable, cautionary, or unsuitable for.

## What Changes

- Define investor profiles used for strategy suitability assessment:
  - accumulation
  - balanced core
  - pre-retirement preservation
  - retirement withdrawal
- Add profile-specific objectives, constraints, and risk/behavior tolerance boundaries.
- Expand allocation sweep coverage to include higher-equity and lower-gold/lower-cash variants for accumulation-oriented investors.
- Require suitability scoring and classification per profile: `suitable`, `caution`, or `unsuitable`.
- Require validation output and strategy-lock documents to disclose suitability classification, reasons, and key tradeoffs.
- Strengthen lifecycle validation so suitability conclusions are based on actual cashflow simulation rather than post-processing a baseline value curve.

## Out of Scope

- No live brokerage integration.
- No discretionary market-timing rules.
- No automatic allocation redesign after suitability review.
- No personalized financial advice beyond mechanical profile classification.
- No implementation of tax optimization or account-location rules.

## Expected Impact

- The system will be able to distinguish between a strategy that is generally robust and a strategy that is appropriate for a specific investor lifecycle.
- The default permanent portfolio may remain a candidate, but it will be evaluated alongside growth-tilted and preservation-tilted alternatives.
- Strategy-lock documents will become more transparent about who should use the locked configuration and who should not.
