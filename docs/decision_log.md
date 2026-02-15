# Decision Log

This log tracks important decisions made during the project.

<!-- Add new decisions at the top in reverse chronological order -->

---

## 2026-02-13: Waive "0 failures" criterion for pre-existing test failures

**Decision:** The Phase 5 success criterion "`pytest tests/` runs clean with 0 failures" is satisfied when all Phase 5 tests pass and no new failures are introduced. Pre-existing failures that predate Phase 5 are accepted and do not block phase completion.

**Context:** Phase 5 added 305 new tests across 22 files, all passing. However, 4 tests that were already failing before Phase 5 began continue to fail:
- `test_full_api_workflow` — schemathesis integration test (fixture startup timeout)
- `test_mcp_server_initializes` — MCP protocol handshake returns "Invalid request parameters"
- `test_mcp_detect_openapi_tool` — same fixture startup timeout
- `test_deduplicate_routes_prefers_higher_confidence` — pre-existing route dedup logic bug

**Alternatives Considered:**
- Fix all 4 failures in Phase 5: Would expand scope beyond "test-only, no features or refactoring." Three of the four require fixing production code (MCP protocol handling, schemathesis fixture, route dedup logic), violating the phase's out-of-scope rules.
- Mark tests as `pytest.mark.skip`/`xfail`: Hides the failures and risks forgetting them. Better to leave them visible for future phases to address.
- Waive the criterion for documented pre-existing failures: Keeps failures visible, acknowledges they're out of scope, and allows Phase 5 to close on its actual deliverables.

**Rationale:** Phase 5's scope explicitly states "No new features or refactoring — this phase is test-only." Fixing the 4 pre-existing failures would require production code changes (MCP protocol, route deduplication logic, schemathesis fixture infrastructure), which directly violates the phase scope. All 4 failures predate Phase 5 and are unrelated to the 22 new test files. The appropriate fix venue is a future phase.

**Decided By:** claude (lead), pending reviewer acceptance

**Phase:** Phase 5 (Hardening & Test Coverage)

**Follow-ups:**
- Update Phase 5 success criteria to reflect the waiver.
- Track the 4 pre-existing failures for resolution in a future phase.

---

## 2026-02-10: No enforced test coverage thresholds

**Decision:** Do not set or enforce minimum line-coverage thresholds (e.g., 80%) in CI.

**Context:** Phase 5 adds tests for 24 untested modules. We considered adding a coverage gate to CI.

**Alternatives Considered:**
- Enforce 80% per-module threshold: Provides a hard guarantee but can encourage low-value tests just to hit a number.
- No threshold: Trust test quality over quantity; focus on happy-path + key error cases.

**Rationale:** Coverage numbers can incentivize writing tests for the metric rather than for value. Better to focus on meaningful tests.

**Decided By:** Human

**Phase:** Phase 5 (Hardening & Test Coverage)

**Follow-ups:**
- Success criteria updated to "happy path and key error cases" instead of percentage targets.

---

## 2026-02-10: CLI integration tests over unit tests

**Decision:** Use `typer.testing.CliRunner` integration tests for all CLI command modules rather than mocked unit tests.

**Context:** Phase 5 needs to test 6 command modules. The codebase has both patterns (CliRunner integration tests and mocked unit tests).

**Alternatives Considered:**
- Mocked unit tests: Faster, more isolated, but don't exercise the full Typer dispatch path.
- CliRunner integration tests: Slower but test the real CLI surface, catching registration and argument parsing bugs.

**Rationale:** Integration tests catch more real-world issues and match the existing test style (test_analyze_routes_cli.py, test_config_cli.py).

**Decided By:** Human

**Phase:** Phase 5 (Hardening & Test Coverage)

**Follow-ups:**
- CLI command test files go in `tests/integration/commands/`.

---

## 2026-02-10: Phases can be split as needed

**Decision:** Phase 5 includes all 5 priority tiers (P1-P5), but can be split into separate phases during implementation if scope becomes too large.

**Context:** 24 test files is a large batch. We considered splitting CLI commands (P4) and API routes (P5) into a Phase 5b upfront.

**Alternatives Considered:**
- Split now: Cleaner scope per phase, but adds ceremony before we know it's needed.
- Keep together, split if needed: Start with P1-P3, assess, split P4-P5 out if the phase is running long.

**Rationale:** Avoid premature splitting. We can reassess after P1-P3 are done.

**Decided By:** Human

**Phase:** Phase 5 (Hardening & Test Coverage)

**Follow-ups:**
- Monitor scope during implementation; split if P1-P3 alone fills the phase.
