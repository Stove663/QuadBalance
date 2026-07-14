## 1. Data model and result shape

- [ ] 1.1 Define the structured suitability explanation payload shape used by validation and reporting
- [ ] 1.2 Add a shared helper or adapter for constructing classification, reasons, drivers, warnings, and governance notes
- [ ] 1.3 Ensure the payload can be serialized consistently for artifacts and CLI output

## 2. Validation and classification integration

- [ ] 2.1 Update suitability classification flow to emit mandatory human-readable reasons
- [ ] 2.2 Populate explanation drivers from existing validation metrics without recomputing them
- [ ] 2.3 Separate governance notes from classification reasons in the validation output

## 3. Reporting and document output

- [ ] 3.1 Update report sections to render the structured suitability explanation payload
- [ ] 3.2 Include the classification reasons in strategy lock output for each investor profile
- [ ] 3.3 Ensure CLI summary output shows the top reasons for each profile classification

## 4. Verification and regression coverage

- [ ] 4.1 Add or update tests to verify reasons are always present for each profile classification
- [ ] 4.2 Add tests to ensure governance notes do not change the classification label
- [ ] 4.3 Add regression coverage for consistent profile-specific emphasis across outputs
