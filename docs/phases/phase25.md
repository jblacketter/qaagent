# Phase 25: Branch Board — Branch Lifecycle Tracker with Test Intelligence

## Status: Planning

## Summary

Add a **Branch Board** module to qaagent — a branch-aware test intelligence layer that tracks git branches from creation through merge/release, auto-generates test checklists per branch based on code changes, and provides multiple audience views (QA, dev leads, product owners).

This fills three unoccupied white spaces in the QA tooling landscape:
1. Branch lifecycle as a first-class entity (no existing tool tracks branches through multiple environments)
2. Auto-generated test plans/checklists per branch from code diffs (existing tools generate executable code, not human-readable QA checklists)
3. Unified branch + test intelligence in a single tool

## Scope

### Core Capabilities

1. **Branch Tracking & Cards**
   - Track branches from creation → active development → merged to main → merged to QA → released
   - Each branch is a "card" with: auto-generated change summary (from commits), story/ticket link (manual or auto-detected from branch name), human-editable notes, current lifecycle stage
   - Branch state machine: `created` → `active` → `in_review` → `merged` → `qa` → `released` (configurable stages)
   - **Transition rules (source of truth):**
     - `created` → `active`: **Automatic** — git polling detects new commits on the branch
     - `active` → `in_review`: **Automatic** — git polling detects an open PR (or manual override)
     - `in_review` → `merged`: **Automatic** — git polling detects branch merged into base branch
     - `merged` → `qa`: **Manual only** — user moves card via UI/API (no deployment tracking in this phase)
     - `qa` → `released`: **Manual only** — user moves card via UI/API (no deployment tracking in this phase)
     - Any stage can be manually overridden via the card editor
   - Detect branch creation/merge events via git polling (webhook support later)

2. **Test Checklist Generation**
   - Analyze the diff between a branch and its base (e.g., main) to identify changed routes, files, and risk areas
   - Auto-generate a test checklist: "these files/routes changed → here are the scenarios to verify"
   - Start with simple checklist format (easiest); Gherkin/BDD format as a follow-up
   - Leverage existing qaagent analyzers (route discovery, risk assessment) scoped to the branch diff

3. **Test Execution Integration**
   - Option to generate automated tests from the checklist (reuse existing generators: pytest, Behave, Playwright)
   - Run generated tests against the branch using existing runners
   - Track pass/fail results per branch card
   - Option to promote passing tests into the regression suite or discard them

4. **Board UI (Dashboard)**
   - Kanban-style board view with columns for each lifecycle stage
   - Branch cards show: branch name, story link, change summary, test status (checklist progress, automated test results)
   - Multiple views: QA view (test-focused), dev lead view (integration readiness), PO view (pipeline progress)
   - Click into a card for full detail: diff summary, checklist, test results, notes

5. **Story/Ticket Association**
   - Auto-detect story IDs from branch naming conventions (e.g., `feature/PROJ-123-description`)
   - Manual association via card editing
   - Display story reference on cards (link to Jira/Trello/GitHub Issues — read-only, no write integration initially)

### Out of Scope (Future Phases)

- GitHub/GitLab webhook receiver (start with git polling)
- Jira/Trello write integration (start with read-only links)
- Gherkin/BDD checklist format (start with simple checklists)
- Deployment tracking to environments (start with branch merge tracking)
- Slack/email notifications
- AI-powered risk scoring per branch ("this branch is high-risk because...")

## Technical Approach

### New Module: `src/qaagent/branch/`

| File | Purpose |
|------|---------|
| `__init__.py` | Package init |
| `models.py` | Pydantic models: `BranchCard`, `BranchStage`, `TestChecklist`, `ChecklistItem`, `StoryLink` |
| `tracker.py` | `BranchTracker` — discovers branches, detects state changes, manages lifecycle |
| `diff_analyzer.py` | `DiffAnalyzer` — computes branch diff vs. base, identifies changed routes/files/risks |
| `checklist_generator.py` | `ChecklistGenerator` — produces test checklists from diff analysis |
| `store.py` | `BranchStore` — SQLite persistence for branch cards, checklists, test results |

### Integration Points

| Component | Location | Change |
|-----------|----------|--------|
| CLI commands | `src/qaagent/commands/branch_cmd.py` | `qaagent branch list`, `branch track`, `branch checklist`, `branch run-tests` |
| API routes | `src/qaagent/api/routes/branches.py` | CRUD for branch cards, checklist endpoints, test execution triggers |
| Dashboard page | `src/qaagent/dashboard/frontend/src/pages/BranchBoard.tsx` | Kanban board view |
| Dashboard components | `src/qaagent/dashboard/frontend/src/components/Branch/` | `BranchCard.tsx`, `BranchColumn.tsx`, `ChecklistView.tsx`, `BranchDetail.tsx` |
| Sidebar nav | `Sidebar.tsx` | New "Branch Board" link |
| DB migrations | `src/qaagent/db.py` | Tables: `branches`, `branch_checklists`, `branch_checklist_items`, `branch_test_runs` |
| pyproject.toml | `[project.optional-dependencies]` | New `branch` extra if any unique deps needed |

### Reused Infrastructure

- **`RepoCloner`** — clone/update repos, `get_repo_info()` for branch/commit metadata
- **`GitChurnCollector`** — file-level change statistics
- **Route analyzer** — discover routes in changed files
- **Risk assessment** — assess risks for changed routes
- **Test generators** — generate pytest/Behave/Playwright from routes+risks
- **Test runners** — execute generated tests, parse JUnit results
- **Evidence system** — store test run results per branch
- **Auth middleware** — protect branch API endpoints
- **Dashboard Layout/Sidebar** — extend existing navigation

### Database Schema (New Tables)

