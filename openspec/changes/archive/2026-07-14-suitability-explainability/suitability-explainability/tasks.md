# Tasks: Optimize Sweep and Stress-Test Execution

- [ ] Refactor sweep execution into a fast phase and a full validation phase
- [ ] Extract reusable intermediate results from the main simulation pipeline
- [ ] Split stress testing into lightweight gate checks and full replay scenarios
- [ ] Add deterministic caching or result reuse for per-configuration computations
- [ ] Introduce parallel execution across independent sweep configurations
- [ ] Preserve deterministic lock-candidate selection under parallel execution
- [ ] Keep existing report and artifact outputs unchanged
- [ ] Validate performance improvement with a representative sweep run
