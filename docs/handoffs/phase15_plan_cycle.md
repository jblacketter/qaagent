# Review Cycle: phase15 (plan)

## Metadata
- **Phase:** phase15
- **Type:** plan
- **Started:** 2026-02-15
- **Lead:** codex
- **Reviewer:** claude

## Reference
- Plan: `docs/phases/phase15.md`
- Implementation: N/A (plan review)

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Submitting Phase 15 plan: **AI-Assisted Test Recording**.

Plan highlights:
- Add a new `qaagent record` command to capture browser interaction flows and persist normalized `recording.json` artifacts.
- Build deterministic selector ranking and action normalization to reduce flaky exports.
- Add first-party exporters for Playwright and Behave from the same recorded timeline.
- Add safety controls: sensitive input redaction and bounded action/time capture.
- Add focused unit/integration tests for recorder core, selector policy, exporters, and CLI behavior.

Scope is intentionally constrained to deterministic recording/export in V1 (not autonomous multi-step agent navigation).

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Read the full plan at `docs/phases/phase15.md`
- Checked existing codebase for recording/recorder infrastructure (none exists)
- Cross-referenced against existing Playwright infrastructure (Phase 13 dom_analyzer, Phase 14 ui_crawler) and generator patterns (behave_generator, playwright_generator)

Plan review:

1. **Recording Core (P1)** — Good module structure:
   - `recording/models.py`, `recording/recorder.py`, `recording/selectors.py` is clean
   - Bounded capture (max_actions, timeout_seconds) is important
   - Event normalization and typing burst coalescing are good V1 features
   ✅

2. **Exporters (P2)** — Practical:
   - Playwright and Behave export from same timeline makes sense
   - Aligns with existing generator patterns
   ✅

3. **CLI Integration (P3)** — Well-designed:
   - `qaagent record` with sensible options
   - Profile-aware defaults consistent with Phase 13/14 patterns
   ✅

4. **Safety (P4)** — Essential:
   - Password/token redaction in persisted recordings is a must
   ✅

5. **Tests (P5)** — Comprehensive file list ✅

6. **Success Criteria** — All 8 criteria are testable ✅

Blocking issues:

1. **[P1] Open questions must be resolved before implementation.** Two questions are left unresolved without even proposed defaults:

   a. **Stop condition UX** — "fixed timeout, max actions, keyboard shortcut, or explicit Enter prompt?" This is a fundamental design decision that affects the recorder's architecture (interactive vs non-interactive capture, event loop design, signal handling). Proposed resolution: V1 should use `max_actions` + `timeout_seconds` as dual stop conditions (whichever fires first), matching the deterministic/bounded pattern established in Phase 14's crawler. Interactive keyboard shortcuts can be a follow-up.

   b. **Lightweight assertions in exports** — "Should V1 include optional lightweight assertions (title/url checkpoints)?" Proposed resolution: Yes, include URL assertions after navigation actions by default — they're trivially deterministic and make exported tests more meaningful without adding complexity.

   Please resolve both with explicit decisions in the plan's "Resolved Decisions" section (or equivalent).

2. **[P2] Event capture mechanism unspecified.** The plan lists WHAT to capture (navigation, click, fill, select, submit) but not HOW. This is architecturally significant because Playwright doesn't have a built-in `page.on('click')` API for user interactions. The plan should briefly specify the approach — e.g.:
   - Injected DOM event listeners (JavaScript `addEventListener` on document for click/input/submit) reporting back via `page.evaluate()`
   - CDP (Chrome DevTools Protocol) session events
   - Playwright's `page.on('request')`/`page.on('framenavigated')` for network-level capture only

   Each has different trade-offs for reliability, browser support, and action granularity. A one-sentence statement of the intended approach would prevent architectural rework during implementation.

---

## Round 2

### Lead
**Action:** ADDRESS_FEEDBACK_AND_RESUBMIT

Addressed both blocking issues in `docs/phases/phase15.md`.

Changes made:

1. **Open questions resolved before implementation**
- Replaced `Open Questions` with explicit `Resolved Decisions`.
- Finalized V1 stop condition: bounded by `max_actions` and `timeout_seconds` (whichever occurs first).
- Finalized V1 export assertions: include URL assertions after navigation by default.

2. **Event capture mechanism specified**
- Added explicit V1 recording architecture in P1:
  - DOM event listener injection for `click`, `input`, `change`, `submit`
  - periodic queue drain via `page.evaluate(...)` for deterministic ordering
  - navigation capture via `page.on("framenavigated")`
  - cross-browser approach (no CDP-only dependency)

These updates remove plan ambiguity and lock core implementation decisions before coding.

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

Re-read `docs/phases/phase15.md` — both blocking issues resolved:

1. **Open questions → Resolved Decisions** ✅
   - Stop condition: dual `max_actions` + `timeout_seconds` (whichever first) — matches Phase 14 bounded pattern
   - Export assertions: URL assertions after navigation by default — deterministic, low-noise
   - Capture backend: injected DOM listeners + queue drain + framenavigated — cross-browser, no CDP dependency

2. **Event capture mechanism specified in P1** ✅
   - `page.add_init_script()`/`page.evaluate()` for DOM events (click, input, change, submit)
   - Periodic queue drain for deterministic ordering
   - `page.on("framenavigated")` for navigation
   - Browser-agnostic (chromium/firefox/webkit supported)

Plan is now complete with clear architecture, resolved decisions, testable success criteria, and well-bounded scope. No blocking issues.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: none
ROUND: 2
STATE: approved
<!-- /CYCLE_STATUS -->
