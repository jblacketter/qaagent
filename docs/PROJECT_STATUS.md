# QAAgent Project Status and Next Steps

This document captures current capabilities and the plan so we can resume work seamlessly (e.g., when moving to Windows for Ollama).

## Current Capabilities
- CLI (Typer): analyze, pytest-run, schemathesis-run (smart defaults, auth, filters), playwright install/scaffold/run, a11y-run (axe), lighthouse-audit, perf-scaffold/run, report (Markdown/HTML), init, api-detect.
- Phase 2 commands: `qaagent analyze routes|risks|strategy` for intelligent analysis and `qaagent generate behave` for BDD assets.
- Phase 3 additions: Target management (`qaagent targets add/list/remove`, `qaagent use`), workspace system (`~/.qaagent/workspace/<target>/`), `qaagent generate openapi` with Next.js route discovery, `qaagent dashboard` for interactive visual reports.
- **Web UI (NEW)**: Complete browser-based GUI (`qaagent web-ui`) with 5 tabs (Home, Configure, Commands, Reports, Workspace), real-time WebSocket updates, target management, command execution, and embedded dashboard viewer.
- **Enhanced Dashboard (NEW)**: Interactive HTML dashboard with tabs (Overview/Risks/Routes/Tests), clickable charts, advanced filtering, search, sortable tables, and risk detail modals.
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

## Open Questions / Future Ideas
- Add ZAP baseline scan integration
- Add coverage from pytest (python code coverage) into Findings
- RAG: index repo/docs/specs for better context
- Add Slack/Email notifier for Findings summary in CI
