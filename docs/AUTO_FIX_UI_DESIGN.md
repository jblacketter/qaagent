# Auto-Fix UI Design & Implementation Plan

## Overview

Add auto-fix capabilities to the web dashboard, allowing users to fix code quality issues directly from the UI without using CLI commands.

**Status:** 📋 Planned - Document approved, ready for Phase 1 implementation

---

## 🎯 Three Integration Points

### 1. Category-Level Fixes (High-Level Overview)

**Location:** New "Fixable Issues" card on Dashboard/Landing page

**Visual Design:**
```
┌─────────────────────────────────────────────────┐
│ 🔧 Fixable Issues (57 files)                   │
├─────────────────────────────────────────────────┤
│                                                 │
│ 📝 Formatting Issues                           │
│    • 42 files with PEP 8 violations            │
│    • Line length, whitespace, indentation      │
│    [Preview Changes] [Fix All - autopep8] ✓    │
│                                                 │
│ 📦 Import Issues                               │
│    • 15 files with unsorted imports            │
│    • Wrong import order, unused imports        │
│    [Preview Changes] [Fix All - isort] ✓       │
│                                                 │
│ 🔐 Security Issues                             │
│    • 3 files with potential vulnerabilities    │
│    • Requires manual review                    │
│    [View Details] [Generate AI Fixes] 🤖       │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ Clear overview of what can be auto-fixed
- ✅ Batch fixes by category (efficient)
- ✅ Shows impact before applying
- ✅ Separates safe auto-fixes from manual review

**User Flow:**
1. User lands on dashboard
2. Sees "Fixable Issues" card with categories
3. Clicks "Fix All - autopep8" button
4. Confirmation modal appears with summary
5. User confirms
6. Progress indicator shows
7. Success message with "Re-scan" option

---

### 2. File-Level Fixes (Risk Detail View)

**Location:** Individual risk cards in Risks page

**Visual Design:**
```
┌─────────────────────────────────────────────────────────┐
│ 🔴 CRITICAL: python-tests/ui/pages/mixins/nav.py       │
├─────────────────────────────────────────────────────────┤
│ Risk Score: 100  |  Security: 162  |  Coverage: 0      │
│                                                         │
│ 📋 Issues Found:                                        │
│   • 12 PEP 8 violations (fixable) ✓                    │
│   •  3 import order issues (fixable) ✓                 │
│   •  1 security warning (review needed) ⚠️              │
│                                                         │
│ 🔧 Quick Actions:                                       │
│   [Auto-Fix Formatting] [Auto-Fix Imports]             │
│   [Fix All Safe Issues] [View Code] [Dismiss]          │
│                                                         │
│ 💡 What would be fixed:                                 │
│   • Lines 12, 45, 78: Trailing whitespace              │
│   • Line 134: Line too long (132 > 79 chars)           │
│   • Imports: Move stdlib imports above third-party     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ Context-aware fixes (user sees exactly what file)
- ✅ Granular control (fix just this file)
- ✅ Shows preview of changes
- ✅ Doesn't require leaving risk view

**User Flow:**
1. User viewing specific risk
2. Sees "Auto-Fix Formatting" button
3. Clicks button
4. Mini modal shows what will be fixed
5. User confirms
6. File is fixed
7. Risk card updates to show reduced issues

---

### 3. Guided Fix Wizard (Step-by-Step Flow)

**Location:** New page route: `/fix-wizard`

**Step 1: Select Issues to Fix**
```
┌─────────────────────────────────────────────┐
│ Step 1 of 4: Select Issues                 │
├─────────────────────────────────────────────┤
│                                             │
│ ☑️ Formatting Issues (42 files)            │
│    PEP 8 violations: line length,          │
│    whitespace, indentation                 │
│                                             │
│ ☑️ Import Issues (15 files)                │
│    Unsorted imports, wrong grouping        │
│                                             │
│ ☐ Security Issues (requires manual review) │
│    Cannot be auto-fixed safely             │
│                                             │
│ [Cancel] [Next: Preview Changes →]         │
└─────────────────────────────────────────────┘
```

