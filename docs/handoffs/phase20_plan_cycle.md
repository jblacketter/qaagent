# Phase 20 Plan Review Cycle

**Phase:** phase20
**Type:** plan
**Date:** 2026-02-16
**Lead:** claude
**Reviewer:** codex

## Reference
- Plan: [docs/phases/phase20.md](../phases/phase20.md)
- Predecessor: [Phase 19](../phases/phase19.md) (approved & implemented)

## Context

Phase 20 is the third and final phase of the three-phase plan. Phase 18 (quick fixes) and Phase 19 (enhanced product documentation) are both complete. This phase adds a "Talk to an Agent" feature allowing users to leverage an LLM for deeper project analysis, with token usage tracking.

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Phase 20 plan is ready for review. Five work packages:

**P1 — Agent Configuration Backend:**
- New `src/qaagent/api/routes/agent.py` with `POST/GET/DELETE /api/agent/config` endpoints.
- In-memory config store: provider, model, API key (masked on read).
- Mounted on `web_ui.py`.

**P2 — LLM Analysis Endpoint:**
- `POST /api/agent/analyze` collects `AppDocumentation` data (features, integrations, CUJs, user roles, journeys, tech stack) and sends structured prompt to LLM.
- Returns enhanced documentation text + token usage stats.
- `LLMClient` in `llm.py` gets API key override support (pass `api_key` param to litellm without persisting to env).
- `ChatResponse.usage` already returns `prompt_tokens`, `completion_tokens`, `total_tokens` — verified in current code.

**P3 — Token Usage Tracking:**
- In-memory per-session accumulator.
- `GET /api/agent/usage` returns cumulative usage + estimated cost.
- `DELETE /api/agent/usage` resets counters.
- Hardcoded price table for common models (Claude, GPT-4o, etc.).

**P4 — React UI — Agent Page:**
- New `Agent.tsx` page at `/agent` route.
- Config form (provider dropdown, model input, API key password field).
- "Talk to an Agent" analyze button with loading state.
- Results section rendering LLM output as markdown.
- Token usage widget showing cumulative tokens and cost.
- Sidebar + router updated.

**P5 — Tests:**
- Config CRUD endpoint tests.
- Token usage accumulation test.
- Contract test for `POST /api/agent/analyze` with mocked LLM.
- Frontend build verification.

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Reviewed `docs/phases/phase20.md`
- Cross-checked current architecture in `src/qaagent/web_ui.py`, `src/qaagent/api/routes/doc.py`, and frontend routing/sidebar context patterns

Strong points:
- Scope aligns with user request for an LLM-backed “Talk to an Agent” feature.
- Reuses existing `LLMClient` and usage metadata shape, which is a good base.

Blocking issues:

1. **[P2/P4] Repo context contract is missing for agent analysis.**
   - Existing doc flow is repo-scoped (`?repo=` in UI, `repo_id` in API), but this plan does not define how `/api/agent/analyze` selects which repository/documentation to analyze.
   - Required update: define explicit repo context contract (recommended: `repo_id` query param on agent endpoints + UI route/query propagation). Also define behavior for missing/invalid repo (no silent fallback).

2. **[P3] “Per-session” token usage scope is undefined.**
   - In-memory usage without a session key becomes process-global and mixes users/repos.
   - Required update: define concrete accumulator keying (at minimum by `repo_id`; ideally include client/session identifier) and document reset semantics against that key.

3. **[P1] API key persistence policy is ambiguous and unsafe.**
   - Plan allows optional plaintext token persistence in `~/.qaagent/agent.yaml`.
   - Required update: for this phase, make storage memory-only (no file persistence) and explicitly guarantee API key is never written to disk/logs/responses.

4. **[P2/P5] Missing explicit safeguards and tests for LLM cost/error boundaries.**
   - Plan sends rich project data but does not define prompt-size/token-budget limits or timeout/retry behavior.
   - Required update: add bounded prompt construction (size/token caps), request timeout, and tests for: invalid token/provider errors, masked config responses, and usage accounting on both success and handled failure paths.

Please update the plan with these specifics and resubmit.

## Round 2

### Lead
**Action:** SUBMIT_FOR_REVIEW

Rewrote `docs/phases/phase20.md` addressing all four blocking issues:

**1. [P2/P4] Repo context contract defined.**
- `POST /api/agent/analyze` requires `repo_id` query param. Missing → 400, not found → 404. No silent fallback.
- Config and usage endpoints also keyed by `repo_id`.
- Agent UI page reads `?repo=` from URL with no-repo guard (same pattern as doc pages).
- Sidebar propagates `?repo=` to Agent link.
- All `api.ts` agent methods accept `repoId`.

**2. [P3] Token usage scope concretely defined.**
- Usage accumulator is a `Dict[str, UsageAccumulator]` keyed by `repo_id` at module level.
- `GET /api/agent/usage?repo_id=X` returns per-repo stats. `repo_id` required (400 if missing).
- `DELETE /api/agent/usage?repo_id=X` resets per-repo counters.
- Reset semantics: zeroes all counters for that repo_id only.

**3. [P1] API key persistence: memory-only, explicitly guaranteed.**
- Removed all mention of `~/.qaagent/agent.yaml` or file persistence.
- API key stored in module-level dict keyed by `repo_id`. NEVER written to disk, logs, or responses.
- `GET /api/agent/config` returns masked key (first 4 + last 4 chars, rest `***`).
- On process restart, config must be re-entered.

**4. [P2/P5] Cost/error boundaries added.**
- Bounded prompt: 50,000 character cap on serialized project data. Truncates feature details while keeping summary + structure.
- 120-second timeout on LLM requests (passed to `litellm.completion(timeout=...)`).
- Usage accounting: accumulates on success AND handled failures (if usage returned before error). Network/timeout errors only increment `requests` counter.
- New test cases: masked config response, invalid token error, missing repo_id → 400, unknown repo → 404, LLM timeout error with usage accounting.

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Re-read updated `docs/phases/phase20.md`.
- Confirmed all prior blockers are now explicitly resolved:
  - Repo context contract is defined (`repo_id` required, 400/404 behavior, no silent fallback).
  - Usage scope is concretely keyed by `repo_id` with defined reset semantics.
  - API key policy is explicitly memory-only with no disk/log/full-response exposure.
  - Prompt/cost/error boundaries are specified (50k char cap, 120s timeout, explicit error-path tests).

Plan quality:
- Scope is now implementation-ready and consistent with existing repo-scoped UI/API patterns.
- Security and cost controls are concretely specified for this phase.
- Test plan covers both happy-path and critical failure/guardrail behavior.

No blocking issues remain.

---

<!-- CYCLE_STATUS -->
READY_FOR: none
ROUND: 2
STATE: approved
