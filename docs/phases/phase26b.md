# Phase 26b: Bugalizer Integration

## Summary

Add concrete integration between QA Agent and Bugalizer: a config section for bugalizer connection settings, an HTTP client module for submitting bug reports, and a `--submit-bugs` flag on `run-all` that auto-submits failed test cases as structured bug reports to Bugalizer's API.

## Context

Phase 26 established the architecture plan for the QA Tool Suite. This phase implements the first concrete integration: QA Agent → Bugalizer issue submission. When tests fail, QA Agent's diagnostics engine already produces structured failure analysis (root cause, category, suggestion, confidence). This phase wires that data into Bugalizer's `/api/v1/reports` endpoint.

## Scope

### 1. Config Model: `BugalizerSettings`

Add to `src/qaagent/config/models.py`:

```python
class BugalizerSettings(BaseModel):
    enabled: bool = False
    api_url: str = "http://localhost:8001"
    api_key_env: str = "BUGALIZER_API_KEY"     # Environment variable name
    project_id: Optional[str] = None            # Bugalizer project to submit to
    submit_on_failure: bool = True              # Auto-submit when --submit-bugs is used
    reporter: str = "qaagent"                   # Reporter name in bug reports
    labels: List[str] = Field(default_factory=lambda: ["qaagent"])
```

Add `bugalizer: Optional[BugalizerSettings] = None` to `QAAgentProfile`.

Add corresponding section to config templates.

### 2. Bugalizer Client Module

New file: `src/qaagent/integrations/bugalizer_client.py`

- `BugalizerClient` class wrapping `httpx.Client`
- `submit_bug(title, description, project_id, ...)` → posts to `/api/v1/reports`
- `test_case_to_report(case: TestCase, diagnostic: DiagnosticResult, suite: TestResult)` → builds the payload
- Severity mapping: diagnostic category → bugalizer severity (auth→critical, assertion/connection→high, timeout/data→medium, flaky→low)
- Error handling: log failures, don't crash the run

### 3. CLI Integration

Modify `src/qaagent/commands/run_cmd.py`:

- Add `--submit-bugs` flag to `run_all()`
- After orchestrator returns results with failures, call `submit_failures_to_bugalizer()`
- Print submitted bug IDs in the summary
- Config-driven: `profile.bugalizer.enabled` must be `True` and `--submit-bugs` flag must be passed (both required)

### 4. Diagnostic Persistence to Evidence

Currently, the orchestrator only persists `diagnostic_summary.summary_text` (a string) to evidence via `handle.add_diagnostic()`. Per-test diagnostic records (`DiagnosticResult` with category, root_cause, confidence, suggestion) are lost after the run.

**Change:** After running diagnostics, persist the full per-test diagnostic records to `diagnostics.json` in the evidence directory:

```python
# In orchestrator.run_all(), after diagnostics:
diagnostics_data = [
    {
        "test_name": case.name,
        "suite": suite_name,
        "category": diag.category,
        "root_cause": diag.root_cause,
        "confidence": diag.confidence,
        "suggestion": diag.suggestion,
        "error_message": case.error_message,
        "route": case.route,
    }
    for suite_name, suite_result in result.suites.items()
    for case, diag in zip(failed_cases, diagnostics)
]
# Write to evidence_dir/diagnostics.json
```

This enables the manual `submit-bug <run-id>` command to read structured diagnostics from any previous run.

**Files modified:** `src/qaagent/runners/orchestrator.py` (write diagnostics.json), `src/qaagent/evidence/models.py` (register file type)

### 5. Standalone CLI Command

Add `qaagent submit-bug` to `src/qaagent/commands/misc_cmd.py` (or new file):

- Manual bug submission from a previous run's diagnostics
- `qaagent submit-bug <run-id>` — reads `diagnostics.json` from run evidence and submits
- Falls back to recomputing diagnostics from JUnit artifacts if `diagnostics.json` is missing (for runs before this phase)
- Useful for submitting bugs from runs that didn't use `--submit-bugs`

### 6. Tests

New test file: `tests/test_bugalizer_integration.py`

- Config model validation (BugalizerSettings defaults, serialization)
- Payload mapping (TestCase + DiagnosticResult → BugReportCreate-compatible dict)
- Client submission with mocked httpx (success, API error, connection error)
- CLI flag integration (--submit-bugs triggers submission)
- Diagnostic persistence (diagnostics.json written to evidence, read back for submit-bug)
- No dependency on running Bugalizer instance — all HTTP calls mocked

## Technical Approach

### Files to Create
- `src/qaagent/integrations/__init__.py`
- `src/qaagent/integrations/bugalizer_client.py`
- `tests/test_bugalizer_integration.py`

### Files to Modify
- `src/qaagent/config/models.py` — Add `BugalizerSettings`, add to `QAAgentProfile`
- `src/qaagent/config/templates.py` — Add bugalizer section to templates
- `src/qaagent/runners/orchestrator.py` — Write `diagnostics.json` to evidence after diagnostics run
- `src/qaagent/evidence/models.py` — Register `diagnostics` evidence file type
- `src/qaagent/commands/run_cmd.py` — Add `--submit-bugs` flag, submission logic
- `src/qaagent/commands/misc_cmd.py` — Add `submit-bug` command (or new file)
- `src/qaagent/cli.py` — Register new command if separate file
- `pyproject.toml` — Add `httpx` dependency (if not already present)

### Dependencies
- `httpx` for HTTP client (async-capable, timeout support, cleaner API than requests)
- No dependency on bugalizer source code — purely API-driven integration

### Design Decisions
- **Environment variable for API key** (not inline config) — follows existing pattern and Phase 26 security requirements
- **Both config + flag required** — prevents accidental submission; user must enable in config AND pass `--submit-bugs`
- **httpx over requests** — already used in test suites, supports timeouts natively
- **Separate `integrations/` package** — keeps integration code isolated, natural place for future tool integrations
- **No Bugalizer SDK dependency** — pure HTTP, so qaagent doesn't need bugalizer installed

## Files Changed

- `src/qaagent/config/models.py` — `BugalizerSettings` model + `QAAgentProfile.bugalizer`
- `src/qaagent/config/templates.py` — Bugalizer config section in templates
- `src/qaagent/runners/orchestrator.py` — Persist per-test diagnostics to `diagnostics.json`
- `src/qaagent/evidence/models.py` — Register `diagnostics` evidence file type
- `src/qaagent/integrations/__init__.py` — New package
- `src/qaagent/integrations/bugalizer_client.py` — HTTP client + payload mapping
- `src/qaagent/commands/run_cmd.py` — `--submit-bugs` flag
- `src/qaagent/commands/misc_cmd.py` — `submit-bug` command
- `tests/test_bugalizer_integration.py` — Integration tests (mocked HTTP)
- `pyproject.toml` — httpx dependency (if needed)

## Success Criteria

1. `BugalizerSettings` config model with validation, added to `QAAgentProfile`
2. `bugalizer_client.py` submits structured bug reports via HTTP with proper error handling
3. `qaagent run-all --submit-bugs` submits failed test cases to Bugalizer after diagnostics
4. `qaagent submit-bug <run-id>` submits bugs from a previous run's evidence
5. All new code covered by tests with mocked HTTP (no live Bugalizer dependency)
6. Severity mapping from diagnostic categories to Bugalizer severity levels
