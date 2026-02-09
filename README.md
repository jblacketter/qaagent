# QA Agent

A Python QA automation framework that discovers API routes, assesses risks, generates runnable test suites, orchestrates test execution, and produces reports. Exposes tooling via CLI (Typer) and MCP (Model Context Protocol). Local-first, works on macOS (including Apple Silicon) and Windows.

## Features

- **Route Discovery** - Extract API routes from OpenAPI specs or source code (FastAPI, Flask, Django, Next.js)
- **Risk Assessment** - 16 pluggable rules across security, performance, and reliability categories
- **Test Generation** - Produce runnable pytest, Behave BDD, and Playwright E2E test suites
- **Test Orchestration** - Run generated suites with retry, JUnit parsing, and failure diagnostics
- **CI/CD Generation** - Generate GitHub Actions and GitLab CI pipeline templates
- **Reporting** - Markdown/HTML reports, interactive dashboards, executive summaries
- **MCP Server** - Expose QA tools to AI agents via Model Context Protocol
- **LLM Integration** - Optional LLM enhancement via Ollama (local) or cloud APIs (Claude, GPT) through litellm

## System Requirements

- **Python**: 3.11+ (< 3.13)
- **Platform**: macOS (including M1/M2/M3) or Windows
- **Memory**: 8GB+ RAM
- **LLM**: Optional - works without any LLM; all features have template fallbacks

## Quickstart

```bash
# Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install (choose extras you need)
pip install -e .                    # Core
pip install -e .[api]               # + API testing (Schemathesis)
pip install -e .[ui]                # + UI testing (Playwright)
pip install -e .[llm]              # + LLM providers (Ollama, litellm)
pip install -e .[mcp]              # + MCP server
pip install -e .[report,config,cov,perf]  # + Reporting, config, coverage, perf

# Verify installation
qaagent doctor
```

## Usage

### Configure a Target

```bash
# Initialize a project profile
qaagent config init . --template fastapi --name my-api
qaagent use my-api

# Or point at an existing OpenAPI spec
qaagent analyze routes --openapi openapi.yaml --out routes.json
```

### Discover Routes

```bash
# From OpenAPI spec
qaagent analyze routes --openapi openapi.yaml --format json --out routes.json

# From source code (FastAPI, Flask, Django)
qaagent analyze routes --source-dir ./src --out routes.json

# Generate strategy from discovered routes
qaagent analyze strategy --routes-file routes.json --out strategy.yaml
```

### Generate Tests

```bash
# Generate pytest unit tests
qaagent generate unit-tests --routes-file routes.json --out tests/unit

# Generate Behave BDD scenarios
qaagent generate behave --routes-file routes.json --out tests/behave

# Generate Playwright E2E project (TypeScript)
qaagent generate e2e --routes-file routes.json --out tests/e2e

# Generate all enabled suites from .qaagent.yaml
qaagent generate all

# Generate CI/CD pipeline
qaagent generate ci --platform github --framework fastapi
qaagent generate ci --platform gitlab --framework django
```

### Run Tests

```bash
# Run pytest
qaagent pytest-run --path tests --cov --cov-target src

# Run all generated suites with orchestration
qaagent run-all

# Full pipeline: discover -> assess -> generate -> run -> report
qaagent plan-run --generate
```

### Reports

```bash
# Generate findings report
qaagent report --fmt html --out reports/findings.html

# Interactive dashboard
qaagent dashboard

# Executive summary (LLM-enhanced if available)
qaagent summarize --out reports/summary.md

# Open in browser
qaagent open-report --path reports/findings.html
```

### Additional Tools

```bash
# API property-based testing
qaagent schemathesis-run --openapi openapi.yaml --base-url http://localhost:8000

# Accessibility
qaagent a11y-run --url https://example.com --tag wcag2a

# Performance
qaagent perf-run --users 25 --spawn-rate 5 --run-time 2m

# Lighthouse audit
qaagent lighthouse-audit --url https://example.com
```

### MCP Server

