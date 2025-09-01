# QAAgent Handoff (Mac → Windows)

This single page lets you resume the project on your Windows machine and gives me enough context in a new session.

## Snapshot
- Codebase: Python 3.11 package + CLI + MCP server
- Capabilities: API (Schemathesis), UI (Playwright), A11y (axe), Lighthouse, Perf (Locust), Findings (MD/HTML), OpenAPI helpers, Config loader, optional LLM (Ollama) with fallbacks
- CI: `.github/workflows/qaagent.yml` builds Findings and uploads artifacts
- Docs: `README.md`, `docs/WINDOWS_SETUP.md`, `docs/PROJECT_STATUS.md`

## Resume Steps (Windows)
1) Clone/venv
   - `py -3.11 -m venv .venv && . .venv\Scripts\activate`
2) Install
   - Base: `pip install -e .`
   - Extras as needed: `[api, ui, report, config, perf, cov, llm]`
   - Playwright browsers: `qaagent playwright-install`
3) Sanity run
   - `qaagent analyze .`
   - `qaagent a11y-run --url https://example.com`
   - `qaagent lighthouse-audit --url https://example.com`
   - `qaagent perf-scaffold && setx BASE_URL https://example.com && qaagent perf-run --run-time 15s`
   - `qaagent pytest-run --cov --cov-target src`
   - `qaagent report --format html --out reports/findings.html`
4) Open report
   - `qaagent open-report --path reports/findings.html`

## Config
- Generate defaults: `qaagent init` → `.qaagent.toml` + `.env.example`
- Common env: `API_TOKEN`, `BASE_URL`
- LLM env (optional):
  - `QAAGENT_LLM=ollama`
  - `QAAGENT_MODEL=qwen2.5:14b` (or `llama3.1:8b`)

## LLM (Ollama) Enablement (Windows)
- Install Ollama, then: `ollama pull qwen2.5:14b`
- Install Python extras: `pip install -e .[llm]`
- Try:
  - `qaagent gen-tests --kind api --openapi openapi.yaml --base-url http://localhost:8000`
  - `qaagent summarize --out reports/summary.md`

## Next Tasks (Planned)
- Planner: `plan-run` orchestration with LangGraph (optional, later)
- Improve API generation prompts (auth flows, negative cases)
- UI generation: flow stubs from sitemap/navigation (future)
- CI: optionally add coverage gate / thresholds

## Where Things Go
- Reports: `reports/` (pytest, schemathesis, ui, a11y, lighthouse, perf, coverage)
- Config: `.qaagent.toml` and `.env`
- MCP server: `qaagent-mcp` (stdio)

## Known Notes
- Python 3.13 is not recommended yet; stick to 3.11 for venvs
- Lighthouse requires Node; CLI falls back to `npx` if `lighthouse` is not on PATH
- LLM features gracefully degrade when Ollama is not installed/running

