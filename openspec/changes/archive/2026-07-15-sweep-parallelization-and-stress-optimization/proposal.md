## Why

The sweep and stress-test pipeline already separates fast screening from heavier validation, but the current execution model still relies on a thread pool over CPU-heavy Python work. That leaves multicore capacity underused and makes large sweeps slower than necessary as the configuration space grows.

## What Changes

- Replace the current thread-based sweep executor with a process-based executor for CPU-bound configuration evaluation.
- Keep the existing fast-screen then exact-validation flow, but make the scheduling explicit so only shortlisted passing configurations incur the most expensive stress and artifact generation steps.
- Remove assumptions about shared mutable simulation caches across workers and move toward per-worker or read-only data reuse.
- Preserve existing CLI behavior and output artifacts while improving throughput on multicore machines.

## Capabilities

### New Capabilities
- `sweep-parallel-execution`: multicore configuration evaluation using process-based parallelism.
- `sweep-staged-validation`: a staged validation flow that limits expensive stress calculations to shortlisted candidates.

### Modified Capabilities
- `strategy-validation`: validation timing and execution strategy are changing, but the acceptance criteria remain the same.
- `portfolio-backtest`: runtime characteristics and orchestration are changing, but not the backtest contract itself.

## Impact

Affected areas include `src/quadbalance/sweep.py`, stress-test orchestration in `src/quadbalance/stress.py`, and any shared simulation caching or worker setup logic. The change may also affect test expectations around runtime behavior and concurrency safety, but should not alter user-facing results, report formats, or the CLI surface.
