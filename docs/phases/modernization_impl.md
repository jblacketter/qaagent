# Implementation Log: Codebase Modernization

**Started:** 2026-02-07
**Lead:** claude
**Plan:** docs/phases/modernization.md

## Progress

### Milestone 1A: CLI Split ✓

- [x] Capture pre-split help tree snapshot for parity tests
- [x] Create `src/qaagent/commands/_helpers.py` with shared utilities
- [x] Move analyze commands to `commands/analyze_cmd.py`
- [x] Create `commands/config_cmd.py` from cli.py config commands
- [x] Create `commands/targets_cmd.py` from cli.py targets commands
- [x] Create `commands/generate_cmd.py` from cli.py generate commands
- [x] Create `commands/workspace_cmd.py` from cli.py workspace commands
- [x] Create `commands/run_cmd.py` from cli.py test runner commands
- [x] Create `commands/report_cmd.py` from cli.py report commands
- [x] Create `commands/misc_cmd.py` from cli.py misc commands
- [x] Rewrite `commands/__init__.py` as app assembly
- [x] Rewrite `cli.py` as thin entry point (14 lines)
- [x] Create `tests/integration/test_cli_split_parity.py` (20 tests, all pass)
- [x] Verify all existing tests pass (6 pre-existing failures unrelated to split)

### Milestone 1B: Config Migration ✓

- [x] Add `load_config_compat()` with deprecation warning
- [x] Replace 4 legacy callsites with compat function
- [x] Add `qaagent config migrate` command
- [ ] Delete `config/legacy.py` (deferred to end of phase per plan — migration utility must ship first)

### Milestone 1C: LLM + Pydantic ✓

- [x] Convert `Route`, `Risk`, `StrategySummary` to Pydantic BaseModel
- [x] Refactor `llm.py` to `LLMClient` with litellm
- [x] Add typed models (`ChatMessage`, `ChatResponse`, `QAAgentLLMError`)
- [x] Add `tests/unit/test_llm_client.py` (14 tests, all pass)
- [x] Fix pre-existing test failures (risk.score() → risk.score property, LLM fallback)

## Test Results

**Before modernization:** 6 failures (pre-existing)
**After modernization:** 4 failures (pre-existing, unrelated to our changes)
- Fixed: `test_risk_to_dict_contains_score_and_references` (score is now computed property)
- Fixed: `test_generate_api_tests_fallback_works_without_llm` (no longer hits Ollama directly)
- Remaining 4: MCP server integration issues (2), API workflow test (1), route dedup test (1)

## Files Created
- `src/qaagent/commands/_helpers.py` (235 lines) — shared CLI utilities
- `src/qaagent/commands/analyze_cmd.py` (248 lines) — analyze subcommands
- `src/qaagent/commands/config_cmd.py` (145 lines) — config subcommands + migrate
- `src/qaagent/commands/targets_cmd.py` (81 lines) — targets subcommands + `use`
- `src/qaagent/commands/generate_cmd.py` (310 lines) — generate subcommands
- `src/qaagent/commands/workspace_cmd.py` (166 lines) — workspace subcommands
- `src/qaagent/commands/run_cmd.py` (507 lines) — test runner commands
- `src/qaagent/commands/report_cmd.py` (195 lines) — report/dashboard commands
- `src/qaagent/commands/misc_cmd.py` (315 lines) — doctor, version, web-ui, etc.
- `tests/fixtures/cli_snapshots/pre_split_commands.json` — command tree snapshot
- `tests/integration/test_cli_split_parity.py` — 20 parity + smoke tests
- `tests/unit/test_llm_client.py` — 14 LLM client tests

## Files Modified
- `src/qaagent/commands/__init__.py` — rewritten as app assembly (52 lines)
- `src/qaagent/cli.py` — rewritten as thin entry point (14 lines, down from 2048)
- `src/qaagent/config/__init__.py` — added `load_config_compat()` and `_profile_to_legacy()`
- `src/qaagent/mcp_server.py` — migrated to `load_config_compat()`
- `src/qaagent/analyzers/models.py` — converted Route, Risk, StrategySummary to Pydantic
- `src/qaagent/llm.py` — refactored to LLMClient with litellm, added typed models
- `tests/unit/analyzers/test_models.py` — fixed score assertion for computed property

## Decisions Made
- Named analyze CLI module `analyze_cmd.py` (not `analyze.py`) to avoid conflict with existing `analyze.py` helper module
- Used `register(app)` pattern for modules with top-level commands (run_cmd, report_cmd, misc_cmd) to avoid circular imports
- Subgroup modules (analyze_cmd, config_cmd, targets_cmd, generate_cmd, workspace_cmd) export their own Typer subapps
- Kept `analyze.py` unchanged for backward-compat (`from qaagent.commands import run_collectors` still works)
- Dropped underscore prefix on _helpers.py functions since they're now shared module-level APIs
- Risk.score is a `@computed_field` property (not a method) — access as `risk.score` not `risk.score()`
- LLMClient backward compat: module-level `chat()` function wraps LLMClient and returns old dict format
- Deferred `config/legacy.py` deletion per plan — migration utility needs to be available first

### Codex Review Fixes (Round 1)

Three HIGH issues identified by codex reviewer, all resolved:

1. **[FIXED] `qaagent analyze .` broken** — Dual registration (`app.command("analyze")` + `app.add_typer(analyze_app)`) caused Typer to treat `.` as a subcommand name. Fix: custom `_AnalyzeGroup(TyperGroup)` that overrides `resolve_command()` to fall back to `repo` subcommand for unrecognized tokens. Removed conflicting `app.command("analyze")` from `__init__.py`.

2. **[FIXED] `load_config_compat()` priority order** — Was trying global active-target first, which could override local project config. Fix: reordered to local `.qaagent.yaml` in cwd → global active target → legacy TOML.

3. **[FIXED] `config migrate` lossy for API settings** — Migration dropped auth/timeout/tags/operations/endpoint_pattern. Fix: added `AuthSettings` model, extended `EnvironmentSettings` with `auth`/`timeout`, extended `OpenAPISettings` with `tags`/`operations`/`endpoint_pattern`. Updated both `_profile_to_legacy()` and `config_migrate` to carry all fields.

**Files modified in this round:**
- `src/qaagent/commands/analyze_cmd.py` — added `_AnalyzeGroup` custom Click group, callback pattern
- `src/qaagent/commands/__init__.py` — removed broken `app.command("analyze")` dual registration
- `src/qaagent/config/__init__.py` — reordered `load_config_compat()` stages, enhanced `_profile_to_legacy()`
- `src/qaagent/config/models.py` — added `AuthSettings`, extended `EnvironmentSettings` and `OpenAPISettings`
- `src/qaagent/commands/config_cmd.py` — enhanced `config_migrate` to carry all API settings

## Issues Encountered
- Codex review caught 3 HIGH issues in the initial implementation — all resolved in review round 1