**Step 2: Preview Changes**
```
┌─────────────────────────────────────────────┐
│ Step 2 of 4: Preview Changes               │
├─────────────────────────────────────────────┤
│                                             │
│ Changes to be made:                         │
│                                             │
│ 📄 python-tests/ui/pages/login.py          │
│   - Line 45: Remove trailing whitespace    │
│   - Line 67: Shorten line (98 → 79 chars)  │
│   [View Full Diff]                          │
│                                             │
│ 📄 python-tests/ui/steps/auth.py           │
│   - Imports: Reorder (stdlib → third-party)│
│   [View Full Diff]                          │
│                                             │
│ ... and 55 more files                       │
│                                             │
│ 📊 Total: 57 files, 234 changes             │
│                                             │
│ [← Back] [Apply Fixes →]                   │
└─────────────────────────────────────────────┘
```

**Step 3: Applying Fixes**
```
┌─────────────────────────────────────────────┐
│ Step 3 of 4: Applying Fixes                │
├─────────────────────────────────────────────┤
│                                             │
│ 🔄 Fixing files... (42/57)                 │
│ ████████████░░░░░░░░ 74%                   │
│                                             │
│ Current: python-tests/ui/support/wait.py   │
│                                             │
│ ✓ Completed: 41 files                      │
│ ⏳ In Progress: 1 file                      │
│ ⏱️  Remaining: 15 files                     │
│                                             │
└─────────────────────────────────────────────┘
```

**Step 4: Complete**
```
┌─────────────────────────────────────────────┐
│ Step 4 of 4: Complete                      │
├─────────────────────────────────────────────┤
│                                             │
│ ✅ Fixed 57 files successfully!            │
│                                             │
│ 📊 Summary:                                 │
│   • Formatting: 42 files fixed             │
│   • Imports: 15 files fixed                │
│   • Total changes: 234 lines               │
│                                             │
│ 🔄 Next Steps:                              │
│   1. Re-scan repository to verify fixes    │
│   2. Review changes with git diff          │
│   3. Commit changes to version control     │
│                                             │
│ [Re-scan Now] [View Changes] [Done]        │
└─────────────────────────────────────────────┘
```

**Benefits:**
- ✅ User friendly for non-technical users
- ✅ Clear confirmation before changes
- ✅ Progress feedback with real-time updates
- ✅ Guides next steps after completion

---

## 🔌 API Design

### New Endpoints

#### 1. Get Fixable Issues Summary
```typescript
GET /api/repositories/{repo_id}/fixable-issues

Response: {
  categories: [
    {
      category: "formatting",
      tool: "autopep8",
      file_count: 42,
      issue_count: 234,
      auto_fixable: true,
      severity_breakdown: {
        critical: 0,
        high: 2,
        medium: 150,
        low: 82
      },
      affected_files: [
        "python-tests/ui/pages/login.py",
        "python-tests/ui/steps/auth.py",
        ...
      ]
    },
    {
      category: "imports",
      tool: "isort",
      file_count: 15,
      issue_count: 47,
      auto_fixable: true,
      affected_files: [...]
    },
    {
      category: "security",
      tool: "bandit",
      file_count: 3,
      issue_count: 5,
      auto_fixable: false,
      requires_manual_review: true,
      llm_available: true  // Can use LLM for fixes
    }
  ],
  total_fixable: 57,
  total_manual: 3,
  repository: {
    path: "/path/to/repo",
    last_scan: "2025-10-28T10:00:00Z"
  }
}
```

#### 2. Preview Fixes for Category
```typescript
POST /api/repositories/{repo_id}/preview-fix

Body: {
  category: "formatting",
  tool: "autopep8",
  files?: ["specific/file.py"]  // Optional: preview specific files only
}

Response: {
  files: [
    {
      path: "python-tests/ui/pages/login.py",
      changes: [
        {
          line: 45,
          type: "remove_whitespace",
          before: "    def login(self):    ",
          after: "    def login(self):"
        },
        {
          line: 67,
          type: "shorten_line",
          before: "    result = self.api.call_very_long_method_name_with_many_parameters(param1, param2, param3, param4)",
          after: "    result = self.api.call_very_long_method_name(\n        param1, param2, param3, param4\n    )"
        }
      ],
      issue_count: 12
    }
  ],
  total_files: 42,
  total_changes: 234,
  estimated_time_seconds: 15
}
```

#### 3. Apply Fixes
```typescript
POST /api/repositories/{repo_id}/apply-fix

Body: {
  category: "formatting",
  tool: "autopep8",
  files?: ["file1.py", "file2.py"]  // Optional: if not provided, fixes all
}

Response: {
  status: "success",
  files_modified: 42,
  files_failed: 0,
  message: "Fixed 42 files successfully",
  results: [
    {
      file: "python-tests/ui/pages/login.py",
      status: "success",
      changes_made: 12
    },
    {
      file: "python-tests/ui/steps/auth.py",
      status: "success",
      changes_made: 3
    }
  ]
}
```

