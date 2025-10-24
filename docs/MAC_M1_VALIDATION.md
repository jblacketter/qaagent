# Mac M1/M2/M3 Validation Checklist

Use this checklist to verify QA Agent works end to end on Apple Silicon before releasing new features.

## Environment
- [ ] Apple Silicon Mac (M1/M2/M3)
- [ ] macOS Sonoma 14.5+ (record actual version: ____________)
- [ ] Python 3.11 or 3.12 installed via Homebrew

## Installation
- [ ] Clone repository fresh
- [ ] Create venv: `python3.11 -m venv .venv`
- [ ] Activate venv
- [ ] Install base package: `pip install -e .`
- [ ] Install extras: `pip install -e .[mcp,api,ui,report,llm]`
- [ ] Install example requirements: `pip install -r examples/petstore-api/requirements.txt`

## Health Check
- [ ] `qaagent doctor` exits with code 0 (warnings acceptable if intentional)
- [ ] Missing dependencies (if any) documented with fixes

## Examples
- [ ] Start FastAPI server: `uvicorn server:app --app-dir examples/petstore-api --port 8765`
- [ ] Run analysis: `qaagent analyze examples/petstore-api`
- [ ] Run Schemathesis: `qaagent schemathesis-run --openapi examples/petstore-api/openapi.yaml --base-url http://localhost:8765`
- [ ] Generate report: `qaagent report --sources reports/schemathesis/junit.xml`
- [ ] Review findings Markdown output

## CLI Commands
- [ ] `qaagent --help` shows commands
- [ ] `qaagent analyze .` works in repo root
- [ ] `qaagent schemathesis-run` succeeds against petstore server
- [ ] `qaagent doctor` reports statuses
- [ ] `qaagent playwright-install` installs browsers (if UI extras installed)
- [ ] `qaagent report` generates Markdown/HTML output

## MCP Server
- [ ] `qaagent-mcp` starts without stack traces
- [ ] MCP handshake verified via `docs/PHASE_1_IMPLEMENTATION_PLAN.md` Flow (initialize + tools/list)
- [ ] Process stops cleanly with Ctrl+C

## Integration Tests
- [ ] `pytest tests/unit -v` passes
- [ ] `pytest tests/integration -v` passes (skipping optional tests is acceptable if extras missing)

## Playwright Specific
- [ ] `npx playwright install --with-deps` completes
- [ ] Chromium launches
- [ ] Firefox launches
- [ ] WebKit launches (document if Developer Tools entitlement needed)
- [ ] Video recording works (requires `brew install ffmpeg`)

## Ollama (Optional)
- [ ] `brew install ollama` (if not installed)
- [ ] `ollama serve` running
- [ ] `ollama pull llama3.2:3b` completes
- [ ] `qaagent gen-tests --kind api --openapi examples/petstore-api/openapi.yaml` returns generated tests

## Issues Found
- [ ] Document any warnings or manual steps here:
  - Issue: ____________________________
  - Workaround: _______________________

## Sign-off
- [ ] Validation complete
- [ ] Reviewer name: __________________
- [ ] Date: ___________________________
