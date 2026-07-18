# Proposal: Algorithmic sweep acceleration for validation runs

## Problem
`uv run quadbalance --output output --no-cache` currently evaluates every candidate configuration with the full validation stack. Even with parallel execution and caching, the command still spends most of its time on work that does not change the final locked strategy:

- full stress evaluation for every candidate
- long-term scenario analysis for every candidate
- repeated metric computation across similar configurations
- no early exit when a candidate has already failed acceptance criteria

This makes the sweep slower than necessary and limits scalability as the configuration space grows.

## Goal
Reduce end-to-end runtime by changing the validation sweep from a flat full-evaluation pass into a staged algorithm that prunes failing candidates early and reserves expensive analyses for promising configurations only.

## Proposed approach
1. **Two-stage sweep**
   - Stage 1: fast screening using simulation, core metrics, and a minimal acceptance gate.
   - Stage 2: deep validation only for candidates that pass Stage 1.

2. **Early exit / short-circuiting**
   - Stop evaluating additional expensive checks once a candidate has already failed irrecoverably.
   - Skip long-term and path-heavy analyses for candidates that cannot meet baseline thresholds.

3. **Candidate ranking before deep validation**
   - Score and sort candidates by a lightweight objective such as return-minus-risk margin.
   - Run deep validation only on the top-ranked subset and any candidates near the decision boundary.

4. **Reusable precomputed intermediates**
   - Precompute invariant time-series artifacts once per run (daily returns, drawdown base series, benchmark series).
   - Reuse these across candidates instead of recomputing identical transformations.

5. **Sweep-space pruning**
   - Allow the sweep to evaluate only the configuration dimensions that matter for lock selection.
   - Avoid unnecessary combinations that are known to be dominated or redundant.

## Expected outcome
The command should finish materially faster on large sweeps, with the largest wins coming from:
- fewer long-term scenario evaluations
- fewer full stress evaluations on obvious failures
- less repeated transformation work
- smaller effective candidate set

The final locked configuration and validated result files must remain behaviorally equivalent for candidates that still reach deep validation.