```bash
qaagent-mcp  # Starts MCP server over stdio
```

Exposes tools: `schemathesis_run`, `pytest_run`, `generate_report_tool`, `detect_openapi`, `a11y_run`, `lighthouse_audit`, `generate_tests`, `summarize_findings`.

## Project Structure

```
src/qaagent/
  cli.py                    # Typer CLI entry point
  commands/                 # CLI command modules
    analyze_cmd.py          #   Route discovery, risk assessment, strategy
    generate_cmd.py         #   Test & CI/CD generation
    run_cmd.py              #   Test execution (pytest, playwright, schemathesis, etc.)
    report_cmd.py           #   Reporting and dashboards
    config_cmd.py           #   Configuration management
    workspace_cmd.py        #   Workspace management
  analyzers/
    route_discovery.py      # OpenAPI + source code route extraction
    risk_assessment.py      # Pluggable risk rule engine
    rules/                  # 16 risk rules (security, performance, reliability)
    strategy_generator.py   # Test strategy recommendations
  discovery/
    base.py                 # FrameworkParser ABC + RouteParam model
    fastapi_parser.py       # AST-based FastAPI route extraction
    flask_parser.py         # AST-based Flask/Blueprint parsing
    django_parser.py        # URL patterns + DRF ViewSet parsing
    nextjs_parser.py        # Next.js App Router discovery
  generators/
    base.py                 # BaseGenerator ABC + GenerationResult
    unit_test_generator.py  # pytest test generation
    behave_generator.py     # BDD scenario generation
    playwright_generator.py # Playwright TypeScript E2E generation
    cicd_generator.py       # GitHub Actions / GitLab CI templates
    llm_enhancer.py         # LLM-powered test enhancement
    validator.py            # Syntax validation + auto-fix
  runners/
    base.py                 # TestRunner ABC + TestCase/TestResult models
    pytest_runner.py        # pytest subprocess wrapper
    playwright_runner.py    # Playwright subprocess wrapper
    behave_runner.py        # Behave subprocess wrapper
    orchestrator.py         # Config-driven suite execution with retry
    diagnostics.py          # Heuristic + LLM failure analysis
    junit_parser.py         # Generic JUnit XML parser
  config/
    models.py               # Pydantic config models (QAAgentProfile, etc.)
  llm.py                    # Multi-provider LLM client via litellm
  mcp_server.py             # MCP server exposing QA tools
  templates/                # Jinja2 templates (Playwright, CI/CD, unit tests)
```

## Configuration

qaagent uses `.qaagent.yaml` profiles per project:

```yaml
project:
  name: my-api
  type: fastapi

app:
  dev:
    base_url: http://localhost:8000

openapi:
  spec_path: openapi.yaml
  source_dir: src

tests:
  unit:
    enabled: true
    output_dir: tests/qaagent/unit
  behave:
    enabled: true
    output_dir: tests/qaagent/behave
  e2e:
    enabled: false
    output_dir: tests/qaagent/e2e

risk_assessment:
  disable_rules: []  # e.g. ["SEC-002", "PERF-004"]

llm:
  enabled: false
  provider: ollama
  model: qwen2.5-coder:7b
```

## LLM Setup (Optional)

All features work without LLM - test generators fall back to templates.

**Local (Ollama):**
```bash
brew install ollama
ollama pull llama3.2:3b
ollama serve
```

**Cloud APIs (via litellm):**
Set environment variables for your provider (e.g., `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`). litellm handles routing.

## Examples

[`examples/petstore-api`](examples/petstore-api/) includes a FastAPI service, OpenAPI spec, and sample config:

```bash
pip install -r examples/petstore-api/requirements.txt
uvicorn server:app --app-dir examples/petstore-api --port 8765

# In another terminal
qaagent analyze routes --openapi examples/petstore-api/openapi.yaml --out routes.json
qaagent generate unit-tests --routes-file routes.json --out /tmp/tests
qaagent report --fmt html --out reports/findings.html
```

## License

This project is provided as-is for learning and personal use.
