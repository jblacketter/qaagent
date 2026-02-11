# Review Cycle: phase5 (plan)

## Metadata
- **Phase:** phase5
- **Type:** plan
- **Started:** 2026-02-10
- **Lead:** claude
- **Reviewer:** codex

## Reference
- Plan: `docs/phases/phase5.md`
- Decision Log: `docs/decision_log.md`
- Roadmap: `docs/ROADMAP.md`

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Phase 5 plan covers hardening and test coverage for 24 untested source modules, organized into 5 priority tiers:

- **P1 (Core Infrastructure):** behave_runner, evidence/writer, tools, autofix, workspace — highest impact, these are used throughout the codebase.
- **P2 (Config & Repo):** config/detect, config/templates, config/legacy, repo/cache, repo/validator — medium impact, configuration and repository utilities.
- **P3 (Utilities):** sitemap, a11y, dashboard — lower risk, smaller modules.
- **P4 (CLI Commands):** 6 command modules — integration tests using CliRunner.
- **P5 (API Routes):** 4 FastAPI route modules — TestClient-based tests.

Key decisions already made by human arbiter:
1. No enforced coverage thresholds — focus on meaningful happy-path + error-case tests.
2. CLI commands use CliRunner integration tests (not mocked unit tests).
3. Phase can be split at P4-P5 boundary if scope grows too large.

Technical approach follows existing test conventions (subprocess mocking, tmp_path for file I/O, patch.dict for module-level maps). 24 new test files to create, 0 existing files modified (except possibly conftest.py for shared fixtures).

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

Blocking issue:
1. `docs/phases/phase5.md` states all CLI command modules should use CliRunner integration tests (`docs/phases/phase5.md:71`), and the decision log requires CLI command tests under `tests/integration/commands/` (`docs/decision_log.md:32`, `docs/decision_log.md:47`). However, `targets_cmd` and `workspace_cmd` are currently planned as unit tests (`docs/phases/phase5.md:104`, `docs/phases/phase5.md:105`). Please move those command module tests to integration paths to match the approved testing strategy.

Non-blocking suggestions:
- Clarify whether `commands/_helpers.py` remains unit-tested or is covered indirectly via command integration tests.
- Update phase status to "In Review" in `docs/phases/phase5.md` for status consistency.

---

## Round 2

### Lead
**Action:** SUBMIT_FOR_REVIEW

All three items addressed:

1. **Blocking fix:** Moved `targets_cmd` and `workspace_cmd` test files from `tests/unit/commands/` to `tests/integration/commands/` to match the approved CliRunner strategy. All 5 command module tests are now under `tests/integration/commands/`.

2. **`_helpers.py` clarification:** Removed its dedicated test file from the plan. `_helpers.py` contains shared utilities (profile loading, output formatting) that are exercised through every command integration test. Added a note in the scope section: "Covered indirectly by command integration tests; no dedicated test file." Total new test files adjusted from 24 to 23.

3. **Phase status:** Updated `docs/phases/phase5.md` status to "In Review."

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

The plan now matches the Phase 5 decisions and review requirements:
- CLI command tests are planned as integration tests under `tests/integration/commands/`.
- `_helpers.py` is explicitly documented as indirect coverage via command integration tests.
- Phase status is updated to In Review.

Non-blocking note:
- `docs/phases/phase5.md` still references "24 new test files" in one risk line; it should say 23 for consistency.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: reviewer
ROUND: 2
STATE: approved
<!-- /CYCLE_STATUS -->
