## Context

QuadBalance has grown into a multi-workflow platform that includes backtesting, stress testing, validation, lock selection, reporting, and a NiceGUI-based workbench. The current codebase already reflects substantial domain complexity, so the main architectural risk is not missing capability but gradual erosion of module boundaries, duplicated rules, and inconsistent execution semantics across CLI, UI, and batch runs.

This design assumes the existing OpenSpec governance model remains the source of truth for requirements and that the implementation should preserve current behavior while making the architecture easier to reason about.

## Goals / Non-Goals

**Goals:**
- Separate core strategy logic from orchestration and presentation concerns.
- Standardize run identity, metadata, and artifact outputs across workflows.
- Reduce duplicated rule interpretation by centralizing validation and reporting contracts.
- Preserve deterministic behavior for candidate ranking and final lock selection.
- Make the codebase easier to extend with new stress scenarios, metrics, and views.

**Non-Goals:**
- Rewriting the entire engine or changing portfolio mathematics.
- Introducing a new external platform or service dependency.
- Redesigning the investor or strategy specification model.
- Altering acceptance criteria, stress thresholds, or suitability rules as part of this change.

## Decisions

### 1. Keep a single canonical run model
All execution paths should emit the same conceptual run record, even if the invocation comes from CLI, UI, or a sweep worker. This run model should contain input configuration, data/version references, selected scenario set, validation state, and artifact locations.

**Why this approach:** It makes auditability and reproducibility much simpler, and it prevents each workflow from inventing its own output contract.

**Alternatives considered:**
- Separate per-workflow result schemas: rejected because they increase drift and complicate downstream reporting.
- A loosely typed dictionary-only approach: rejected because it weakens validation and makes artifacts harder to trust.

### 2. Treat calculation code as pure as possible
Core backtest, stress, and validation logic should depend on explicit inputs and return structured outputs without side effects where practical. Orchestration layers can handle persistence, UI callbacks, and logging.

**Why this approach:** Pure-ish functions are easier to test, easier to cache, and safer to reuse across sweep, single-run, and lock-generation paths.

**Alternatives considered:**
- Stateful engine objects with hidden mutable context: rejected because they are harder to reason about and more error-prone under staged execution.
- Fully script-style orchestration: rejected because it encourages duplication and makes deterministic behavior harder to enforce.

### 3. Make validation output the shared contract for reporting
Reporting should consume the same structured validation result objects used by the engine rather than recomputing derived meanings from raw simulation output.

**Why this approach:** It avoids divergence between what the engine decided and what the report claims, especially for review-required and lockability outcomes.

**Alternatives considered:**
- Re-deriving statuses in the reporting layer: rejected because it duplicates business logic.
- Writing reporting-specific transforms from raw paths: rejected because it creates another semantic interpretation layer.

### 4. Preserve deterministic selection semantics
Any staged evaluation, ranking, or partial computation must not change the final selection outcome for identical inputs. Parallelization and deferral are acceptable only if they do not alter acceptance or lock choice.

**Why this approach:** The platform is used for strategy governance, so reproducibility and stable decision making are more important than opportunistic reordering.

**Alternatives considered:**
- Best-effort selection based on execution timing: rejected because it would make the lock outcome less auditable.
- Non-deterministic tie-breaking in sweeps: rejected because it would make comparisons and reviews unreliable.

### 5. Make the canonical data contract explicit
The platform should define explicit shared schemas for strategy inputs, simulation outputs, validation results, and artifact manifests so that no module invents its own ad hoc interpretation of core data.

**Why this approach:** A named, shared contract makes the architecture easier to evolve, reduces ambiguity in tests, and prevents subtle divergence across workflows.

**Alternatives considered:**
- Implicit agreement through informal conventions: rejected because it is fragile and hard to verify.
- Pushing all structure into the database: rejected because the project already treats file artifacts and in-memory results as primary integration points.

### 6. Make UI and presentation a strict orchestration boundary
UI and reporting layers should orchestrate user flows and render outputs, but they should not own validation rules, compute strategy decisions, or interpret acceptance criteria.

**Why this approach:** It prevents the presentation layer from becoming a second business logic implementation and keeps the domain logic testable without UI dependencies.

**Alternatives considered:**
- Embedding small pieces of decision logic in views or handlers: rejected because it leads to drift and hidden coupling.
- Duplicating validation checks in the UI for convenience: rejected because the UI must remain a consumer of core results, not a source of truth.

### 7. Let artifacts be the integration boundary
The system should standardize artifact emission for validation summaries, sweep outputs, and strategy lock documents so that the rest of the platform can rely on file-based evidence of each run.

**Why this approach:** Artifacts are the natural audit trail for this project and fit both human review and future automation.

**Alternatives considered:**
- In-memory only outputs: rejected because they do not support governance and post-run review.
- Database-only reporting state: rejected because the repository already uses file artifacts as part of its workflow and governance process.

## Risks / Trade-offs

- [Risk] Refactoring boundary definitions may temporarily touch many modules. → Mitigation: keep the first pass focused on shared contracts and artifact shape rather than behavior changes.
- [Risk] A canonical run model can become too broad if every new field is added ad hoc. → Mitigation: require explicit ownership for fields and prefer nested, purpose-specific sections.
- [Risk] Pure calculation functions may still need adapters for current code paths. → Mitigation: introduce orchestration wrappers gradually and keep adapters thin.
- [Risk] Tightening deterministic execution can expose hidden assumptions in tests or existing workflows. → Mitigation: update tests alongside the boundary refactor and preserve backward-compatible artifact fields where possible.
- [Risk] Standardizing artifacts may surface inconsistencies in legacy output formats. → Mitigation: support compatibility shims during migration and document canonical outputs clearly.
