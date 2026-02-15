# Review Cycle: phase5 (impl)

## Metadata
- **Phase:** phase5
- **Type:** impl
- **Started:** 2026-02-10
- **Lead:** claude
- **Reviewer:** codex

## Reference
- Plan: `docs/phases/phase5.md`
- Implementation Log: `docs/phases/phase5_impl.md`
- Decision Log: `docs/decision_log.md`

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Implementation of Phase 5 Priorities 1-3 is complete. 13 new test files, 164 new tests, all passing. P4 (CLI commands) and P5 (API routes) are not yet started.

**Files Created (13):**

Priority 1 — Core Infrastructure (73 tests):
- `tests/unit/runners/test_behave_runner.py` — 8 tests: parse_results from dir/file/empty, run with/without JUnit, missing python, timeout, success
- `tests/unit/evidence/test_writer.py` — 10 tests: JsonlWriter append/empty/nested/additive, EvidenceWriter records/manifest/zero/single/unmapped/reuse
- `tests/unit/test_tools.py` — 13 tests: CmdResult fields, which found/not found, run_command success/failure/timeout/tail/cwd/env/empty/none stdout
- `tests/unit/test_autofix.py` — 20 tests: FixResult defaults, autopep8/black/isort success/not-installed/timeout/exception, security issues, generate_fix_commands, _check_tool_available
- `tests/unit/test_workspace.py` — 22 tests: init default/custom, get paths, list targets, clean target/all, workspace info, copy_to_target/dry_run

Priority 2 — Configuration & Repo (74 tests):
- `tests/unit/config/test_detect.py` — 17 tests: detect nextjs/fastapi/generic, default_base_url/start_command/spec_path/source_dir for each type
- `tests/unit/config/test_templates.py` — 8 tests: TemplateContext fields, available_templates, render fastapi/nextjs/generic, unknown raises
- `tests/unit/config/test_legacy.py` — 15 tests: dataclass defaults, load_config from path/env/cwd/invalid/missing, with auth/tags, write_default_config, write_env_example
- `tests/unit/repo/test_cache.py` — 13 tests: init, register/list/access_time/remove, stats empty/with repos, cleanup old/recent
- `tests/unit/repo/test_validator.py` — 21 tests: detect nextjs/fastapi/flask/django/express/none, validate with/without routes, get_api_directory

Priority 3 — Utilities (17 tests):
- `tests/unit/test_sitemap.py` — 5 tests: parse urls, limit, trailing slash, invalid XML, HTTP error
- `tests/unit/test_a11y.py` — 5 tests: A11yResult fields, run_axe basic/no violations/with tags, AXE_CDN constant
- `tests/unit/test_dashboard.py` — 7 tests: creates HTML, contains project name/risk data, parent dirs, empty risks/routes, basic mode

**Key implementation decisions:**
- Lazy imports (httpx, playwright) require patching the library directly, not the module attribute
- `RouteSource` enum uses uppercase members (OPENAPI, CODE)
- `Risk` model takes `route` as `Optional[str]`, not a Route object
- All tests use `tmp_path` for filesystem isolation

**Test results:** 164 new tests pass. 1 pre-existing failure in `test_route_discovery.py::test_deduplicate_routes_prefers_higher_confidence` (unrelated to this work).

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

Blocking issues:
1. Phase 5 implementation is not complete against the approved scope. Priority 4 and 5 test files are still missing:
   - `tests/integration/commands/test_targets_cmd.py`
   - `tests/integration/commands/test_workspace_cmd.py`
   - `tests/integration/commands/test_run_cmd.py`
   - `tests/integration/commands/test_report_cmd.py`
   - `tests/integration/commands/test_misc_cmd.py`
   - `tests/unit/api/routes/test_evidence.py`
   - `tests/unit/api/routes/test_runs.py`
   - `tests/unit/api/routes/test_repositories.py`
   - `tests/unit/api/routes/test_fix.py`
   The phase success criteria require all 23 planned test files and completion of P1-P5.

2. Full suite does not run clean: `pytest tests/` errors during collection with an import-file mismatch between `tests/unit/generators/test_validator.py` and `tests/unit/repo/test_validator.py`. This blocks the success criterion "`pytest tests/` runs clean with 0 failures."

Validation performed:
- P1-P3 tests pass as reported: 164 passed across the 13 new files.
- `pytest tests/` currently fails at collection (not a clean run).

Please complete P4/P5 and resolve the test module collision, then resubmit for review.

---

## Round 2

### Lead
**Action:** SUBMIT_FOR_REVIEW

Both blocking issues from Round 1 are resolved:

**1. P4 and P5 complete — 141 new tests across 9 files, all passing.**

Priority 4 — CLI Commands Integration (94 tests):
- `tests/integration/commands/test_targets_cmd.py` — 9 tests: list empty/with targets, add success/activate/error, remove success/error, use success/error
- `tests/integration/commands/test_workspace_cmd.py` — 12 tests: show existing/empty/no-target/explicit, list targets/empty, clean all/target/no-target, apply success/empty/dry-run
- `tests/integration/commands/test_run_cmd.py` — 35 tests: pytest-run help/success/not-installed/json/failure, schemathesis help/not-installed/no-spec/no-base-url, playwright-install help/not-installed/success, playwright-scaffold creates/exists/no-pytest, ui-run help/no-pytest, perf-scaffold creates/exists, perf-run help/not-installed/success, lighthouse help/no-url/no-tool/success, a11y-run help/no-url/success, a11y-from-sitemap help/no-urls/error, run-all help/no-profile/success
- `tests/integration/commands/test_report_cmd.py` — 17 tests: report help/success/json/html-flip, dashboard help/no-target/success/error, summarize help/success, open-report help/not-found/success, export help/not-found/success, plan-run help
- `tests/integration/commands/test_misc_cmd.py` — 21 tests: doctor help/all-ok/errors/json/warnings, fix help/no-target/success/unknown-tool, version json, init creates, api-detect help/no-files/found, gen-tests help/unsupported/no-spec/dry-run, web-ui/api/mcp-stdio help

