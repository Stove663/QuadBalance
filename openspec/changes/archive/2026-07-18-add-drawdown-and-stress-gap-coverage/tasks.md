# Tasks

- [ ] Add a fast screening stage to the sweep pipeline using core metrics and early-fail thresholds.
- [ ] Refactor candidate evaluation so expensive stress, path, and long-term checks are only run for screened candidates.
- [ ] Introduce reusable precomputed intermediates for market series and benchmark calculations.
- [ ] Add ranking for screened candidates and prioritize deep validation for the highest-scoring subset.
- [ ] Add a configurable deep-validation budget and deterministic candidate ordering.
- [ ] Update sweep reporting to record whether a candidate was screened out, deferred, or advanced to deep validation.
- [ ] Add tests covering early exit, reusable intermediates, deterministic lock selection, and reduced deep-validation workload.
