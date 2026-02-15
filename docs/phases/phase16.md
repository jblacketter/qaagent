# Phase 16: Integration Reliability & MCP Protocol Alignment

## Status
- [x] Planning
- [ ] In Review
- [ ] Approved
- [ ] Implementation
- [ ] Implementation Review
- [ ] Complete

## Roles
- Lead: codex
- Reviewer: claude
- Arbiter: Human

## Summary
**What:** Resolve remaining integration regressions in the API workflow and MCP stdio handshake path, and harden test harness reliability.
**Why:** The project has strong feature coverage through Phase 15, but known integration failures still reduce confidence in end-to-end and MCP workflows.
**Depends on:** Phase 15 (AI-Assisted Test Recording) - Complete

## Context

Known failing targets as of 2026-02-15:
- `tests/integration/test_api_workflow.py::test_full_api_workflow`
  - petstore fixture startup times out waiting for `http://127.0.0.1:8765/health`
- `tests/integration/test_mcp_server.py::test_mcp_server_initializes`
  - MCP `initialize` returns JSON-RPC `-32602 Invalid request parameters`
- `tests/integration/test_mcp_server.py::test_mcp_detect_openapi_tool`
  - blocked by the same fixture startup timeout path

Phase 5 explicitly deferred pre-existing failures. This phase is the cleanup/hardening follow-up so the integration baseline is trustworthy again.

## Scope

### In Scope
- Harden integration server fixture startup/teardown behavior:
  - avoid fixed-port collisions
  - improve readiness checks
  - expose actionable startup diagnostics on failure
- Align MCP integration handshake behavior with current FastMCP expectations while preserving qaagent MCP tool compatibility.
- Make the full API workflow integration test deterministic under local/CI timing variability.
- Add/adjust targeted tests so regressions are caught early and with clear failure messages.

### Out of Scope
- New analyzer/generator/user-facing feature commands.
- Broad CI matrix refactors.
- Re-architecting MCP tool definitions or switching transport protocols.

## Technical Approach

### P1 - Integration Fixture Hardening

Update `tests/conftest.py` fixture behavior:
- replace fixed port (`8765`) with an available dynamic local port
- keep startup bounded with explicit timeout and process liveness checks
- capture startup stderr (or tail) and surface it in fixture failure output
- keep teardown deterministic (terminate -> wait -> kill fallback)

### P2 - MCP Initialize Compatibility

Update MCP integration handshake flow in tests (and server compatibility path if required):
- align initialize request payload with the FastMCP protocol shape expected by installed dependency versions
- preserve existing MCP tool contract checks (`tools/list`, `tools/call` for `detect_openapi`, `discover_routes`, `assess_risks`)
- if server-side guardrails are needed, add compatibility handling without breaking existing clients

### P3 - API Workflow Determinism

Stabilize `test_full_api_workflow` execution path:
- ensure base URL resolves from fixture-provided dynamic port
- reduce race conditions around server readiness and downstream CLI calls
- keep timeout values explicit and defensible for CI variability

### P4 - Regression Coverage

Add/update regression-focused tests:
- MCP initialize success path validation
- MCP tool list/call smoke flow after initialize
- petstore fixture failure diagnostics behavior (where testable)

### P5 - Validation

Required validation run for phase completion:
- `pytest -q tests/integration/test_api_workflow.py::test_full_api_workflow tests/integration/test_mcp_server.py::test_mcp_server_initializes tests/integration/test_mcp_server.py::test_mcp_detect_openapi_tool`
- relevant MCP/CLI parity regression tests if touched by implementation

## Files to Create/Modify

### New Files
- `docs/phases/phase16_impl.md` (implementation phase)

### Modified Files
- `tests/conftest.py`
- `tests/integration/test_api_workflow.py`
- `tests/integration/test_mcp_server.py`
- `src/qaagent/mcp_server.py` (only if compatibility shim is required)

## Success Criteria
- [ ] `tests/integration/test_api_workflow.py::test_full_api_workflow` passes reliably
- [ ] `tests/integration/test_mcp_server.py::test_mcp_server_initializes` passes
- [ ] `tests/integration/test_mcp_server.py::test_mcp_detect_openapi_tool` passes
- [ ] Fixture startup failures provide actionable diagnostics (instead of opaque timeout only)
- [ ] MCP tool contract remains functional (`tools/list` and target tool calls)
- [ ] No regressions introduced in adjacent command/MCP test coverage

## Resolved Decisions
- Use dynamic port allocation for the petstore integration fixture to eliminate local port collision flakiness.
- Treat MCP initialize payload compatibility as a first-class reliability issue in this phase (not a test-only workaround).

## Risks
- FastMCP protocol expectations may vary by installed version; mitigated by explicit payload alignment and compatibility handling.
- Integration timing variance across environments; mitigated by bounded readiness waits and better process diagnostics.
