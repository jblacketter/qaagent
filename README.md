# QA Agent (Python) with MCP

A Python-first QA agent scaffold designed to help analyze repos/apps, generate and run tests, and expose tooling via MCP (Model Context Protocol). Local-first, works on macOS and Windows. Uses Python, Typer CLI, and a minimal MCP server.

## Why this project
- Learn to build practical AI agents and MCP servers.
- Produce useful QA utilities: API fuzzing (Schemathesis), pytest orchestration, and later UI/Perf/A11y.
- Run locally; switch to stronger models/cloud later if needed.

## Recommended Python Version
Use Python 3.11 for project virtual environments. Python 3.13 is very new and some packages may lag. Keep your system Python as-is and create a 3.11 venv for this project.

## Quickstart

### 1) Create a venv (macOS)
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 2) Create a venv (Windows)
```powershell
py -3.11 -m venv .venv
. .venv\Scripts\activate
```

### 3) Install base dependencies
```bash
pip install -e .
```
Optional extras (install as needed):
```bash
# MCP runtime
pip install -e .[mcp]
# API testing
pip install -e .[api]
# UI testing (Playwright Python + browsers)
pip install -e .[ui]
# Performance testing
pip install -e .[perf]
# Report (HTML rendering)
pip install -e .[report]
# Config/Env convenience
pip install -e .[config]
# Local LLM (optional; enables generation/summarization)
pip install -e .[llm]
# Coverage (pytest-cov)
pip install -e .[cov]
```

### 4) CLI usage
```bash
# Show help
qaagent --help

# Analyze a repo (heuristics) and suggest a QA plan
qaagent analyze .

# Run pytest (writes JUnit XML to reports/pytest by default)
qaagent pytest-run --path tests --no-junit
# With coverage (writes coverage.xml + HTML report)
qaagent pytest-run --path tests --cov --cov-target src

# Run Schemathesis against an OpenAPI target (requires schemathesis)
qaagent schemathesis-run --openapi openapi.yaml --base-url http://localhost:8000

# Detect OpenAPI specs in a repo and/or probe a base URL
qaagent api-detect --path . --base-url http://localhost:8000 --probe

# Initialize config and env example
qaagent init

# Generate API test stubs (LLM optional; falls back to templates)
qaagent gen-tests --kind api --openapi openapi.yaml --base-url http://localhost:8000

# Summarize findings into a short executive summary (LLM optional)
qaagent summarize --out reports/summary.md
```

### 5) UI testing with Playwright (Python)
```bash
# Install Playwright Python + pytest plugins
pip install -e .[ui]

# Download browsers
qaagent playwright-install

# Scaffold a sample test
qaagent playwright-scaffold --dest tests/ui

# Run UI tests (headless by default)
qaagent ui-run --base-url https://example.com

# Run headed and choose browser
qaagent ui-run --base-url https://example.com --headed --browser firefox

# Accessibility checks with axe-core (Playwright)
qaagent a11y-run --url https://example.com --tag wcag2a --tag wcag2aa
# Machine-readable output
qaagent a11y-run --url https://example.com --json-out

# A11y from sitemap.xml (fetches URLs)
qaagent a11y-from-sitemap --base-url https://example.com --limit 30

# Lighthouse audit (Node required)
qaagent lighthouse-audit --url https://example.com
# Machine-readable output
qaagent lighthouse-audit --url https://example.com --json-out

# Perf testing with Locust
qaagent perf-scaffold
qaagent perf-run --users 25 --spawn-rate 5 --run-time 2m
# Machine-readable output
qaagent perf-run --json-out
```

### 6) MCP server (stdio)
```bash
# Requires the mcp package
qaagent-mcp
```
Use your preferred MCP client to connect over stdio and invoke tools:
- `schemathesis_run(openapi, base_url, outdir)`
- `pytest_run(path, junit, outdir)`
- `generate_report_tool(out, sources, title)`
 - `detect_openapi(path, base_url, probe)`
 - `a11y_run(url[], outdir, tag[], browser, axe_url)`
 - `lighthouse_audit(url, outdir, categories, device)`
 - `generate_tests(kind, openapi, base_url, max_tests)`
 - `summarize_findings(findings, fmt)`

## What’s here
- `src/qaagent/cli.py`: Typer CLI with useful QA commands.
- `src/qaagent/mcp_server.py`: Minimal MCP server exposing QA tools.
- `tests/test_smoke.py`: Import/version smoke test.
- `pyproject.toml`: Project config, scripts, optional extras.
 - UI commands: `playwright-install`, `playwright-scaffold`, `ui-run`.
 - Reporting: `qaagent report` to produce a consolidated Markdown report.
 - Config + API helpers: `.qaagent.toml`, `qaagent init`, `qaagent api-detect`, smarter `schemathesis-run`.

### 7) Generate a QA Findings report
```bash
# Create a consolidated Markdown report from default locations
qaagent report --out reports/findings.md

# Or specify JUnit files explicitly
qaagent report --out reports/findings.md \
  --sources reports/pytest/junit.xml --sources reports/schemathesis/junit.xml --sources reports/ui/junit.xml

# Generate an HTML report (requires jinja2)
pip install -e .[report]
qaagent report --format html --out reports/findings.html
# Machine-readable metadata
qaagent report --format html --out reports/findings.html --json-out

# Open the report in your browser
qaagent open-report --path reports/findings.html

# Export all reports to a zip
qaagent export-reports --reports-dir reports --out-zip reports/export.zip
```

The Findings report will automatically include sections for:
- Test suites (pytest/Schemathesis/UI) with failed/error cases
- Accessibility (axe) if `reports/a11y/a11y_*.json` are present
- Lighthouse scores and key metrics if a `lighthouse*.json` exists
- Performance summary (Locust) when `*stats.csv` is found

## Roadmap (Milestones)
1. API tooling: OpenAPI scanning + Schemathesis orchestration
2. UI tooling: Playwright scaffold + smoke flow + video/HTML reports
3. Reports: Aggregate artifacts into a concise QA Findings report
4. MCP: Expose tools via MCP with helpful schemas and outputs
5. Agent loop: Add planning/execution (e.g., LangGraph) when needed
6. Perf/A11y/Sec: Locust, Lighthouse, axe checks, basic ZAP scan
7. RAG/docs: Index repo/specs for context-aware analysis

## Notes
- Local LLMs with Ollama work well for tool-use reasoning. You can later add a switch to cloud models via LiteLLM if needed.
- On Windows, ensure CUDA-enabled packages match your driver/toolkit when you add GPU-accelerated libraries.

### Config and secrets
- Create config: `qaagent init` generates `.qaagent.toml` and `.env.example`.
- Set `API_TOKEN` (or your custom env) in `.env` (auto-loaded if you `pip install -e .[config]`).
- `schemathesis-run` reads defaults from `.qaagent.toml` if CLI flags are omitted.

## License
This scaffold is provided as-is for your learning and personal use.
