# Phase 20: Talk to an Agent — LLM Deep Analysis

## Summary

Add a "Talk to an Agent" feature that allows users to send their project's documentation and analysis data to an LLM (Claude, GPT, or local Ollama) for enhanced, AI-generated product descriptions. Includes API token configuration, a dedicated UI page, and a token usage tracking widget showing input/output tokens and estimated costs.

## Scope

### P1: Agent Configuration Backend
- **File:** `src/qaagent/api/routes/agent.py` (NEW)
- New API router with endpoints:
  - `POST /api/agent/config` — Save agent configuration (provider, model, API token).
  - `GET /api/agent/config` — Return current config (token masked: first 4 + last 4 chars shown, rest replaced with `***`).
  - `DELETE /api/agent/config` — Clear stored config.
- Configuration model: `provider` (anthropic/openai/ollama), `model` (string), `api_key` (string).
- **Storage policy: memory-only.** API key is NEVER written to disk, logs, or returned in full in any response. Stored in a module-level dict keyed by `repo_id`. On process restart, config must be re-entered.
- Mount router on `web_ui.py`.

### P2: LLM Analysis Endpoint
- **File:** `src/qaagent/api/routes/agent.py`
- `POST /api/agent/analyze?repo_id=<repo_id>` — Main analysis endpoint:
  1. **Repo context:** `repo_id` is required. If missing → 400. If not found → 404. No silent fallback. Loads `AppDocumentation` from the repo's `.qaagent/appdoc.json`.
  2. **Bounded prompt construction:** Collect project data (features, integrations, CUJs, user roles, journeys, tech stack). Serialize to structured text. **Cap prompt at 50,000 characters** (truncate feature details if needed, keeping summary + high-level structure). This prevents runaway token costs.
  3. Build a system prompt asking the LLM to produce: detailed app overview, refined feature descriptions, user journey narratives, role-based access description, and suggestions for missing documentation.
  4. Call LLM via `LLMClient` with user-provided API key override and a **300-second timeout** (agent analysis sends large prompts that can take several minutes to process).
  5. Return: `{ content: string, usage: { prompt_tokens, completion_tokens, total_tokens }, model: string }`.
- **File:** `src/qaagent/llm.py`
  - Add `api_key` parameter to `LLMClient.__init__()` and pass it to `litellm.completion()` via the `api_key` kwarg (litellm supports this natively). Do NOT set environment variables.
  - Add `timeout` parameter to `chat()` method, defaulting to 120 seconds. Pass to `litellm.completion(timeout=...)`.

### P3: Token Usage Tracking
- **File:** `src/qaagent/api/routes/agent.py`
- **Usage accumulator keyed by `repo_id`**: `Dict[str, UsageAccumulator]` stored at module level.
  - `GET /api/agent/usage?repo_id=<repo_id>` — Return cumulative usage for this repo: `{ repo_id, requests, prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd }`. Returns zeroed stats if no usage yet. `repo_id` required (400 if missing).
  - `DELETE /api/agent/usage?repo_id=<repo_id>` — Reset usage counters for this repo.
- **Usage accounting:** Accumulate on both success AND handled failure paths (if the LLM returned a response with usage before erroring, count it). On network/timeout errors where no usage is returned, only increment `requests` counter.
- Cost estimation: hardcoded price table for common models (Claude Sonnet/Opus input/output per 1M tokens, GPT-4o, etc.). Falls back to $0 if model not in table.

### P4: React UI — Agent Page
- **File:** `src/qaagent/dashboard/frontend/src/pages/Agent.tsx` (NEW)
- New page at `/agent` route, reads `?repo=` from URL (same pattern as doc pages):
  - **No-repo guard:** If `?repo=` is absent, show "Select a repository" prompt with link to `/repositories`.
  - **Configuration Section**: Form with provider dropdown (Anthropic, OpenAI, Ollama), model text input, API key password input. Save/Clear buttons. Passes `repo_id` to API calls.
  - **Analyze Button**: "Talk to an Agent" button. Shows loading spinner during analysis. Disabled until config is saved.
  - **Results Section**: Rendered markdown of the LLM's enhanced documentation output.
  - **Token Usage Widget**: Small card/panel showing cumulative tokens used for this repo, estimated cost (e.g., "$0.0042"), and a reset button. Refreshes after each analysis call.
- **File:** `src/qaagent/dashboard/frontend/src/App.tsx` — Add `/agent` route.
- **File:** `src/qaagent/dashboard/frontend/src/components/Layout/Sidebar.tsx` — Add "Agent" link to repoLinks with `?repo=` propagation.
- **File:** `src/qaagent/dashboard/frontend/src/services/api.ts` — Add agent API methods (all accept `repoId`).

### P5: Tests
- Config CRUD endpoint tests (save, read masked, delete).
- **Test: GET /api/agent/config returns masked API key** (never full key in response).
- Token usage accumulation test (multiple requests accumulate correctly, keyed by repo_id).
- Token usage reset test.
- Contract test: `POST /api/agent/analyze` with mocked LLM returns expected structure + usage.
- **Error boundary tests:** invalid token → clear error message; missing repo_id → 400; unknown repo → 404; LLM timeout → error response with usage accounting.
- Frontend builds successfully.

## Files Changed

| File | Change |
|------|--------|
| `src/qaagent/api/routes/agent.py` | NEW — Agent config, analyze, usage endpoints |
| `src/qaagent/llm.py` | `api_key` + `timeout` params on LLMClient/chat |
| `src/qaagent/web_ui.py` | Mount agent router |
| `src/qaagent/dashboard/frontend/src/pages/Agent.tsx` | NEW — Agent UI page with repo context |
| `src/qaagent/dashboard/frontend/src/App.tsx` | Add /agent route |
| `src/qaagent/dashboard/frontend/src/components/Layout/Sidebar.tsx` | Add Agent nav link with ?repo= |
| `src/qaagent/dashboard/frontend/src/services/api.ts` | Agent API methods (all repo-scoped) |
| `tests/api/test_agent.py` | NEW — Agent endpoint tests |

## Success Criteria

1. User can configure an API token via the UI and it persists in memory for the process lifetime.
2. API key is NEVER written to disk, logs, or returned in full (masked display only).
3. "Talk to an Agent" sends repo-scoped project data to the configured LLM and returns enhanced documentation.
4. Prompt is bounded (50k char cap) and requests have a 300s timeout (large prompts require extended processing time).
5. Token usage widget displays accurate per-repo token counts and cost estimate.
6. Usage accumulates correctly across multiple requests and resets per repo.
7. Missing/invalid repo_id returns appropriate HTTP errors (400/404).
8. Graceful error handling: clear messages for invalid tokens, network failures, rate limits.
9. Frontend builds successfully. All tests pass.

## Dependencies

- Phase 19 must be completed first (enhanced doc models provide the data sent to the agent).
- Existing `LLMClient` in `src/qaagent/llm.py` provides the foundation.

## Future Integration

- Token analyzer project (user's separate GitHub repo) can be integrated as a more sophisticated cost tracking system in a future phase.
- Agent could be extended to support multi-turn conversations (chat mode) rather than single-shot analysis.