```sql
CREATE TABLE branches (
    id INTEGER PRIMARY KEY,
    repo_id TEXT NOT NULL REFERENCES repositories(id),
    branch_name TEXT NOT NULL,
    base_branch TEXT DEFAULT 'main',
    stage TEXT DEFAULT 'created',  -- created, active, in_review, merged (auto via git); qa, released (manual only)
    story_id TEXT,                 -- e.g., "PROJ-123"
    story_url TEXT,                -- link to ticket
    notes TEXT,                    -- human-editable notes
    change_summary TEXT,           -- auto-generated from commits
    first_seen_at TEXT,
    last_updated_at TEXT,
    merged_at TEXT,
    UNIQUE(repo_id, branch_name)
);

CREATE TABLE branch_checklists (
    id INTEGER PRIMARY KEY,
    branch_id INTEGER REFERENCES branches(id),
    generated_at TEXT,
    format TEXT DEFAULT 'checklist',  -- checklist or gherkin (future)
    source_diff TEXT                  -- stored diff hash for staleness detection
);

CREATE TABLE branch_checklist_items (
    id INTEGER PRIMARY KEY,
    checklist_id INTEGER REFERENCES branch_checklists(id),
    description TEXT NOT NULL,
    category TEXT,            -- e.g., "route_change", "security", "edge_case"
    priority TEXT,            -- high, medium, low
    status TEXT DEFAULT 'pending',  -- pending, passed, failed, skipped
    notes TEXT
);

CREATE TABLE branch_test_runs (
    id INTEGER PRIMARY KEY,
    branch_id INTEGER REFERENCES branches(id),
    run_id TEXT,              -- links to evidence system run
    suite_type TEXT,          -- pytest, behave, playwright
    total INTEGER,
    passed INTEGER,
    failed INTEGER,
    skipped INTEGER,
    promoted_to_regression BOOLEAN DEFAULT FALSE,
    run_at TEXT
);
```

## Implementation Sub-Phases

Given the scope, this should be broken into sub-phases:

### 25a: Foundation — Models, Store, Tracker, CLI
- Pydantic models for branch cards and checklists
- SQLite store with migrations
- `BranchTracker` that scans a repo's branches and populates cards
- CLI: `qaagent branch list`, `qaagent branch track <repo>`
- Auto-detect story IDs from branch names

### 25b: Diff Analysis & Checklist Generation
- `DiffAnalyzer` — compute diff vs. base branch, identify changed files/routes
- `ChecklistGenerator` — produce test checklists from diff analysis
- CLI: `qaagent branch checklist <branch>`
- API endpoints for checklist CRUD

### 25c: Dashboard — Board View
- `BranchBoard.tsx` kanban page with columns per stage
- `BranchCard.tsx` component with summary, story link, test status
- `BranchDetail.tsx` — full card view with checklist, notes, test results
- Sidebar navigation entry
- API endpoints for branch CRUD

### 25d: Test Execution & Promotion
- Generate automated tests from checklist items (reuse existing generators)
- Run tests via existing runners, store results per branch
- UI for test results on branch cards
- "Promote to regression" action

## Files Changed/Created

| File | Action |
|------|--------|
| `src/qaagent/branch/__init__.py` | Create |
| `src/qaagent/branch/models.py` | Create |
| `src/qaagent/branch/tracker.py` | Create |
| `src/qaagent/branch/diff_analyzer.py` | Create |
| `src/qaagent/branch/checklist_generator.py` | Create |
| `src/qaagent/branch/store.py` | Create |
| `src/qaagent/commands/branch_cmd.py` | Create |
| `src/qaagent/commands/__init__.py` | Edit — register branch subcommand |
| `src/qaagent/api/routes/branches.py` | Create |
| `src/qaagent/api/app.py` | Edit — include branch router |
| `src/qaagent/web_ui.py` | Edit — include branch router |
| `src/qaagent/db.py` | Edit — add branch table migrations |
| `src/qaagent/dashboard/frontend/src/pages/BranchBoard.tsx` | Create |
| `src/qaagent/dashboard/frontend/src/components/Branch/BranchCard.tsx` | Create |
| `src/qaagent/dashboard/frontend/src/components/Branch/BranchColumn.tsx` | Create |
| `src/qaagent/dashboard/frontend/src/components/Branch/BranchDetail.tsx` | Create |
| `src/qaagent/dashboard/frontend/src/components/Branch/ChecklistView.tsx` | Create |
| `src/qaagent/dashboard/frontend/src/App.tsx` | Edit — add route |
| `src/qaagent/dashboard/frontend/src/components/Layout/Sidebar.tsx` | Edit — add nav link |
| `pyproject.toml` | Edit — optional `branch` extra if needed |

## Success Criteria

### 25a (Foundation)
- `qaagent branch track <repo-path>` scans branches and creates cards in the DB
- `qaagent branch list` shows all tracked branches with stage, story ID, last activity
- Branch stage auto-updates when merges are detected
- Story IDs auto-detected from branch names matching common patterns

### 25b (Diff & Checklists)
- `qaagent branch checklist <branch>` produces a test checklist from the branch diff
- Checklist items categorized by type (route change, security, edge case) and prioritized
- Checklist stored in DB and retrievable via API

### 25c (Dashboard)
- `/branch-board` page renders a kanban board with columns per lifecycle stage
- Branch cards display name, story link, change summary, test status
- Clicking a card opens detail view with full checklist and notes
- Cards can be manually edited (notes, story link, stage override)

### 25d (Test Execution)
- "Generate tests" button on a branch card produces automated tests from the checklist
- "Run tests" executes them and displays results on the card
- "Promote to regression" marks selected tests for inclusion in the regression suite