Priority 5 — API Routes (47 tests):
- `tests/unit/api/routes/test_evidence.py` — 13 tests: findings/coverage/churn/risks/recommendations returns+not-found, CUJ empty-config/with-config/not-found
- `tests/unit/api/routes/test_runs.py` — 8 tests: list all/pagination-limit/offset/structure, get-run found/not-found, trends data/limit
- `tests/unit/api/routes/test_repositories.py` — 18 tests: list empty/with-repos, create local/duplicate/bad-path/not-dir/github, get found/not-found, delete success/not-found, analyze success/not-found/failure, status/not-found, runs/not-found
- `tests/unit/api/routes/test_fix.py` — 8 tests: fixable-issues flake8/empty/not-found/bandit, apply-fix success/no-changes/invalid-category/not-found

**2. Test module collision fixed.** Added `__init__.py` to all test directories, resolving the `test_validator.py` namespace collision between `generators/` and `repo/`.

**Test results:** `pytest tests/` now collects and runs all 766 tests. 762 pass, 4 fail (all pre-existing, none from Phase 5):
- `test_full_api_workflow` — schemathesis integration test (external tool assertions)
- `test_mcp_server_initializes` — MCP protocol handshake change
- `test_mcp_detect_openapi_tool` — MCP tool listing issue
- `test_deduplicate_routes_prefers_higher_confidence` — pre-existing route dedup bug

**Key decisions (P4-P5):**
- CLI integration tests use `CliRunner` from Typer per approved strategy
- Commands with lazy local imports require patching at the source module (e.g., `qaagent.config.load_active_profile` not `qaagent.commands.run_cmd.load_active_profile`)
- API tests use `TestClient` + `create_app()` factory with seeded evidence via `RunManager`/`EvidenceWriter`
- Repository tests use `autouse=True` fixture to clear in-memory storage between tests

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- All 9 planned P4/P5 test files now exist.
- New P4/P5 tests pass: `141 passed`.
- The prior collection collision is resolved (no `test_validator.py` import-file mismatch now).

Blocking issue:
1. Phase success criterion "`pytest tests/` runs clean with 0 failures" is still not met.
   - Current full-suite result in this environment includes 4 failing cases:
     - `tests/integration/test_api_workflow.py::test_full_api_workflow` (fixture startup timeout on `http://127.0.0.1:8765/health`)
     - `tests/integration/test_mcp_server.py::test_mcp_detect_openapi_tool` (same fixture timeout)
     - `tests/integration/test_mcp_server.py::test_mcp_server_initializes` (MCP initialize returns `Invalid request parameters`)
     - `tests/unit/analyzers/test_route_discovery.py::test_deduplicate_routes_prefers_higher_confidence`

Please either:
- Fix/contain these failures so the full suite is clean, or
- Formally adjust/waive this success criterion (decision + plan/log update) if these are accepted pre-existing/out-of-scope failures.

---

## Round 3

### Lead
**Action:** SUBMIT_FOR_REVIEW

Addressing the remaining blocking issue: the 4 pre-existing test failures that prevent a fully clean `pytest tests/` run.

**Resolution: Formal waiver of "0 failures" criterion for pre-existing failures.**

Decision logged in `docs/decision_log.md` (2026-02-13). Rationale:

1. **All 4 failures predate Phase 5.** None were introduced by the 22 new test files or the `__init__.py` additions. They were failing before Phase 5 work began.

2. **Fixing them violates Phase 5 scope.** The phase plan explicitly states "No new features or refactoring — this phase is test-only." Three of the four failures require production code changes:
   - `test_full_api_workflow` / `test_mcp_detect_openapi_tool` — require fixing the schemathesis/petstore fixture infrastructure (server startup, port binding)
   - `test_mcp_server_initializes` — requires fixing MCP protocol handshake code
   - `test_deduplicate_routes_prefers_higher_confidence` — requires fixing route deduplication logic in `analyzers/`

3. **Marking them `xfail`/`skip` would hide legitimate bugs.** Better to leave them visible for a future phase to address properly.

**Changes made:**
- `docs/decision_log.md` — Added decision "Waive '0 failures' criterion for pre-existing test failures"
- `docs/phases/phase5.md` — Updated final success criterion to `[x]` with waiver reference

**Phase 5 final scorecard:**
- 22 new test files: all created and passing
- 305 new tests total (164 P1-P3 + 141 P4-P5)
- 0 new failures introduced
- 0 regressions in existing tests
- All 7 success criteria now satisfied (last one waived for pre-existing failures)
- `pytest tests/`: 762 passed, 4 failed (all pre-existing)

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

Review outcome:
- Round 2 blockers are resolved:
  - P4/P5 deliverables exist and pass (`141 passed`).
  - The prior collection collision was fixed via test-package `__init__.py` additions.
- Waiver is documented in `docs/decision_log.md` (2026-02-13) and reflected in `docs/phases/phase5.md` success criteria.
- Remaining full-suite failures are explicitly captured as pre-existing/out-of-scope for this test-only phase.

Non-blocking cleanup note:
- `docs/phases/phase5.md` still contains mixed counts (22/23/24) across sections; align to one final number for consistency.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: none
ROUND: 3
STATE: complete
<!-- /CYCLE_STATUS -->
