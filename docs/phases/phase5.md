# Phase: Hardening & Test Coverage

## Status
- [x] Planning
- [x] In Review
- [x] Approved
- [x] Implementation
- [ ] Implementation Review
- [ ] Complete

## Roles
- Lead: claude
- Reviewer: codex
- Arbiter: Human

## Summary
**What:** Fill test coverage gaps across 24 untested source modules (23 new test files; `_helpers.py` covered indirectly), prioritized by risk and impact.
**Why:** Phases 1-4 built substantial functionality but left ~25% of modules without tests. Core infrastructure (evidence writer, behave runner, tools utilities) and command modules are the primary gaps. Hardening now prevents regressions as we build Phases 6-11 on top.
**Depends on:** Phase 4 (Enhanced Analysis) — Complete

## Scope

### In Scope

#### Priority 1: Core Infrastructure (High impact)
- `runners/behave_runner.py` — BehaveRunner (91 lines, 3 methods). Only runner without tests; follow pytest_runner pattern.
- `evidence/writer.py` — EvidenceWriter + JsonlWriter (64 lines). Core evidence pipeline.
- `tools.py` — CmdResult, `run_command()`, `which()`, `ensure_dir()` (49 lines). Used throughout codebase.
- `autofix.py` — AutoFixer + FixResult (281 lines, 7 methods). Orchestrates autopep8/black/isort.
- `workspace.py` — Workspace class (234 lines, 15 methods). File staging and management.

#### Priority 2: Configuration & Repo (Medium impact)
- `config/detect.py` — Project type detection heuristics (60 lines, 4 functions).
- `config/templates.py` — Jinja2 config template rendering (48 lines).
- `config/legacy.py` — Legacy TOML config migration (131 lines).
- `repo/cache.py` — RepoCache with metadata and cleanup (189 lines, 10 methods).
- `repo/validator.py` — RepoValidator with project detection (260 lines, 13 methods).

#### Priority 3: Utilities & UI (Lower risk)
- `sitemap.py` — `fetch_sitemap_urls()` (32 lines).
- `a11y.py` — A11yResult + `run_axe()` (105 lines).
- `dashboard.py` — Dashboard generation from workspace/evidence (152 lines).

#### Priority 4: CLI Commands
- `commands/_helpers.py` — Shared CLI utilities (235 lines, 14 functions). Covered indirectly by command integration tests; no dedicated test file.
- `commands/targets_cmd.py` — Target management (81 lines, 4 functions).
- `commands/workspace_cmd.py` — Workspace commands (166 lines, 4 functions).
- `commands/run_cmd.py` — Test execution commands (559 lines, 12 functions).
- `commands/report_cmd.py` — Report generation (291 lines, 6 functions).
- `commands/misc_cmd.py` — Miscellaneous commands (315 lines, 8 functions).

#### Priority 5: API Routes
- `api/routes/evidence.py` — Evidence endpoints (96 lines, 6 routes).
- `api/routes/runs.py` — Runs endpoints (91 lines, 3 routes).
- `api/routes/repositories.py` — Repository management (205 lines, 7 routes).
- `api/routes/fix.py` — Autofix endpoints (236 lines, 3 routes).

### Out of Scope
- `web_ui.py` — Complex FastAPI + WebSocket server (357 lines). Better suited for E2E testing in a later phase.
- Vendored third-party code (`dashboard/frontend/node_modules/`)
- Increasing coverage of already-tested modules
- New features or refactoring — this phase is test-only
- Performance benchmarking or load testing of qaagent itself

## Technical Approach

**Pattern:** Follow existing test conventions established in Phases 1-4.

1. **Unit tests** for pure logic modules — use `pytest` with `tmp_path`, mock subprocess calls via `unittest.mock.patch`. Mirror the directory structure: `tests/unit/<package>/test_<module>.py`.

2. **Integration tests** for CLI commands — use `typer.testing.CliRunner` with `invoke()`. Follow the pattern in `test_analyze_routes_cli.py` and `test_config_cli.py`. Prefer integration tests over mocked unit tests for all command modules.

