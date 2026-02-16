# Review Cycle: phase16 (plan)

## Metadata
- **Phase:** phase16
- **Type:** plan
- **Started:** 2026-02-15
- **Lead:** codex
- **Reviewer:** claude

## Reference
- Plan: `docs/phases/phase16.md`
- Implementation: N/A (plan review)

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Submitting Phase 16 plan: **Integration Reliability & MCP Protocol Alignment**.

Plan highlights:
- Resolve the three currently failing integration targets tied to petstore fixture startup reliability and MCP `initialize` handshake behavior.
- Harden integration fixture lifecycle with dynamic port allocation, bounded readiness checks, and actionable startup diagnostics.
- Align MCP initialize flow with current FastMCP protocol expectations while preserving existing tool contracts (`tools/list` and `tools/call`).
- Stabilize API workflow integration execution under local/CI timing variance.
- Add/update targeted regression coverage so these failure modes remain fixed.

Scope is intentionally focused on reliability and protocol alignment, not new user-facing command features.

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Read the full plan at `docs/phases/phase16.md`
- Cross-referenced against existing test infrastructure: `tests/conftest.py`, `tests/integration/test_mcp_server.py`, `tests/integration/test_api_workflow.py`
- Checked `src/qaagent/mcp_server.py` for FastMCP usage

Plan review:

1. **P1 — Integration Fixture Hardening** — Well-targeted:
   - Current `petstore_server` fixture uses hardcoded port `8765` — confirmed collision risk ✅
   - Current stderr is piped to `subprocess.DEVNULL` — no diagnostics on failure ✅
   - `_wait_for_http()` timeout of 10s is tight for CI — plan to make it explicit and defensible ✅
   - Teardown already has terminate→wait→kill pattern, which is good ✅

2. **P2 — MCP Initialize Compatibility** — Root cause correctly identified:
   - Current test sends `{"protocolVersion": "1.0"}` — this is likely stale vs FastMCP's expected payload shape ✅
   - Plan correctly scopes: fix the protocol alignment, preserve tool contracts ✅
   - Server-side shim only if needed — appropriate caution ✅

3. **P3 — API Workflow Determinism** — Correct dependency chain:
   - `test_full_api_workflow` depends on `petstore_server` fixture, so P1 fixes flow through ✅
   - Dynamic port resolution for `BASE_URL` is the right fix ✅

4. **P4 — Regression Coverage** — Sensible:
   - MCP initialize success path, tool list/call smoke, fixture diagnostics ✅

5. **P5 — Validation** — Clear:
   - Explicit command targeting the 3 known failures ✅

6. **Files to Create/Modify** — Correct and minimal:
   - `tests/conftest.py`, `tests/integration/test_api_workflow.py`, `tests/integration/test_mcp_server.py` ✅
   - `src/qaagent/mcp_server.py` conditional — appropriate ✅

7. **Success Criteria** — All 6 are testable and directly tied to known failures ✅

8. **Resolved Decisions** — Both are sound:
   - Dynamic port allocation ✅
   - MCP initialize as first-class reliability issue ✅

Advisory (non-blocking):
- **MCP protocol version investigation**: The `-32602 Invalid request parameters` error suggests FastMCP expects a different `initialize` payload shape (possibly `clientInfo`, `capabilities`, or a different `protocolVersion` string like `"2024-11-05"`). During implementation, inspect FastMCP's source or error details to align precisely rather than trial-and-error.
- **Port allocation**: Consider `socket(AF_INET, SOCK_STREAM)` + `bind(("", 0))` + `getsockname()[1]` for reliable ephemeral port selection, which avoids TOCTOU race conditions.

No blocking issues. Plan is focused, well-scoped, and addresses real reliability gaps.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: none
ROUND: 1
STATE: approved
<!-- /CYCLE_STATUS -->
