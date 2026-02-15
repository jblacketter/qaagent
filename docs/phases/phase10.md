# Phase 10: RAG-Powered Test Generation

## Status
- [x] Planning
- [x] In Review
- [ ] Approved
- [ ] Implementation
- [ ] Implementation Review
- [ ] Complete

## Roles
- Lead: codex
- Reviewer: claude
- Arbiter: Human

## Summary
**What:** Add repository-aware retrieval to test generation so LLM prompts include relevant local context (code, docs, and specs) instead of only route metadata.
**Why:** Current LLM generation works, but prompts often miss project-specific conventions and domain rules. Retrieval context should improve test relevance and reduce generic output.
**Depends on:** Phase 9 (Coverage Gap Analysis) - Complete

## Context

The codebase already has:
- `qaagent.llm.LLMClient` for provider/model abstraction
- `LLMTestEnhancer` used by `UnitTestGenerator`, `BehaveGenerator`, and `PlaywrightGenerator`
- `qaagent gen-tests` command for API test generation from OpenAPI

What is missing is a stable retrieval layer that indexes repo context and feeds high-signal snippets into LLM prompts.

## Scope

### In Scope
- Local indexing pipeline for repository context:
  - source files (`src/**`, selected app paths)
  - docs (`README.md`, `docs/**`)
  - API specs (`openapi*.yaml|json`, swagger variants)
- Lightweight retrieval engine (no external service) for top-k context snippets by relevance to route/test intent
- Integration into LLM enhancement path so prompts can include retrieved context
- CLI support to build/query index and to enable retrieval in `gen-tests`
- Test coverage for chunking, retrieval ranking, integration wiring, and fallback behavior

### Out of Scope
- External vector databases or hosted embedding services
- Multi-repo/global index management
- UI/dashboard retrieval visualization
- Automatic agent loops beyond test generation

## Technical Approach

### P1 - RAG Core

Add a new retrieval package under `src/qaagent/rag/`:
- `models.py`:
  - `RagDocument`, `RagChunk`, `RagSearchResult`
- `indexer.py`:
  - walks repository paths
  - applies include/exclude filters
  - chunks files into bounded text segments with file/path metadata
  - writes index to `.qaagent/rag/index.json`
- `retriever.py`:
  - lexical relevance scoring (deterministic, dependency-light)
  - query by route/method/risk text
  - returns top-k chunks with score and source path

Design constraints:
- No required new dependency for V1 retrieval ranking
- Deterministic results for stable tests
- Hard caps on chunk size and total indexed bytes

### P2 - Generator Integration

Integrate retrieval into existing LLM enhancement without breaking current behavior:
- extend `LLMTestEnhancer` with optional retrieval context input
- plumb retrieval options through generators that already use enhancer
- default behavior remains unchanged when retrieval is disabled or index missing

Primary integration points:
- `src/qaagent/generators/llm_enhancer.py`
- `src/qaagent/generators/unit_test_generator.py`
- `src/qaagent/generators/behave_generator.py`
- `src/qaagent/generators/playwright_generator.py`

### P3 - CLI Integration

Add practical CLI entrypoints:
- `qaagent rag index`:
  - build/update local retrieval index for active target or cwd
- `qaagent rag query`:
  - inspect retrieved chunks for a query
- `qaagent gen-tests` enhancement:
  - flags to enable retrieval and set top-k context snippets

This keeps retrieval debuggable and avoids hidden behavior.

### P4 - Safety and Limits

To avoid noisy prompts and token blowups:
- enforce max snippets and per-snippet character limits
- strip binary/non-text files
- skip large generated directories (e.g., `node_modules`, `.venv`, build outputs)
- include source provenance for every snippet in prompt context

## Files to Create/Modify

### New Files
- `src/qaagent/rag/__init__.py`
- `src/qaagent/rag/models.py`
- `src/qaagent/rag/indexer.py`
- `src/qaagent/rag/retriever.py`
- `tests/unit/rag/test_indexer.py`
- `tests/unit/rag/test_retriever.py`
- `tests/integration/commands/test_rag_cmd.py`

### Modified Files
- `src/qaagent/generators/llm_enhancer.py`
- `src/qaagent/generators/unit_test_generator.py`
- `src/qaagent/generators/behave_generator.py`
- `src/qaagent/generators/playwright_generator.py`
- `src/qaagent/commands/misc_cmd.py` (extend existing command registration with `rag` subgroup or equivalent)
- `src/qaagent/commands/__init__.py` (if new command module is added)
- `tests/integration/commands/test_misc_cmd.py` or new rag command test file
- `tests/fixtures/cli_snapshots/pre_split_commands.json` (if command tree changes)

## Success Criteria
- [ ] `qaagent rag index` builds a local index for supported text files
- [ ] `qaagent rag query` returns deterministic top-k snippets with scores and file paths
- [ ] `gen-tests` can run with retrieval-enabled prompts using local context snippets
- [ ] Retrieval-disabled path behaves exactly as today (backward compatibility)
- [ ] Prompt context includes source provenance and obeys configured caps
- [ ] Non-text/oversized/generated files are excluded by default
- [ ] Unit tests cover chunking, indexing, ranking, and filtering logic
- [ ] Integration tests cover CLI commands and generator wiring
- [ ] No regressions in existing `gen-tests` behavior when retrieval is off

## Resolved Decisions
- **Retrieval backend (V1):** dependency-light lexical scoring and local JSON index; no external vector DB.
- **LLM dependency:** retrieval path must still work when LLM extras are unavailable (index/query remain usable).
- **Prompt policy:** include only top-k bounded snippets with file provenance; no full-file dumps.

## Risks
- **Prompt bloat:** too much context can hurt quality. Mitigation: strict top-k and size caps.
- **Irrelevant retrieval:** lexical matching can be noisy. Mitigation: path weighting + method/route token boosts and tests on fixtures.
- **Index staleness:** code changes can desync index. Mitigation: clear rebuild command and stale-index warning metadata.
