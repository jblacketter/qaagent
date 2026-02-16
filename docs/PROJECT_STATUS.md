# QAAgent Project Status and Next Steps

This document captures current capabilities and the plan so we can resume work seamlessly (e.g., when moving to Windows for Ollama).

## Current Capabilities
- CLI (Typer): analyze, pytest-run, schemathesis-run (smart defaults, auth, filters), playwright install/scaffold/run, a11y-run (axe), lighthouse-audit, perf-scaffold/run, report (Markdown/HTML), init, api-detect.
- Phase 2 commands: `qaagent analyze routes|risks|strategy` for intelligent analysis and `qaagent generate behave` for BDD assets.
- Phase 3 additions: Target management (`qaagent targets add/list/remove`, `qaagent use`), workspace system (`~/.qaagent/workspace/<target>/`), `qaagent generate openapi` with Next.js route discovery, `qaagent dashboard` for interactive visual reports.
- **Web UI (NEW)**: Complete browser-based GUI (`qaagent web-ui`) with 5 tabs (Home, Configure, Commands, Reports, Workspace), real-time WebSocket updates, target management, command execution, and embedded dashboard viewer.
- **Enhanced Dashboard (NEW)**: Interactive HTML dashboard with tabs (Overview/Risks/Routes/Tests), clickable charts, advanced filtering, search, sortable tables, and risk detail modals.
- **Phase 6 — App Documentation (NEW)**: `qaagent doc generate|show|export|cujs` — auto-generates app documentation from route discovery (feature grouping, AST-based integration detection, CUJ discovery, architecture graphs, LLM prose synthesis). Full API + React Flow dashboard integration.
- **Phase 7 — Custom Risk Rules (NEW)**: `qaagent rules list|show|validate` — declarative YAML risk rules with match conditions (path/method/auth/tags/deprecated), severity escalation, severity overrides for built-in rules, file+inline merge with collision protection.
- **Phase 8 — Parallel Execution (NEW)**: Orchestrator-level concurrent suite execution with merged run summaries.
- **Phase 9 — Coverage Gaps (NEW)**: `qaagent analyze coverage-gaps` with route-level uncovered priority reporting and report integration.
- **Phase 10 — RAG Generation (NEW)**: `qaagent rag index|query` plus retrieval-aware `gen-tests` and generator prompt plumbing.
- **Phase 11 — New Language Parsers (NEW)**: Source route discovery support for Go (net/http, Gin, Echo), Ruby (Rails, Sinatra), and Rust (Actix, Axum).
- **Phase 12 — Notifications & CI Summaries (NEW)**: `qaagent notify` for CI-friendly summary output (`text|json`) with optional Slack webhook and SMTP email delivery.
- **Phase 13 — Live DOM Inspection (NEW)**: `qaagent analyze dom` for Playwright-based DOM inventory, selector coverage analysis, form/nav extraction, and actionable selector strategy recommendations.
- **Phase 14 — Live UI Route Crawling (NEW)**: `qaagent analyze routes --crawl` for Playwright-based runtime UI route discovery with depth/page/link limits and profile-aware auth/session defaults.
- **Phase 15 — AI-Assisted Test Recording (NEW)**: `qaagent record` for browser interaction capture to `recording.json` plus Playwright/Behave exports with deterministic selector ranking and sensitive input redaction.
- MCP server: pytest_run, schemathesis_run (with coverage meta), generate_report_tool, detect_openapi, a11y_run, lighthouse_audit.
- Findings report: Aggregates JUnit + artifacts; includes API coverage, A11y violations by impact, Lighthouse scores/metrics, Locust perf summary.
- Tests: smoke/version, OpenAPI parsing, report HTML generation, extras summarization.
- CI (GitHub Actions): runs tests, a11y on example.com, Lighthouse on example.com, short Locust run, and builds Findings HTML as artifact.

## Environment Guidance
- Use Python 3.11 virtual envs on macOS and Windows.
- Extras groups: [api], [ui], [report], [config], [perf].
- For UI: `qaagent playwright-install` after installing [ui].
- For Lighthouse: Node LTS installed; CLI uses `npx` if `lighthouse` not present.

