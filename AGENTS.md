# Repository Guidelines

## Project Structure & Module Organization
The Python package lives in `src/qaagent` with feature modules (`analyzers/`, `collectors/`, `generators/`, `config/`, CLI entry points in `cli.py`, `commands/`, `mcp_server.py`). Templates stay in `src/qaagent/templates`; generated artifacts land in `reports/`; docs and handoffs live in `docs/` and `handoff/`. Tests sit in `tests/` split into `unit/`, `integration/`, and shared fixtures. Example OpenAPI specs and workloads live in `examples/` for reuse during validation.

## Build, Test, and Development Commands
- `pip install -e .[dev]` prepares an editable environment with pytest extras; add `[ui]` or `[api]` when touching Playwright or Schemathesis flows.
- `qaagent analyze .` seeds heuristics for a target repo; run `qaagent doctor` to confirm local tooling before review.
- `pytest -q` covers the full suite; narrow with `pytest tests/unit` while iterating.
- `qaagent pytest-run --path tests --cov --cov-target src` is the preferred coverage command, emitting XML and HTML under `reports/pytest/`.
- `scripts/validate_week2.sh` powers the CI smoke; keep it clean and commit any fixture updates alongside code.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indents, snake_case modules, and explicit type hints (matching existing Typer commands and Pydantic models). Keep CLI surfacing in `commands/` and route user-facing text through `rich` utilities. Reuse helpers from `tools.py` instead of duplicating subprocess or filesystem code.

## Testing Guidelines
Name new tests `test_<feature>.py` and lean on pytest fixtures in `tests/fixtures` or `conftest.py`. Integration cases should exercise CLI commands end-to-end; unit cases isolate Pydantic models, collectors, or generators with fakes. Use `qaagent pytest-run --cov` to confirm coverage and inspect the HTML report in `reports/pytest/html`. Ship representative inputs in `examples/` whenever new analyzers or generators require sample data.

## Commit & Pull Request Guidelines
Use short, imperative commit subjects (e.g., `Refine risk scoring`) and squash WIP commits locally. Reference issues in the footer (`Refs #123`) and describe behavioural changes plus validation commands in each PR. Attach screenshots or artifact paths for UI, report, or MCP output changes, and request review once the `qaagent.yml` GitHub Action passes.

## Agent & MCP Tips
Scaffold targets with `qaagent config init . --template <name>` and track shared configs under `handoff/`. Run the MCP server via `qaagent-mcp` during local integration, documenting new tools or collectors in PR notes so downstream agents can opt in quickly.
