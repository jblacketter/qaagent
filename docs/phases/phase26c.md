# Phase 26c: Aegis — Foundation & Scaffolding

## Summary

Create the Aegis meta-project: a lightweight orchestration layer and portfolio landing page that sits above qaagent and bugalizer. Aegis is "The AI Quality Control Plane" — a unified service registry, workflow engine, and portfolio-grade landing page.

## Context

Phase 26 established the QA Tool Suite architecture. Phase 26b delivered concrete integration (qaagent submits test failures to bugalizer). Phase 26c creates the meta-project at `/Users/jackblacketter/projects/aegis` as a separate repository.

**Branding:** Name "Aegis" (Greek shield of protection). Tagline: "The AI Quality Control Plane". Python package: `aegis-qa` (import as `aegis_qa`). CLI command: `aegis`.

## Scope

### 1. Config System

`.aegis.yaml` with Pydantic models:
- `AegisConfig` — root model
- `AegisIdentity` — name + version metadata
- `LLMConfig` — shared Ollama/LLM settings (supports localhost and LAN)
- `ServiceEntry` — per-tool config (URL, health endpoint, API key env var, features)
- `WorkflowDef` / `WorkflowStepDef` — pipeline definitions
- YAML loader with `${ENV_VAR}` and `${ENV_VAR:-default}` interpolation

### 2. Service Registry + Health Checks

- `ServiceRegistry` class — loads services from config
- `check_health()` — async httpx call to each service's health endpoint
- `check_all_services()` — concurrent health checks via `asyncio.gather`
- `ServiceStatus` / `HealthResult` data models with status labels (healthy/unhealthy/unreachable/unknown)

### 3. Workflow Engine (Sequential)

- `PipelineRunner` — executes named workflows step-by-step
- Step types: `discover`, `test`, `submit_bugs`, `verify` (verify is placeholder)
- Each step calls a downstream service API via httpx
- Conditional steps (`has_failures` — only run if prior steps had failures)
- `BaseStep` ABC with `_get()` and `_post()` helpers, API key from env var
- Returns structured `WorkflowResult` / `StepResult`

### 4. API Layer (FastAPI)

- `GET /health` — Aegis own health
- `GET /api/services` — list services with live health status
- `GET /api/services/{name}/health` — single service health check
- `POST /api/workflows/{name}/run` — trigger a named workflow
- `GET /api/portfolio` — tool metadata for landing page

### 5. CLI (Typer)

- `aegis status` — Rich table of services with health
- `aegis serve` — start API server + serve landing page
- `aegis run <workflow>` — execute a named workflow
- `aegis config show` — print resolved config

### 6. Landing Page (Static HTML/JS)

- Single `index.html` + `styles.css` + `app.js` served as static files
- Hero section: "Aegis" title, tagline, description
- Tool cards: one per service with live status badges
- Architecture diagram: inline SVG showing qaagent ↔ Aegis ↔ bugalizer ↔ LLM
- Fetches `/api/portfolio` and `/api/services` for live data
- Dark theme, no build step required

## Deliverables

### Files Created (35 total)

**Project root (4):** `pyproject.toml`, `README.md`, `CLAUDE.md`, `.aegis.yaml.example`

**Python package (22):**
- `src/aegis_qa/__init__.py` — version
- `src/aegis_qa/config/__init__.py`, `models.py`, `loader.py`
- `src/aegis_qa/registry/__init__.py`, `models.py`, `health.py`, `registry.py`
- `src/aegis_qa/workflows/__init__.py`, `models.py`, `pipeline.py`
- `src/aegis_qa/workflows/steps/__init__.py`, `base.py`, `discover.py`, `test.py`, `submit_bugs.py`, `verify.py`
- `src/aegis_qa/api/__init__.py`, `app.py`, `routes/__init__.py`, `routes/health.py`, `routes/workflows.py`, `routes/portfolio.py`
- `src/aegis_qa/cli.py`

**Landing page (3):** `landing/index.html`, `landing/styles.css`, `landing/app.js`

**Tests (6):** `tests/__init__.py`, `tests/conftest.py`, `tests/test_config.py`, `tests/test_registry.py`, `tests/test_workflows.py`, `tests/test_api.py`

### Dependencies

Core: `fastapi>=0.110`, `uvicorn[standard]>=0.27`, `pydantic>=2.0`, `pydantic-settings>=2.0`, `httpx>=0.27`, `typer>=0.12`, `rich>=13.7`, `PyYAML>=6.0`

Dev: `pytest>=8.0`, `pytest-asyncio>=0.23`

## Success Criteria

| # | Criteria | Status | Evidence |
|---|---------|--------|----------|
| 1 | `pip install -e ".[dev]"` installs cleanly | PASS | All deps resolve, editable install succeeds |
| 2 | `aegis --help` shows all commands | PASS | status, serve, run, config show all registered |
| 3 | `.aegis.yaml` loads with Pydantic validation; `${ENV_VAR}` interpolation works | PASS | `aegis config show` displays resolved config |
| 4 | `aegis status` shows services with health | PASS | Rich table shows services as "unreachable" when not running |
| 5 | `aegis run full_pipeline` executes with conditional logic | PASS | Pipeline runner with has_failures skipping verified in tests |
| 6 | `aegis serve` starts FastAPI; endpoints respond | PASS | /health, /api/services, /api/portfolio all functional |
| 7 | Landing page renders with tool cards and architecture | PASS | Static HTML with live data fetch from API |
| 8 | 68 tests pass; all HTTP calls mocked | PASS | 68 passed in 0.71s, 0 warnings |

## Not in Scope

- No shared LLM client library
- No auth on Aegis API (localhost-only)
- No persistent storage (stateless)
- No changes to qaagent or bugalizer code
- No Docker/deployment config
- No MCP server for Aegis
- No workflow parallelism or DAGs
- No full React app (plain HTML/JS; React upgrade is future phase)