#### 4. Real-Time Progress (WebSocket)
```typescript
WS /api/repositories/{repo_id}/fix-progress

Messages (streamed during fix):
{
  type: "progress",
  current: 42,
  total: 57,
  percent: 74,
  current_file: "python-tests/ui/support/wait.py",
  status: "processing"
}

{
  type: "file_complete",
  file: "python-tests/ui/support/wait.py",
  changes_made: 5,
  status: "success"
}

{
  type: "complete",
  files_modified: 57,
  total_changes: 234,
  duration_seconds: 23
}

{
  type: "error",
  file: "python-tests/ui/pages/broken.py",
  error: "Permission denied"
}
```

---

## 🏗️ React Components Structure

```
src/qaagent/dashboard/frontend/src/
├── pages/
│   ├── FixWizard.tsx          # Step-by-step guided flow
│   ├── FixableIssues.tsx      # Category-level overview page
│   └── Risks.tsx              # Enhanced with fix buttons
├── components/
│   ├── fix/
│   │   ├── FixCard.tsx            # Category card with fix button
│   │   ├── FixPreview.tsx         # Show before/after changes
│   │   ├── FixPreviewModal.tsx    # Modal for previewing changes
│   │   ├── FixProgress.tsx        # Progress bar during fixes
│   │   ├── FixSummary.tsx         # Summary after completion
│   │   ├── FileFixActions.tsx     # Per-file fix buttons
│   │   ├── DiffViewer.tsx         # Side-by-side diff display
│   │   └── ConfirmFixModal.tsx    # Confirmation before applying
│   └── risks/
│       └── RiskCard.tsx           # Enhanced with fix actions
└── services/
    ├── api.ts                     # Existing API client
    └── fixService.ts              # New: API calls for fixes

# Example: FixCard.tsx
interface FixCardProps {
  category: string;
  tool: string;
  fileCount: number;
  issueCount: number;
  autoFixable: boolean;
  onPreview: () => void;
  onFix: () => void;
}

# Example: FixProgress.tsx
interface FixProgressProps {
  current: number;
  total: number;
  currentFile: string;
  onCancel?: () => void;
}
```

---

## 📋 Implementation Phases

### Phase 1: Category-Level Fixes (Quickest Win) ✅ NEXT
**Time Estimate:** 3-4 hours
**Priority:** High

**Backend (Python):**
- [ ] Add `/api/repositories/{id}/fixable-issues` endpoint
- [ ] Add `/api/repositories/{id}/apply-fix` endpoint
- [ ] Integrate with existing `autofix.py` module
- [ ] Return proper error handling and validation

**Frontend (React):**
- [ ] Create `FixCard.tsx` component
- [ ] Add "Fixable Issues" section to Landing page
- [ ] Create confirmation modal
- [ ] Add success/error toast notifications
- [ ] Show progress spinner during fix

**Features:**
- Group issues by category (formatting, imports, security)
- "Fix All" button per category
- Simple confirmation modal
- Show success message with file count

**Acceptance Criteria:**
- User sees fixable issues on landing page
- User can click "Fix All - autopep8"
- Confirmation modal shows before applying
- Progress indicator during fix
- Success message shows files modified
- Errors are displayed clearly

---

### Phase 2: File-Level Actions
**Time Estimate:** 2-3 hours
**Priority:** Medium

**Backend:**
- [ ] Add file filtering to `/apply-fix` endpoint
- [ ] Return per-file fix status

**Frontend:**
- [ ] Add `FileFixActions.tsx` component
- [ ] Enhance `RiskCard.tsx` with fix buttons
- [ ] Show "What would be fixed" list
- [ ] Update risk card after fix applied

**Features:**
- Fix buttons on individual risk cards
- Show specific issues that would be fixed
- "Fix This File" action
- Real-time risk card updates

**Acceptance Criteria:**
- User sees fix buttons on risk cards
- Can preview what would be fixed for that file
- Can fix single file
- Risk card updates after fix

---

### Phase 3: Preview & Wizard
**Time Estimate:** 4-5 hours
**Priority:** Low (nice-to-have)

