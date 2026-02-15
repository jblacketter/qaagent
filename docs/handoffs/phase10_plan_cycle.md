# Review Cycle: phase10 (plan)

## Metadata
- **Phase:** phase10
- **Type:** plan
- **Started:** 2026-02-14
- **Lead:** codex
- **Reviewer:** claude

## Reference
- Plan: `docs/phases/phase10.md`
- Implementation: N/A (plan review)

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Submitting Phase 10 plan: **RAG-Powered Test Generation**.

Plan summary:
- Add a local retrieval subsystem (`src/qaagent/rag/`) for indexing and querying repository context
- Integrate retrieval context into existing `LLMTestEnhancer`/generator flows with backward-compatible defaults
- Add CLI support for index/query and retrieval-enabled test generation workflows
- Keep V1 deterministic and dependency-light (no external vector DB), with explicit prompt-size controls and provenance tracking
- Add unit/integration tests for indexing, ranking, CLI behavior, and generator integration

This plan is scoped to local retrieval and generator context quality, not hosted retrieval infrastructure or UI surfaces.

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Read the full plan at `docs/phases/phase10.md`
- Cross-referenced against existing source files: `generators/llm_enhancer.py`, `generators/unit_test_generator.py`, `generators/behave_generator.py`, `generators/playwright_generator.py`, `commands/misc_cmd.py`, `commands/generate_cmd.py`, `commands/__init__.py`, `qaagent/llm.py`

Plan review:

1. **RAG Core (P1)** — Clean, well-scoped:
   - `rag/models.py`, `rag/indexer.py`, `rag/retriever.py` under `src/qaagent/rag/` is the right structure
   - Lexical scoring with no external deps is appropriate for V1
   - `.qaagent/rag/index.json` storage is consistent with existing `.qaagent/` conventions
   - Hard caps on chunk size and indexed bytes are essential — good call
   ✅

2. **Generator Integration (P2)** — Sound approach:
   - Extending `LLMTestEnhancer` with optional context input is clean — each method's `_chat()` can prepend retrieved snippets to the user prompt
   - All three generators (`UnitTestGenerator`, `BehaveGenerator`, `PlaywrightGenerator`) lazy-init the enhancer via `_get_enhancer()` — retrieval options can flow through the same path
   - Default-off behavior preserves backward compat
   ✅

3. **CLI Integration (P3)** — Practical and debuggable:
   - `rag index` and `rag query` as standalone commands makes retrieval inspectable
   - `gen-tests` enhancement flags are useful
   ✅

4. **Safety and Limits (P4)** — Appropriate safeguards:
   - Binary/non-text filtering, generated dir exclusion, per-snippet caps, source provenance
   ✅

5. **Success Criteria** — All 9 criteria are testable and well-defined ✅

Advisory notes (non-blocking, for implementation awareness):

1. **Two LLM generation paths**: The codebase has two distinct generation paths:
   - `gen-tests` (misc_cmd.py:234) → `generate_api_tests_from_spec()` in `qaagent/llm.py` — monolithic spec-based generation
   - `generate` subcommand (generate_cmd.py) → `UnitTestGenerator`/`BehaveGenerator`/`PlaywrightGenerator` → `LLMTestEnhancer` — per-route generation

   The plan's P2 correctly targets `LLMTestEnhancer`. The plan's P3 mentions `gen-tests` flags. Note that `gen-tests` does NOT use `LLMTestEnhancer` — it calls `generate_api_tests_from_spec()` directly. If `gen-tests` gets retrieval support, `qaagent/llm.py` needs modification (not currently in modified files list). Alternatively, scope V1 `gen-tests` retrieval to documentation only and defer `llm.py` changes.

2. **Missing from modified files**: `generate_cmd.py` should be listed if the `generate` subcommand gets retrieval-aware flags (e.g., `--rag`, `--top-k`). If retrieval is automatic when an index exists, the generators just need the index path — which can come from the active profile or convention.

3. **New command module**: The plan says "extend existing command registration with `rag` subgroup or equivalent" via `misc_cmd.py`. Given the pattern in `__init__.py` (each subgroup gets its own `*_cmd.py`), a dedicated `rag_cmd.py` would be more consistent with `doc_cmd.py`, `rules_cmd.py`, etc.

All three notes are implementation details, not plan-level issues. The architecture is sound, scope is well-bounded, and success criteria are clear.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: none
ROUND: 1
STATE: approved
<!-- /CYCLE_STATUS -->
