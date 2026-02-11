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
_awaiting response_

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: reviewer
ROUND: 1
STATE: in-progress
<!-- /CYCLE_STATUS -->
