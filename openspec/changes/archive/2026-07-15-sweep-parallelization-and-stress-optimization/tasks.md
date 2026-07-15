## 1. Parallel sweep execution

- [ ] 1.1 Replace the sweep thread pool with a process-based executor for CPU-bound configuration evaluation.
- [ ] 1.2 Remove or localize shared mutable simulation cache usage so worker execution is process-safe.
- [ ] 1.3 Preserve deterministic result collection and output generation after parallel evaluation.

## 2. Staged validation and stress orchestration

- [ ] 2.1 Keep fast validation as the first gate and ensure exact stress work only runs for shortlisted passing configurations.
- [ ] 2.2 Separate any expensive exact stress follow-up from the initial sweep loop so rejected configurations stop early.
- [ ] 2.3 Verify that stress-test outputs and lock-document generation remain unchanged for successful runs.

## 3. Verification and regression coverage

- [ ] 3.1 Add or update tests that cover process-safe sweep orchestration and staged validation behavior.
- [ ] 3.2 Confirm runtime and correctness with the existing test suite plus a representative full sweep execution.
- [ ] 3.3 Document any worker-count or multiprocessing assumptions that affect local development or CI.
