# Phase 26: QA Tool Suite Architecture

## Summary

Define the architecture for a QA Tool Suite that connects QA Agent, Bugalizer, and future tools into a cohesive ecosystem. Establish integration points, shared configuration, and a portfolio-ready presentation layer.

## Context

QA Agent is a mature framework (25 phases, 300+ tests) covering route discovery through reporting. Bugalizer is a separate service for AI-powered bug triage and code localization. Both share tech stack (Python, FastAPI, litellm/Ollama) and complementary QA domains. The user anticipates additional QA tools and wants a unified suite that is both functional and portfolio-presentable.

## Scope

### 1. Integration Points: QA Agent ↔ Bugalizer

**QA Agent → Bugalizer (issue submission):**
- When QA Agent's test orchestrator encounters failures, it could submit structured bug reports to Bugalizer's `/api/v1/reports` endpoint
- Risk findings (from `risk_assessment.py`) with severity >= high could auto-submit as bug reports
- Payload mapping: QA Agent's `TestResult` → Bugalizer's report schema (title from test name, description from failure diagnostics, steps from test flow, project_id from active target)

**Bugalizer → QA Agent (fix verification):**
- After Bugalizer produces a fix proposal, trigger QA Agent to re-run the relevant test suite against the patched code
- Bugalizer's localization results (candidate files + functions) can map to QA Agent's route coverage to identify which tests to re-run

**Shared data flows:**
- Route information from QA Agent's discovery feeds Bugalizer's localization (knowing which routes map to which code files)
- QA Agent's RAG index could be shared with Bugalizer to enhance its code understanding
- Both tools' LLM token usage could be aggregated for cost tracking

### 2. Architecture Decision: Meta-Project vs QA Agent as Hub

**Option A: QA Agent as Hub (not recommended)**
- Pros: No new repo, existing CLI/API can orchestrate
- Cons: QA Agent is already complex (2000-line CLI, 15+ phases). Cross-tool orchestration would add coupling and bloat. Bugalizer would become a dependency rather than a peer.

**Option B: New Meta-Project — "QA Suite" (recommended)**
- A lightweight orchestration layer that sits above all QA tools
- Responsibilities:
  - **Unified Configuration**: Shared `.qa-suite.yaml` for LLM settings, auth tokens, service URLs
  - **Service Registry**: Know where each tool's API is running (QA Agent on :8000, Bugalizer on :8001, etc.)
  - **Cross-Tool Workflows**: "Discover routes → Run tests → Submit failures to Bugalizer → Verify fixes" as a single pipeline
  - **Portfolio Dashboard**: A landing page / documentation site showcasing all tools with architecture diagrams
  - **Shared Libraries**: Common utilities extracted over time (auth, LLM client, config loader)
- Pros: Clean separation. Each tool evolves independently. Portfolio-ready landing page. Natural place for future tools.
- Cons: One more repo to maintain. Initial setup effort.

### 3. Feature Breakout Candidates (from QA Agent)

Features that could become standalone tools over time:

| Feature | Current Location | Standalone Value | Priority |
|---------|-----------------|-----------------|----------|
| **Test Generation** | `generators/` | High — reusable across projects, could serve as an API | Medium |
| **App Documentation** | `doc/` | High — useful independently of testing | Low |
| **Browser Recording** | `recording/` | Medium — lightweight standalone tool | Low |
| **CUJ Discovery** | `doc/cuj_discoverer.py` | Medium — ties into product management | Low |

**Recommendation:** Keep these in QA Agent for now. Extract only when there's a concrete need (e.g., another tool needs test generation). Premature extraction adds maintenance overhead without benefit.

### 4. Shared Infrastructure

Both tools already share:
- **LLM Backend**: Ollama locally, litellm for routing
- **Framework**: FastAPI + Pydantic
- **Testing**: pytest with mocked LLM calls
- **Auth pattern**: API key / session-based

The meta-project could provide:
- **Shared LLM config**: Single place to configure Ollama host, API keys, model preferences
- **Service health**: Unified health check across all tools
- **Token budget**: Aggregate LLM spend across tools with alerts

### 5. Deployment Environment Strategy

The QA Tool Suite must account for a two-stage hardware rollout: local Mac development now, with heavier LLM workloads migrating to a GPU-equipped Windows machine on the home LAN.

**Stage 1 — Local Development (current)**
- All tools run on macOS (Apple Silicon)
- Ollama runs locally at `http://localhost:11434`
- All service URLs are `localhost` — QA Agent on `:8000`, Bugalizer on `:8001`
- No LAN binding required; default security posture is localhost-only
- Config uses defaults — no explicit host configuration needed

**Stage 2 — LAN-Distributed LLM (next)**
- Development and tool APIs remain on Mac
- LLM inference moves to Windows machine with GPU (e.g., `192.168.x.x:11434`)
- Tools call the remote Ollama endpoint over LAN instead of localhost
- Tool APIs may optionally bind to LAN interfaces for cross-machine access

**Required config keys** (in `.qaagent.yaml` / `.qa-suite.yaml`):

```yaml
llm:
  ollama_base_url: http://localhost:11434     # Stage 1 default
  # ollama_base_url: http://192.168.1.50:11434  # Stage 2: Windows GPU host
  timeout: 120          # Higher default for LAN hops
  retry_count: 2        # Retry on transient LAN failures

suite:
  services:
    qaagent:
      url: http://localhost:8000
      api_key: ${QAAGENT_API_KEY}
    bugalizer:
      url: http://localhost:8001
      api_key: ${BUGALIZER_API_KEY}
```

**LAN security assumptions:**
- API key required on all tool endpoints when binding to non-localhost interfaces
- Tools default to `127.0.0.1` binding; explicit opt-in (`--host 0.0.0.0`) required for LAN access
- No TLS required for home LAN (trusted network), but API keys prevent unauthorized access
- Environment variables for secrets (`QAAGENT_API_KEY`, `BUGALIZER_API_KEY`, `ANTHROPIC_API_KEY`) — never stored in config files

**Sequencing impact on phases:**
- Phase 26a (documentation): No deployment dependency — works on Stage 1
- Phase 26b (concrete integration): Build with `ollama_base_url` and `suite.services` config keys from the start, defaulting to localhost. Stage 2 transition becomes a config change, not a code change
- Phase 26c (meta-project): Service registry naturally handles both stages via the `suite.services` block

## Technical Approach

### Phase 26a: Architecture Plan & Documentation (this cycle)
- Define QA Tool Suite architecture, integration points, and deployment strategy
- Add cross-reference in Bugalizer README (future — when suite visual is finalized)
- README suite graphic to be designed separately (removed from this cycle's scope)

### Phase 26b: Concrete Integration (future)
- Add `bugalizer` section to `.qaagent.yaml` config (URL, API key)
- Implement failure-to-bug-report submission in QA Agent's diagnostics module
- Add `qaagent submit-bug` CLI command

### Phase 26c: Meta-Project (future, if pursued)
- Create `qa-suite` repo with unified config loader
- Service registry and health aggregation
- Portfolio landing page (could be a simple static site or React dashboard)

## Files Changed

- `docs/phases/phase26.md` — This plan (architecture, integration points, deployment strategy)

## Success Criteria

1. Architecture plan documents concrete integration points between QA Agent and Bugalizer
2. Clear recommendation on meta-project vs hub approach with reasoning
3. Deployment environment strategy defined for Mac-local and LAN-distributed stages
4. Feature breakout candidates identified with reasoning
