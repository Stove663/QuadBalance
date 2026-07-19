## 1. Architecture boundary foundation

- [x] 1.1 Identify the canonical domain concepts shared by backtest, validation, reporting, and lock workflows
- [x] 1.2 Map current modules into domain, calculation, orchestration, and presentation responsibilities
- [x] 1.3 Define the canonical run and artifact metadata shape used across workflows

## 2. Shared contracts and orchestration

- [x] 2.1 Introduce or consolidate shared result objects for validation, stress outcomes, and reporting summaries
- [x] 2.2 Update orchestration paths so CLI, UI, and sweep flows emit the same canonical run metadata
- [x] 2.3 Ensure deterministic candidate evaluation and final lock selection remain stable for identical inputs

## 3. Reporting and artifact consistency

- [x] 3.1 Align reporting helpers with the shared validation result contract
- [x] 3.2 Standardize artifact output paths and references for validation and lock documents
- [x] 3.3 Add or update tests that verify artifact schema consistency and deterministic behavior

## 4. Verification and rollout

- [x] 4.1 Run targeted tests covering the affected orchestration and reporting paths
- [x] 4.2 Fix any boundary regressions revealed by the test run
- [x] 4.3 Confirm the change is ready for implementation follow-up and archive review
