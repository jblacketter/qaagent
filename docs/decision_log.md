# Decision Log

This log tracks important decisions made during the project.

<!-- Add new decisions at the top in reverse chronological order -->

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
