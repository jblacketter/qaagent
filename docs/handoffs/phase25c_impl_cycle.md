# Phase 25c — Implementation Review Cycle

- **Phase:** phase25c
- **Type:** impl
- **Date:** 2026-02-19
- **Lead:** claude
- **Reviewer:** codex

**Plan file:** `docs/phases/phase25.md` (sub-phase 25c)

---

## Round 1

### Lead

**Action:** SUBMIT_FOR_REVIEW

Submitting Phase 25c implementation: Dashboard Board View.

**Files created:**

| File | Purpose |
|------|---------|
| `src/qaagent/dashboard/frontend/src/pages/BranchBoard.tsx` | Main kanban board page — repo selector, scan button, 6-column stage layout, detail panel toggle |
| `src/qaagent/dashboard/frontend/src/components/Branch/BranchColumn.tsx` | Single kanban column — stage header with color-coded dot, card count badge, scrollable card list |
| `src/qaagent/dashboard/frontend/src/components/Branch/BranchCardComponent.tsx` | Branch card in column — branch name, story link, commit/file stats, change summary preview |
| `src/qaagent/dashboard/frontend/src/components/Branch/BranchDetail.tsx` | Expanded detail panel — full branch info, edit form (stage/story/notes), checklist section with generate button, test runs list |
| `src/qaagent/dashboard/frontend/src/components/Branch/ChecklistView.tsx` | Interactive checklist — items grouped by category (collapsible), progress bar, click-to-cycle status (pending→passed→failed→skipped), priority badges |

**Files modified:**

| File | Change |
|------|--------|
| `src/qaagent/dashboard/frontend/src/types/index.ts` | Added 5 TypeScript interfaces: `BranchCard`, `BranchChecklistItem`, `BranchChecklist`, `BranchTestRun`, `BranchStageInfo` |
| `src/qaagent/dashboard/frontend/src/services/api.ts` | Added 10 API methods: `getBranches`, `getBranch`, `updateBranch`, `deleteBranch`, `scanBranches`, `generateChecklist`, `getChecklist`, `updateChecklistItem`, `getTestRuns`, `getBranchStages` |
| `src/qaagent/dashboard/frontend/src/App.tsx` | Added `/branch-board` route with `BranchBoardPage` component |
| `src/qaagent/dashboard/frontend/src/components/Layout/Sidebar.tsx` | Added "Branch Board" entry to `mainLinks` with `GitBranch` icon |

**Design decisions:**

- **Placed in `mainLinks` (not `repoLinks`)**: Branch Board has its own repo selector dropdown, making it accessible from any context. This follows the "hub" pattern — users can switch repos without navigating away.
- **No drag-and-drop for stage transitions**: Kept initial version simple. Stage changes are done via the edit form in the detail panel. Drag-and-drop can be added in a future iteration.
- **Click-to-cycle checklist status**: Each checklist item's status icon is clickable, cycling through `pending → passed → failed → skipped`. This is fast for QA testers working through a list.
- **Collapsible category groups**: Checklist items are grouped by category (Route Changes, Data Integrity, Config, Regression, New Code, Edge Cases) with collapsible sections and per-group progress counters.
- **Detail panel below board (not modal)**: Selected card expands into a detail section below the kanban columns. This avoids modal fatigue and lets users reference the board while editing a card.
- **Dark mode support**: All components use Tailwind `dark:` prefixes consistent with the existing dashboard theme.
- **Data fetching via react-query**: All API calls use `useQuery`/`useMutation` from `@tanstack/react-query`, consistent with every other page in the dashboard.

**Verification:**
- `npm run build` succeeds (TypeScript + Vite, 0 errors)
- All 63 branch unit tests pass
- All 33 parity tests pass (CLI + API)
- Sidebar renders "Branch Board" link with GitBranch icon
- Route `/branch-board` renders the BranchBoardPage

### Reviewer

**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Reviewed UI/API wiring in:
  - `src/qaagent/dashboard/frontend/src/pages/BranchBoard.tsx`
  - `src/qaagent/dashboard/frontend/src/components/Branch/BranchDetail.tsx`
  - `src/qaagent/dashboard/frontend/src/components/Branch/ChecklistView.tsx`
  - `src/qaagent/dashboard/frontend/src/components/Branch/BranchColumn.tsx`
  - `src/qaagent/dashboard/frontend/src/components/Branch/BranchCardComponent.tsx`
  - `src/qaagent/dashboard/frontend/src/types/index.ts`
  - `src/qaagent/dashboard/frontend/src/services/api.ts`
  - `src/qaagent/dashboard/frontend/src/App.tsx`
  - `src/qaagent/dashboard/frontend/src/components/Layout/Sidebar.tsx`
- Ran:
  - `npm run build` (passes)
  - `python -m pytest -q tests/unit/branch tests/integration/test_cli_split_parity.py tests/unit/api/test_api_app_parity.py` (passes)

Blocking issue:
1. **Branch detail edit form can save stale values to the wrong card after selection changes.**
   - `BranchDetail` initializes local edit state from props once (`useState(card.stage/story/notes)` in `src/qaagent/dashboard/frontend/src/components/Branch/BranchDetail.tsx:27`, `src/qaagent/dashboard/frontend/src/components/Branch/BranchDetail.tsx:28`, `src/qaagent/dashboard/frontend/src/components/Branch/BranchDetail.tsx:29`, `src/qaagent/dashboard/frontend/src/components/Branch/BranchDetail.tsx:30`).
   - Parent switches `card` prop without remounting the component (`<BranchDetail ... />` has no key in `src/qaagent/dashboard/frontend/src/pages/BranchBoard.tsx:170`).
   - Result: open card A, then select card B, then click edit -> form fields may still contain A's values and can be saved onto B.
   - Required fix: either remount detail on card switch (e.g., `key={card.id}`) or sync local edit state in `useEffect` when `card.id` changes.

## Round 2

### Lead

**Action:** SUBMIT_FOR_REVIEW

Fixed the stale edit state bug.

**Root cause:** `BranchDetail` initialized local edit state via `useState(card.stage)` etc. at mount time. When the parent swapped the `card` prop (user clicks a different card), React reused the existing component instance, so `useState` kept the old card's values.

**Fix:** Added `key={selectedCard.id}` to `<BranchDetail>` in `BranchBoard.tsx:170`. This forces React to unmount and remount `BranchDetail` whenever the selected card changes, ensuring fresh `useState` initialization from the new card's props.

**Changed file:**
- `src/qaagent/dashboard/frontend/src/pages/BranchBoard.tsx` line 170 — added `key={selectedCard.id}`

**Verification:**
- `npm run build` succeeds (0 errors)
- Parity tests still pass

### Reviewer

**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Confirmed fix in `src/qaagent/dashboard/frontend/src/pages/BranchBoard.tsx`:
  - `BranchDetail` now has `key={selectedCard.id}`, forcing remount on card switch and preventing stale edit state carryover.
- Ran validation:
  - `npm run build` (passes)
  - `python -m pytest -q tests/unit/branch tests/integration/test_cli_split_parity.py tests/unit/api/test_api_app_parity.py` (passes)

No blocking issues remain for Phase 25c implementation.

---

<!-- CYCLE_STATUS -->
READY_FOR: none
ROUND: 2
STATE: approved
