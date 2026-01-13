# Auto-Fix Feature Status

## Current State (2025-10-28)

### What Works ✅

1. **Basic Auto-Fix Flow**
   - User clicks "Auto-Fix" button in dashboard
   - Backend runs autopep8 on repository
   - Files are modified in place
   - Success message appears

2. **Automatic Rescan After Fixes**
   - After autopep8 completes, flake8 automatically re-runs
   - Evidence data is updated with new counts
   - Dashboard refreshes within 30 seconds showing updated numbers
   - No manual rescan needed

3. **Files Modified**
   - `src/qaagent/api/routes/fix.py:167-257` - Auto-fix endpoint with rescan
   - `src/qaagent/autofix.py` - Timeout increased to 1800 seconds (30 min)
   - Bug fix: EvidenceIDGenerator now receives run_id parameter

### What's Working But Misleading ⚠️

**The "Auto-Fix Available" card shows ALL flake8 issues, not just auto-fixable ones.**

**Example from sonicgrid:**
- Card shows: "66,610 fixable issues"
- Actually auto-fixable: ~5,800 issues (whitespace, trailing spaces, some indentation)
- Not auto-fixable: ~47,810 E501 (line too long), ~3,059 F401 (unused imports), etc.

**Current behavior:**
```
formatting
(autopep8)
66610 warning          ← MISLEADING: Most of these can't be auto-fixed
PEP 8 violations: line length, whitespace, indentation
66610 issues in 3864 files
```

## What Needs to Be Fixed 🔧

### Issue: Counting ALL flake8 issues instead of only auto-fixable ones

**Location:** `src/qaagent/api/routes/fix.py:106-117`

**Current code:**
```python
# Formatting issues (autopep8/black)
if "flake8" in tool_stats:
    stats = tool_stats["flake8"]
    categories.append(FixableCategory(
        category="formatting",
        tool="autopep8",
        file_count=len(stats["files"]),
        issue_count=stats["count"],  # ← This counts ALL flake8 issues
        auto_fixable=True,
        severity_breakdown=stats["severity_breakdown"],
        description="PEP 8 violations: line length, whitespace, indentation"
    ))
```

**Problem:**
- `stats["count"]` includes ALL flake8 findings
- Should only count issues that autopep8 can actually fix

**Solution needed:**
Filter findings to only count auto-fixable codes:
- W191 (indentation contains tabs)
- W291 (trailing whitespace)
- W292 (no newline at end of file)
- W293 (blank line contains whitespace)
- W391 (blank line at end of file)
- E101-E129 (indentation issues that autopep8 can fix)
- E201-E275 (whitespace/spacing issues)
- Some E3xx, E4xx issues

**NOT auto-fixable by autopep8:**
- E501 (line too long) - Can't always safely split
- F401 (unused imports) - Requires manual review
- F821 (undefined names) - Logic errors
- F405, F403 (import issues) - Requires manual review

### Proposed Fix

**Step 1:** Define auto-fixable codes
```python
# In src/qaagent/api/routes/fix.py
AUTOPEP8_FIXABLE_CODES = {
    # Indentation
    "E101", "E102", "E103", "E104", "E105", "E106", "E107", "E108", "E109",
    "E111", "E112", "E113", "E114", "E115", "E116", "E117", "E118", "E119",
    "E121", "E122", "E123", "E124", "E125", "E126", "E127", "E128", "E129",

    # Whitespace
    "E201", "E202", "E203", "E204",
    "E211",
    "E221", "E222", "E223", "E224", "E225", "E226", "E227", "E228",
    "E231",
    "E241", "E242",
    "E251",
    "E261", "E262", "E265", "E266",
    "E271", "E272", "E273", "E274", "E275",

    # Blank lines
    "E301", "E302", "E303", "E304", "E305", "E306",

    # Imports (limited)
    "E401", "E402",

    # Trailing whitespace
    "W291", "W292", "W293",

    # Blank line at end
    "W391",

    # Deprecated
    "W601", "W602", "W603", "W604", "W605", "W606",
}
```

**Step 2:** Filter findings in `get_fixable_issues()`
```python
# Count only auto-fixable issues
auto_fixable_findings = [
    f for f in findings
    if f.tool == "flake8" and f.code in AUTOPEP8_FIXABLE_CODES
]

if auto_fixable_findings:
    # Group by file
    files_with_fixable = set(f.file for f in auto_fixable_findings)

    categories.append(FixableCategory(
        category="formatting",
        tool="autopep8",
        file_count=len(files_with_fixable),
        issue_count=len(auto_fixable_findings),  # ← Only auto-fixable count
        auto_fixable=True,
        severity_breakdown=...,  # Calculate from auto_fixable_findings only
        description="Auto-fixable PEP 8 violations: whitespace, indentation, spacing"
    ))
```

## Test Results from sonicgrid

### Before any fixes:
- Total warnings: 113,748
- Files with issues: 4,754

### After autopep8 (first run):
- Total warnings: 66,610 (41% reduction)
- Files with issues: 3,864
- Files modified: 46

### Breakdown of remaining 66,610:
- E501 (line too long): ~47,810 (NOT auto-fixable)
- F401 (unused imports): ~3,059 (NOT auto-fixable)
- Other issues: ~15,741 (mixed - some fixable, some not)

**Estimated truly auto-fixable:** ~5,800 issues
**Currently shown as fixable:** 66,610 issues ❌

## Files Modified in This Work

1. `src/qaagent/api/routes/fix.py`
   - Added automatic rescan after fixes (lines 215-232)
   - Fixed EvidenceIDGenerator initialization (line 220)
   - Removed misleading import estimate (removed lines 119-135)
   - Import additions (lines 15-16)

2. `src/qaagent/autofix.py`
   - Increased all timeouts from 180s to 1800s (30 min)
   - Lines: 74, 186, 198, 216, 245

## Next Steps

1. **Implement accurate counting** - Filter findings to only show auto-fixable codes
2. **Update description** - Change from "PEP 8 violations: line length, whitespace, indentation" to "Auto-fixable: whitespace, indentation, spacing"
3. **Test with fresh scan** - Verify counts are accurate
4. **Consider adding tooltip** - Show breakdown of what will be fixed

## Branch

Work was done on branch: `main` in qaagent repo
Test repository: `sonicgrid` on branch `greg/auto-fix-issues`