**Backend:**
- [ ] Add `/api/repositories/{id}/preview-fix` endpoint
- [ ] Run dry-run of fixes to get diff
- [ ] WebSocket for real-time progress

**Frontend:**
- [ ] Create `FixWizard.tsx` with 4 steps
- [ ] Create `FixPreview.tsx` with diff viewer
- [ ] Create `DiffViewer.tsx` for side-by-side comparison
- [ ] Add WebSocket connection for progress
- [ ] Add multi-step navigation

**Features:**
- Multi-step wizard (select → preview → apply → summary)
- Diff viewer showing before/after
- Real-time progress with WebSocket
- Summary page with statistics

**Acceptance Criteria:**
- Wizard guides through 4 steps
- User can preview all changes before applying
- Progress updates in real-time
- Summary shows detailed statistics

---

## 🔒 Safety Features

### Must-Haves (Phase 1):
1. **Confirmation modal** - Always ask before applying fixes
2. **Error handling** - Show clear errors if fix fails
3. **Success feedback** - Show what was fixed
4. **Re-scan prompt** - Offer to re-scan after fixes
5. **Backend validation** - Validate tool exists, files are writable

### Should-Haves (Phase 2):
1. **Preview changes** - Show what will be fixed
2. **Git check** - Warn if uncommitted changes exist
3. **Per-file status** - Show which files succeeded/failed
4. **Rollback info** - Instructions to undo with git

### Nice-to-Haves (Phase 3):
1. **Diff viewer** - Side-by-side before/after
2. **File-by-file approval** - Approve each file individually
3. **Backup files** - Store originals temporarily
4. **Auto-commit** - Commit fixes with generated message
5. **Test integration** - Run tests after fix
6. **Undo button** - One-click rollback

---

## 🎨 User Flow Examples

### Quick Fix Flow (Power User)
**Time:** ~30 seconds

1. User lands on dashboard
2. Sees "57 fixable issues" in Fixable Issues card
3. Clicks "Fix All - autopep8" button
4. Confirmation modal: "Fix 42 files with autopep8?"
5. User clicks "Confirm"
6. Progress spinner: "Fixing files... (42/42)"
7. Success toast: "✓ Fixed 42 files successfully!"
8. Dashboard updates, "Re-scan now?" button appears
9. User clicks "Re-scan" to verify

### Careful Review Flow (Cautious User)
**Time:** ~2 minutes

1. User goes to Risks page
2. Finds risk for `python-tests/ui/pages/login.py`
3. Sees "12 PEP 8 violations (fixable)" badge
4. Clicks "Preview Fixes" button
5. Modal shows:
   - Line 45: Remove trailing whitespace
   - Line 67: Shorten line (132 → 79 chars)
   - ... 10 more changes
6. User reviews and clicks "Apply to This File"
7. Modal closes, risk card updates
8. Badge now shows "0 PEP 8 violations"
9. Risk score decreased

### Wizard Flow (New User)
**Time:** ~3 minutes

1. User clicks "Fix Issues" button on landing page
2. **Step 1:** Select categories
   - Checks "Formatting" and "Imports"
   - Leaves "Security" unchecked
   - Clicks "Next"
3. **Step 2:** Preview changes
   - Sees list of 57 files with changes
   - Expands `login.py` to see diff
   - Clicks "Apply Fixes"
4. **Step 3:** Progress
   - Watches progress bar: 42/57 files
   - Sees current file being processed
   - Waits ~15 seconds
5. **Step 4:** Summary
   - Sees "✓ Fixed 57 files successfully!"
   - Reads statistics
   - Clicks "Re-scan Now"

---

## 🔧 Backend Implementation Details

### Python Module Structure

```python
# src/qaagent/api/routes/fix.py
"""API routes for auto-fix functionality."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from qaagent.autofix import AutoFixer
from qaagent.evidence.run_manager import RunManager

router = APIRouter(tags=["fix"])

class FixableIssueCategory(BaseModel):
    category: str
    tool: str
    file_count: int
    issue_count: int
    auto_fixable: bool
    affected_files: list[str]

class ApplyFixRequest(BaseModel):
    category: str
    tool: str
    files: list[str] | None = None

@router.get("/repositories/{repo_id}/fixable-issues")
def get_fixable_issues(repo_id: str):
    """Get summary of fixable issues by category."""
    # 1. Get latest run for repository
    # 2. Analyze findings by tool/category
    # 3. Group into fixable categories
    # 4. Return summary
    pass

@router.post("/repositories/{repo_id}/apply-fix")
def apply_fix(repo_id: str, request: ApplyFixRequest):
    """Apply fixes for a category."""
    # 1. Validate repository exists
    # 2. Get repository path
    # 3. Initialize AutoFixer
    # 4. Apply fixes based on category
    # 5. Return results
    pass
```