## Next Steps (Ollama Integration)
1) Dependencies and wrapper
- Add extras group `[llm] = ["ollama>=0.1.0", "litellm>=1.40"]` (litellm optional).
- `src/qaagent/llm.py`:
  - Env/config: `QAAGENT_MODEL` (default: `qwen2.5:7b`), `QAAGENT_LLM=ollama|openai|anthropic`
  - Functions: `chat(messages, tools=None)`, `summarize(text)`, `generate_tests(input)`

2) Commands
- `qaagent gen-tests`:
  - Input: OpenAPI spec (auto-detect) and/or UI hints
  - Output: Stubs in `tests/api/` or `tests/ui/` with TODOs; respect config
- `qaagent summarize`:
  - Input: `reports/` artifacts + config
  - Output: A short executive summary (Markdown) including risks and next steps
- `qaagent plan-run`:
  - Simple LangGraph state machine: detect → choose tools → run → gather → summarize → report

3) MCP Tools
- `generate_tests`, `summarize_findings`, `plan_run` (stream progress chunks)

4) Models
- Default model: `qwen2.5:7b` (fast, ok quality)
- For higher quality: `qwen2.5:14b` or `llama3.1:8b`
- Keep client abstraction so swapping to cloud models is a one-line change

5) Security and Safety
- Respect tool execution boundaries and whitelisted paths
- Prompt templates avoid secrets logging (redact env tokens)

6) Documentation
- Update README with LLM setup, model choices, and examples
- Add examples directory for generated tests

## Useful Commands
- Full local run (example):
  - `qaagent analyze .`
  - `qaagent a11y-run --url https://example.com`
  - `qaagent lighthouse-audit --url https://example.com`
  - `qaagent perf-scaffold && BASE_URL=https://example.com qaagent perf-run --run-time 15s`
  - `qaagent report --format html --out reports/findings.html`

## Next Steps (Browser Automation / Live DOM Inspection)

Based on field testing with the Northstar QA environment (Angular app with Auth0, 30+ form fields), we compared `@playwright/mcp` (MCP Server) vs `playwright-cli` for AI-driven browser automation. See [BROWSER_AUTOMATION_STRATEGY.md](BROWSER_AUTOMATION_STRATEGY.md) for the full analysis.

**Key finding:** MCP Server uses **2.5x–3.8x more tokens** than playwright-cli for the same task due to inline accessibility snapshots on every action. Complex pages (large forms, dropdowns, modals) make this worse.

### Roadmap Items

**Completed: `qaagent analyze dom` command**
- Headless Playwright inspection (non-MCP) for live selector coverage
- Extracts element inventory, data-testid/ARIA coverage, form structure, and nav links
- Writes `dom-analysis.json` with selector strategy recommendations
- Supports profile-driven auth/session defaults (`.qaagent.yaml`, token env, storage-state fallback)

**Completed: `qaagent analyze routes --crawl`**
- Extend route discovery to crawl live UI via Playwright
- Follow links/navigation to discover routes not in OpenAPI spec
- Capture page structure at each route for test generation
- Feed into existing risk assessment and test generation pipelines

**Completed: `qaagent record` (AI-Assisted Test Recording)**
- LLM-driven browser exploration with goal-directed navigation
- Agent decides what to click/fill based on stated test goal
- Records actions as Behave scenarios or Playwright TypeScript
- Token budget management: snapshot throttling, targeted evals over full snapshots
- Use MCP only for interactive exploration; CLI/subprocess for everything else

**Next:** Define Phase 16 scope.

### Design Principles (from Northstar learnings)
1. **Prefer targeted `page.evaluate()` over full snapshots** — ask for exactly what you need
2. **Snapshots to files, read on demand** — don't bloat LLM context with full DOM trees
3. **MCP only when the agent needs to decide what to do next** — interactive exploration mode
4. **Subprocess for pipelines** — crawling, dom auditing, visual regression don't need LLM in the loop
5. **Budget for complex pages** — dropdowns, tables, modals multiply snapshot cost

## Open Questions / Future Ideas
- Add ZAP baseline scan integration
- Add coverage from pytest (python code coverage) into Findings
- Evaluate snapshot compression/filtering for MCP (if upstream adds opt-out flags)
