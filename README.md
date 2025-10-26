# QA Agent (Python) with MCP
[![QA Agent Tests](https://github.com/jackblacketter/qaagent/actions/workflows/qaagent.yml/badge.svg)](https://github.com/jackblacketter/qaagent/actions/workflows/qaagent.yml)

A Python-first QA agent scaffold designed to help analyze repos/apps, generate and run tests, and expose tooling via MCP (Model Context Protocol). Local-first, works great on macOS (including M1/M2/M3) and Windows. Uses Python, Typer CLI, and a minimal MCP server.

## Why this project
- Learn to build practical AI agents and MCP servers.
- Produce useful QA utilities: API fuzzing (Schemathesis), pytest orchestration, and later UI/Perf/A11y.
- Run locally; switch to stronger models/cloud later if needed.

## System Requirements
- **Python**: 3.11 recommended (3.13 is very new and some packages may lag)
- **Platform**: macOS (including M1/M2/M3) or Windows
- **Memory**: 8GB+ RAM (M1 Mac Mini is perfect for this)
- **LLM**: Optional - use Ollama locally or cloud APIs (Claude, GPT)

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

### 3) Install dependencies

**Option A: Using pip install (recommended for development)**
```bash
# Base dependencies only
pip install -e .

# Or install with extras (choose what you need)
pip install -e .[mcp]          # MCP server
pip install -e .[api]          # API testing (Schemathesis)
pip install -e .[ui]           # UI testing (Playwright)
pip install -e .[llm]          # Local LLM (Ollama) - optional
pip install -e .[report,config,cov,perf]  # Other extras
```

**Option B: Using requirements.txt files**
```bash
# Base dependencies
pip install -r requirements.txt

# Add specific features
pip install -r requirements-mcp.txt
pip install -r requirements-api.txt
pip install -r requirements-ui.txt
pip install -r requirements-llm.txt  # Optional

# Or install everything for development
pip install -r requirements-dev.txt
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

# Run environment health check
qaagent doctor
qaagent doctor --json-out

# Discover routes, collect evidence, and aggregate risks
qaagent analyze routes --openapi examples/petstore-api/openapi.yaml --out routes.json
qaagent analyze collectors examples/petstore-api
qaagent analyze risks --top 15 --json-out risks.json
qaagent analyze recommendations --json-out recommendations.json
# Start read-only API server
qaagent api --runs-dir ~/.qaagent/runs --port 8765
# Validate the analysis pipeline against the petstore example
scripts/validate_week1.sh

# Configure and switch between targets
qaagent config init . --template fastapi --name petstore
qaagent targets list
qaagent use petstore

# Generate BDD scenarios (Behave)
qaagent generate behave --out tests/qaagent/behave
behave tests/qaagent/behave

# Generate pytest unit tests
qaagent generate unit-tests --out tests/unit
pytest tests/unit

# Generate realistic test data (JSON, YAML, CSV)
qaagent generate test-data Pet --count 50 --format json --out fixtures/pets.json
qaagent generate test-data Owner --count 20 --format yaml --out fixtures/owners.yaml
qaagent generate test-data User --count 100 --format csv --seed 42 --out fixtures/users.csv

# Generate OpenAPI 3.0 spec from Next.js routes
qaagent generate openapi --auto-discover --out openapi.json
qaagent generate openapi --auto-discover --format yaml --title "My API" --version 2.0.0

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

## Examples

- [`examples/petstore-api`](examples/petstore-api/) bundles a FastAPI service, OpenAPI specification, and sample configuration so you can exercise QA Agent quickly.

```bash
# Install example dependencies (from project root)
pip install -r examples/petstore-api/requirements.txt

# Start the API server
uvicorn server:app --app-dir examples/petstore-api --port 8765

# In a second terminal, run the workflow
qaagent analyze examples/petstore-api
qaagent schemathesis-run --openapi examples/petstore-api/openapi.yaml --base-url http://localhost:8765
qaagent report --sources reports/schemathesis/junit.xml --out reports/findings.md
```

## What's here
- `src/qaagent/cli.py`: Typer CLI with useful QA commands.
- `src/qaagent/doctor.py`: Health checks used by `qaagent doctor`.
- `src/qaagent/mcp_server.py`: Minimal MCP server exposing QA tools.
- `src/qaagent/analyzers/`: Route discovery, Sprint 2 risk aggregation, coverage mapping, and recommendation engine.
- `src/qaagent/api/`: FastAPI application exposing runs, evidence, risks, and recommendations.
- `src/qaagent/discovery/`: **NEW!** Next.js App Router route discovery from source code (no OpenAPI spec needed).
- `src/qaagent/openapi_gen/`: **NEW!** OpenAPI 3.0 spec generator from discovered routes.
- `src/qaagent/repo/`: **NEW!** Git repository cloning, caching, and project type detection for remote repos.
- `src/qaagent/generators/`: Test generators with realistic Faker-based test data:
  - `behave_generator.py`: BDD scenarios for Behave
  - `unit_test_generator.py`: Enhanced pytest unit tests with realistic fixtures
  - `data_generator.py`: Realistic test data using Faker library
- `examples/petstore-api/`: FastAPI example with OpenAPI spec and QA Agent config.
- `tests/unit/`: Fast-running unit tests (100+ tests, 100% passing).
- `tests/integration/`: End-to-end workflows (petstore API, doctor, MCP).
- `tests/fixtures/data/`: Sample artifacts for report parsing tests.
- `pyproject.toml`: Project config, scripts, optional extras.
 - UI commands: `playwright-install`, `playwright-scaffold`, `ui-run`.
 - Reporting: `qaagent report` to produce a consolidated Markdown report.
 - Config + API helpers: `.qaagent.yaml`, `qaagent config init`, `qaagent api-detect`, smarter `schemathesis-run`.

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

### LLM Setup (Optional)
This project works perfectly **without** any LLM - all LLM features have template fallbacks.

If you want to use LLMs for test generation or summarization:

**Option 1: Local LLM with Ollama (recommended for M1/M2/M3 Macs)**
```bash
# Install Ollama from https://ollama.ai
# Or on Mac: brew install ollama

# Pull a model (lightweight options work great on M1)
ollama pull llama3.2:3b      # 3B params, fast, good for this use case
ollama pull phi3:mini        # Alternative lightweight model

# Start Ollama service
ollama serve
```

**Option 2: Cloud APIs via LiteLLM**
Set environment variables for Claude, GPT, etc. LiteLLM handles the rest.

**Mac M1/M2/M3 Users**: Your Mac is excellent for this project! Ollama runs very efficiently on Apple Silicon with unified memory. For 90% of use cases, you don't need a more powerful machine.

**Hybrid Setup**: If you have both a Mac and a Windows GPU machine, see [docs/HYBRID_SETUP.md](docs/HYBRID_SETUP.md) for how to use your Mac for development and offload heavy LLM tasks to your GPU server when needed (batch generation, large models, fine-tuning).

**Windows Users**: If you have CUDA GPU, ensure drivers match when using GPU-accelerated packages.

### Config and secrets
- Create config: `qaagent init` generates `.qaagent.toml` and `.env.example`.
- Set `API_TOKEN` (or your custom env) in `.env` (auto-loaded if you `pip install -e .[config]`).
- `schemathesis-run` reads defaults from `.qaagent.toml` if CLI flags are omitted.

## License
This scaffold is provided as-is for your learning and personal use.
