## Context

The current sweep pipeline already stages work in two phases: a fast validation pass and a more expensive exact pass for shortlisted configurations. However, the main orchestration still uses a thread pool around CPU-heavy Python simulation work, which limits multicore scaling under the GIL and also shares mutable cache state across workers.

The change is performance-focused and touches orchestration rather than strategy semantics. The existing CLI, reports, and validation criteria should remain unchanged.

## Goals / Non-Goals

**Goals:**
- Use multiple CPU cores effectively for sweep evaluation.
- Keep the fast-screen / exact-validation structure intact.
- Avoid unsafe sharing of mutable simulation cache state between workers.
- Preserve output artifacts and user-facing CLI behavior.
- Keep the implementation maintainable and easy to reason about.

**Non-Goals:**
- Rewriting the simulation engine into NumPy-only vectorized code.
- Changing portfolio logic, acceptance thresholds, or stress scenario definitions.
- Introducing a new external runtime dependency.
- Redesigning report formats or CLI flags.

## Decisions

1. **Use process-based parallelism for sweep evaluation**

   The sweep workload is CPU-bound and dominated by Python-level simulation and validation. A process pool is the better default than a thread pool because it bypasses the GIL for independent workers and better matches the existing configuration-isolated workload.

   Alternatives considered:
   - Thread pool: simpler, but limited benefit for CPU-bound work.
   - Single-threaded execution: lowest complexity, but leaves performance on the table.
   - Native extension / JIT rewrite: potentially faster, but much larger scope and higher risk.

2. **Keep the staged validation pipeline**

   The current flow of fast screening followed by exact stress work for shortlisted candidates is already a good performance optimization. The design should preserve that shape rather than collapse everything into one expensive pass.

   Alternatives considered:
   - Run full stress tests for every configuration: simplest, but too expensive.
   - Add more screening heuristics: possible later, but not necessary for this change.

3. **Eliminate shared mutable cache coordination across workers**

   A shared simulation cache is not a good fit for multi-process execution and is fragile even under threads. Each worker should rely on local reuse only, while the main process controls scheduling and any read-only data precomputation.

   Alternatives considered:
   - Keep a shared cache via manager objects: adds synchronization overhead and complexity.
   - Precompute everything centrally: can help some workloads, but does not remove the need for worker-local execution.

4. **Keep exact stress tests confined to shortlisted passing candidates**

   Exact stress tests and artifact generation should only run after a configuration has already passed the fast acceptance path. This avoids duplicating the most expensive work across the full search space.

   Alternatives considered:
   - Run exact stress in the same phase for all configs: simpler control flow, worse runtime.
   - Parallelize exact stress separately: useful later, but secondary to fixing the main sweep bottleneck.

## Risks / Trade-offs

- [Serialization overhead] → Keep worker inputs compact and pass large read-only inputs only when necessary.
- [Process startup cost] → Use bounded worker counts and avoid spawning more processes than the workload can amortize.
- [Platform behavior differences] → Test on macOS and Linux-style multiprocessing semantics to ensure stable startup and cleanup.
- [Cache duplication] → Accept some duplicated memory usage in exchange for safer parallel execution.
- [Harder debugging] → Keep the worker function boundaries narrow and preserve existing deterministic ordering where practical.