3. **API route tests** — use `fastapi.testclient.TestClient` with mocked dependencies. Follow the pattern in `test_api_app.py`.

4. **Subprocess-heavy modules** (tools, autofix, runners) — mock `subprocess.run` / `run_command()` and verify arguments + return handling. Use `patch.dict()` for module-level maps per lessons learned.

5. **File I/O modules** (workspace, evidence/writer, repo/cache) — use `tmp_path` fixture for isolated filesystem operations.

6. **Test naming:** `test_<function_name>_<scenario>` (e.g., `test_run_command_timeout`, `test_run_command_success`).

## Files to Create

### Priority 1
- `tests/unit/runners/test_behave_runner.py` — BehaveRunner tests
- `tests/unit/evidence/test_writer.py` — EvidenceWriter + JsonlWriter tests
- `tests/unit/test_tools.py` — CmdResult, run_command, which, ensure_dir tests
- `tests/unit/test_autofix.py` — AutoFixer tests
- `tests/unit/test_workspace.py` — Workspace class tests

### Priority 2
- `tests/unit/config/test_detect.py` — Project type detection tests
- `tests/unit/config/test_templates.py` — Config template rendering tests
- `tests/unit/config/test_legacy.py` — Legacy config migration tests
- `tests/unit/repo/test_cache.py` — RepoCache tests
- `tests/unit/repo/test_validator.py` — RepoValidator tests

### Priority 3
- `tests/unit/test_sitemap.py` — Sitemap fetching tests
- `tests/unit/test_a11y.py` — Accessibility testing tests
- `tests/unit/test_dashboard.py` — Dashboard generation tests

### Priority 4
- `tests/integration/commands/test_targets_cmd.py` — Targets command integration tests
- `tests/integration/commands/test_workspace_cmd.py` — Workspace command integration tests
- `tests/integration/commands/test_run_cmd.py` — Run command integration tests
- `tests/integration/commands/test_report_cmd.py` — Report command integration tests
- `tests/integration/commands/test_misc_cmd.py` — Misc command integration tests

### Priority 5
- `tests/unit/api/routes/test_evidence.py` — Evidence API tests
- `tests/unit/api/routes/test_runs.py` — Runs API tests
- `tests/unit/api/routes/test_repositories.py` — Repositories API tests
- `tests/unit/api/routes/test_fix.py` — Fix API tests

### May Modify
- `tests/conftest.py` — Add shared fixtures if needed (e.g., mock workspace, mock evidence store)
- `tests/integration/test_cli_split_parity.py` — Update snapshot if test directories change

## Success Criteria
- [ ] All 23 new test files created and passing
- [ ] Priority 1 modules (behave_runner, evidence/writer, tools, autofix, workspace) have tests covering happy path and key error cases
- [ ] Priority 2 modules (config/detect, config/templates, config/legacy, repo/cache, repo/validator) have tests covering happy path and key error cases
- [ ] Priority 3 modules (sitemap, a11y, dashboard) have tests for all public functions
- [ ] Priority 4 command modules have tests for happy path + at least one error case per command
- [ ] Priority 5 API routes have tests for all endpoints using TestClient
- [ ] All existing tests continue to pass (no regressions)
- [ ] `pytest tests/` runs clean with 0 failures

## Open Questions
- None — resolved during planning (see `docs/decision_log.md`)

## Risks
- **Subprocess mocking complexity**: Modules like `autofix.py` and `run_cmd.py` shell out extensively. Mitigation: Follow established `patch("subprocess.run")` patterns from pytest_runner tests.
- **Flaky tests from file I/O**: Workspace and evidence writer tests touch the filesystem. Mitigation: Use `tmp_path` exclusively, never touch real directories.
- **Test maintenance burden**: 23 new test files is a large batch. Mitigation: Prioritize P1-P2 first, validate the approach, then proceed to P3-P5.
- **Scope creep**: Temptation to fix bugs found while writing tests. Mitigation: Log bugs as issues, don't fix in this phase unless they block test writing.