### Integration with Existing Code

```python
# src/qaagent/autofix.py (already exists)
# Enhancements needed:

class AutoFixer:
    def get_fixable_files(self, category: str) -> list[str]:
        """Get list of files that can be fixed for a category."""
        pass

    def get_preview(self, category: str, files: list[str] = None) -> dict:
        """Get preview of changes without applying."""
        pass

    def apply_fixes_with_progress(
        self,
        category: str,
        files: list[str] = None,
        progress_callback=None
    ) -> FixResult:
        """Apply fixes with progress reporting."""
        pass
```

---

## 🚦 Testing Plan

### Unit Tests
- [ ] Test `get_fixable_issues` endpoint
- [ ] Test `apply_fix` endpoint with mock files
- [ ] Test error handling (permission denied, tool not found)
- [ ] Test file filtering (fix specific files)

### Integration Tests
- [ ] Test full flow: get issues → apply → verify
- [ ] Test with real repository (test fixture)
- [ ] Test progress reporting
- [ ] Test WebSocket connection (Phase 3)

### E2E Tests
- [ ] Test category-level fix flow in UI
- [ ] Test file-level fix flow in UI
- [ ] Test error states (network error, tool failure)
- [ ] Test re-scan after fix

---

## 📊 Success Metrics

### Phase 1 Success:
- [ ] Users can see fixable issues on landing page
- [ ] Users can apply category-level fixes
- [ ] Fixes complete in <30 seconds for 50 files
- [ ] Success rate >95% (few errors)
- [ ] Users re-scan after fixing

### Phase 2 Success:
- [ ] Users fix individual files from risk view
- [ ] Risk cards update after fix applied
- [ ] Users prefer file-level fixes for review

### Phase 3 Success:
- [ ] New users successfully use wizard
- [ ] Users preview changes before applying
- [ ] Progress updates work smoothly
- [ ] Users understand next steps from summary

---

## ⚠️ Known Limitations & Future Work

### Current Limitations:
1. **No Git integration** - User must commit manually
2. **No test running** - Can't verify fixes didn't break tests
3. **No rollback** - User must use git to undo
4. **No conflict detection** - Doesn't check if files changed since scan
5. **Single repository** - Can't fix multiple repos at once

### Future Enhancements:
1. **Git integration:**
   - Auto-commit with generated message
   - Create feature branch for fixes
   - Show git diff in UI

2. **Test integration:**
   - Run tests after fix
   - Rollback if tests fail
   - Show test results in UI

3. **LLM-powered fixes:**
   - Generate fixes for security issues
   - Explain why fix is needed
   - Suggest alternative approaches

4. **Batch operations:**
   - Fix multiple repositories
   - Schedule fixes for later
   - Fix on CI/CD pipeline

5. **Advanced preview:**
   - Interactive diff editor
   - Allow manual edits before applying
   - Show impact on risk score

---

## 🏁 Ready to Start

**Prerequisites:**
- [x] `autofix.py` module exists
- [x] CLI `qaagent fix` command works
- [ ] Test `qaagent fix --tool all` on real project
- [ ] Verify performance (time for 50+ files)

**Next Steps:**
1. Test CLI auto-fix on SonicGrid
2. Measure performance (how long for 57 files?)
3. Start Phase 1 implementation
4. Create API endpoints
5. Build React components
6. Test with real data
7. Deploy to staging
8. Get user feedback
9. Iterate and improve

---

## Questions & Decisions

### Open Questions:
1. **Git workflow:** Should we require clean working directory?
2. **Batch size:** Fix all at once or batch in chunks?
3. **Permissions:** How to handle read-only files?
4. **Conflict resolution:** What if files changed since scan?

### Decisions Made:
- ✅ Start with Phase 1 (category-level)
- ✅ No auto-commit in Phase 1 (too risky)
- ✅ Confirmation required before applying
- ✅ Show success message with re-scan option
- ✅ WebSocket for progress (Phase 3 only)

---

**Document Version:** 1.0
**Last Updated:** 2025-10-28
**Next Review:** After Phase 1 implementation
