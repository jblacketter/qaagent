# Phase 25 — Plan Review Cycle

- **Phase:** phase25
- **Type:** plan
- **Date:** 2026-02-18
- **Lead:** claude
- **Reviewer:** codex

**Plan file:** `docs/phases/phase25.md`

---

## Round 1

### Lead

**Action:** SUBMIT_FOR_REVIEW

Submitting the Phase 25 plan for review. This phase introduces **Branch Board** — a branch lifecycle tracker with integrated test intelligence, implemented as a new module within qaagent.

**Context & Motivation:**
- Research confirmed three unoccupied white spaces in the QA tooling landscape: (1) branch lifecycle as a first-class entity, (2) auto-generated test checklists from code diffs, (3) unified branch + test intelligence. No existing tool combines these.
- The qaagent architecture is highly modular and already provides git operations, test generation, test execution, risk analysis, a React dashboard, and a FastAPI API — all of which Branch Board reuses.

**Key design decisions:**
- **Module within qaagent** (not a separate project) — reuses existing infrastructure with minimal glue code
- **New subpackage** `src/qaagent/branch/` following established patterns (`doc/`, `evidence/`, `runners/`)
- **Branch lifecycle state machine**: `created → active → in_review → merged → qa → released` (configurable stages)
- **Checklist-first** test format (simpler than Gherkin); BDD format planned as a follow-up
- **Git polling** for branch discovery (webhook support deferred)
- **Four sub-phases** (25a–25d) to manage scope: foundation → diff/checklists → dashboard → test execution
- **Story auto-detection** from branch naming conventions (e.g., `feature/PROJ-123-desc`)
- **SQLite persistence** with four new tables: `branches`, `branch_checklists`, `branch_checklist_items`, `branch_test_runs`
- **Optional extras** pattern in pyproject.toml for branch-specific dependencies

### Reviewer

**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Reviewed `docs/phases/phase25.md` against current project structure in:
  - `src/qaagent/db.py`
  - `src/qaagent/commands/__init__.py`
  - `src/qaagent/api/app.py`
  - `src/qaagent/web_ui.py`
  - `src/qaagent/dashboard/frontend/src/App.tsx`
  - `src/qaagent/dashboard/frontend/src/components/Layout/Sidebar.tsx`

Blocking issues:
1. **Repository foreign key type is inconsistent with the existing schema.**
   - The proposed SQL uses `repo_id INTEGER REFERENCES repositories(id)`.
   - Current schema defines `repositories.id` as `TEXT` in `src/qaagent/db.py`.
   - Required fix: update the phase plan so all branch tables use `repo_id TEXT` (and align model/API types accordingly) to avoid type drift and join/validation bugs.
2. **Lifecycle transition source-of-truth is underspecified for non-git stages.**
   - Plan includes stages through `qa` and `released`, but phase scope says deployment/environment tracking is out-of-scope.
   - Required fix: explicitly define transition ownership/rules for each stage in phase 25 (for example, git-detected automatic transitions only up to `merged`, and `qa`/`released` manual-only until deployment integration exists).

## Round 2

### Lead

**Action:** SUBMIT_REVISION

Addressed both reviewer findings:

**Finding 1 — Repository foreign key type mismatch:**
- Verified `repositories.id` is `TEXT PRIMARY KEY` in `src/qaagent/db.py` (line 88).
- Updated the `branches` table schema in the plan: `repo_id INTEGER` → `repo_id TEXT NOT NULL REFERENCES repositories(id)`.
- All Pydantic models and API types will use `str` for `repo_id` accordingly.

**Finding 2 — Lifecycle transition ownership for non-git stages:**
- Added explicit **Transition Rules** section under the state machine definition in the plan:
  - `created → active`: **Automatic** — git polling detects new commits
  - `active → in_review`: **Automatic** — git polling detects open PR (or manual override)
  - `in_review → merged`: **Automatic** — git polling detects branch merged into base
  - `merged → qa`: **Manual only** — user moves card via UI/API
  - `qa → released`: **Manual only** — user moves card via UI/API
  - Any stage can be manually overridden via the card editor
- Updated the schema comment to annotate which stages are auto vs. manual.
- This makes clear that `qa` and `released` are manual-only until deployment integration is added in a future phase.

### Reviewer

**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Confirmed `repo_id` alignment fix in `docs/phases/phase25.md`:
  - `branches.repo_id` is now `TEXT NOT NULL REFERENCES repositories(id)`, matching `repositories.id` in `src/qaagent/db.py`.
  - Lead explicitly committed to `str` typing for `repo_id` in models/API.
- Confirmed lifecycle ownership rules are now explicit in `docs/phases/phase25.md`:
  - Git-driven automatic transitions through `merged`.
  - `merged -> qa` and `qa -> released` defined as manual-only in this phase.
  - Manual override behavior is documented.

No blocking issues remain for Phase 25 plan.

---

<!-- CYCLE_STATUS -->
READY_FOR: none
ROUND: 2
STATE: approved
