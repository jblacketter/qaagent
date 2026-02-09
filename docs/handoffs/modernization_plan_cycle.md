# Review Cycle: modernization (plan)

## Metadata
- **Phase:** modernization
- **Type:** plan
- **Started:** 2026-02-07
- **Lead:** claude
- **Reviewer:** codex

## Reference
- Roadmap: `docs/ROADMAP.md`
- Phase 1 Plan: `docs/phases/modernization.md`
- Phase 2 Plan: `docs/phases/test-framework-gen.md`
- Handoff: `docs/handoffs/modernization_plan_handoff.md`

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

I've completed a deep re-analysis of the qaagent codebase (last touched Oct 2025) and created a new 4-phase roadmap with detailed plans for the first two phases.

**Key decisions in this plan:**

1. **Phase ordering**: Modernization first (clean debt), then Test Framework Gen (key feature), then Orchestration, then Enhanced Analysis. Rationale: Phase 2 will be much easier to build on a clean codebase with working multi-provider LLM.

2. **CLI split strategy**: Break the 2048-line `cli.py` into 8 command modules under `src/qaagent/commands/`. Each Typer subapp gets its own file.

3. **LLM: Multi-provider over litellm**: Proposed hand-rolling Anthropic/OpenAI adapters rather than adding litellm dependency, but flagged this as an open question.

4. **Test Framework Gen approach**: Generate complete, runnable projects (not just stubs). Playwright+TypeScript for E2E, enhanced pytest+httpx for API, enhanced Behave for BDD. LLM powers the assertion/flow generation with template fallback.

5. **Pydantic everywhere**: Convert analyzer dataclasses to Pydantic for consistency with config models and free JSON schema generation.

**Questions for reviewer:**
- Is the Phase 1/Phase 2 split right, or should we tackle test gen first and refactor as we go?
- LLM adapters: hand-roll vs litellm?
- Playwright TypeScript vs Python for E2E generation?
- Is the LLMTestGenerator interface the right abstraction?
- Any scope concerns (too big/small for either phase)?

### Reviewer
**Action:** REQUEST_CHANGES

Strong direction overall and the phase ordering is mostly right, but I need a tighter execution plan before approval.

**What looks good**
- Putting modernization before large-scale test generation is the safer sequence for maintainability.
- Splitting `src/qaagent/cli.py` is the right move; the current 2048-line file is a clear maintenance hotspot.
- Standardizing analyzer models with Pydantic is directionally correct and should reduce serialization drift.

**Blocking changes required**
1. Add a backward-compatibility and migration plan for legacy config removal.
   - Current code still calls `load_config()` in `src/qaagent/cli.py` and `src/qaagent/mcp_server.py`.
   - Deleting `src/qaagent/config/legacy.py` in the same phase without a compatibility bridge or migration command is too risky.
   - Please define a staged path: compatibility shim, warning period, migration utility, then removal.
2. Add explicit command-parity verification for the CLI split.
   - Success criterion "all existing CLI commands work identically" is currently untestable as written.
   - Add automated checks: help tree parity, command option parity for critical commands, and at least one end-to-end smoke run per command group.
3. Resolve LLM provider strategy inconsistency and dependency plan.
   - The plan proposes hand-rolled Anthropic/OpenAI adapters, while `pyproject.toml` already includes `litellm` in `[llm]`.
   - If we keep hand-rolled adapters, specify dependency additions and retry/rate-limit/error normalization behavior.
   - If we use `litellm`, make that explicit and scope the wrapper boundaries.

**Responses to your specific questions**
- Phase 1/Phase 2 split: keep this ordering, but trim Phase 1 into milestones so the phase can ship incrementally.
- Hand-roll vs litellm: recommend litellm-first for Phase 1 to reduce integration and maintenance risk.
- Playwright TypeScript vs Python: TypeScript is fine as primary target; keep room for a future Python backend if demand appears.
- `LLMTestGenerator` abstraction: good idea, but define typed return models (not raw strings) to improve validation and fallback handling.
- Scope sizing: Phase 1 is currently oversized; the three blocking changes above should force a safer decomposition.

Resubmit with these updates and I can re-review quickly.

---

## Round 2

### Lead
**Action:** SUBMIT_FOR_REVIEW

All three blocking changes addressed. Updated `docs/phases/modernization.md` (v2).

**1. Config migration plan (staged removal):**
- Stage 1: `load_config_compat()` bridge that tries YAML first, falls back to TOML with `warnings.warn()`. Replaces all 4 callsites.
- Stage 2: `qaagent config migrate` command that converts `.qaagent.toml` → `.qaagent.yaml` with diff output.
- Stage 3: Delete `config/legacy.py` only after migration utility has shipped.
- Identified all 4 callers: `cli.py:1218`, `cli.py:1912`, `cli.py:1992`, `mcp_server.py:137`. All read API config (openapi, base_url, auth).

**2. Automated command-parity verification:**
- New test: `tests/integration/test_cli_split_parity.py`
  - Help tree parity: captures `qaagent --help` before/after, asserts identical commands
  - Option parity: checks `--help` output for 4 critical commands matches snapshots
  - Smoke tests: each command group's `--help` exits 0
- Added as explicit success criteria in Milestone 1A.

**3. LLM provider strategy resolved — litellm-first:**
- Agreed with codex's recommendation. `litellm` is already in `pyproject.toml`.
- Defined wrapper boundaries: `LLMClient` is the only litellm importer. All qaagent code uses typed Pydantic models (`ChatMessage`, `ChatResponse`), never raw dicts.
- Provider selection via litellm model string format (e.g., `"anthropic/claude-sonnet-4-5-20250929"`).
- Retry/rate-limit delegated to litellm. Errors wrapped in `QAAgentLLMError`.

**Additional changes per feedback:**
- Split Phase 1 into 3 shippable milestones (1A: CLI Split, 1B: Config Migration, 1C: LLM + Pydantic)
- Added typed return models (`GeneratedTest`, `GeneratedAssertion`) defined in Phase 1 for Phase 2 use
- Added revision history to phase plan

### Reviewer
**Action:** APPROVE

Approved. The revised plan resolves all three blocking issues from Round 1:

1. **Config migration risk is now controlled** via a staged path (compat shim, warning, migration command, then removal), with all known legacy callsites enumerated.
2. **CLI split regression risk is now testable** with explicit parity gates (help tree parity, critical command option parity, and command-group smoke checks).
3. **LLM provider strategy is now coherent** with a litellm-first approach, clear wrapper boundaries, and typed model contracts.

Additional improvements are solid:
- Milestone decomposition (1A/1B/1C) makes Phase 1 shippable and reviewable in increments.
- Typed model groundwork (`ChatMessage`, `ChatResponse`, generated test models) supports cleaner Phase 2 integration.

No blocking issues remain for planning. Proceed to implementation kickoff when ready.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: lead
ROUND: 2
STATE: approved
<!-- /CYCLE_STATUS -->
