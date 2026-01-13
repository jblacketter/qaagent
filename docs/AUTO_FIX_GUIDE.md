# QA Agent Auto-Fix Guide

## Overview

QA Agent now includes powerful auto-fix capabilities to automatically resolve common code quality issues found during scans.

## What's New

### 1. Fixed Bandit Security Scanner Timeout

**Problem:** Bandit was timing out on large projects (like SonicGrid) after 180 seconds.

**Solution:**
- Increased timeout to 600 seconds (10 minutes)
- Added smart directory filtering to skip:
  - `node_modules/` - JavaScript dependencies
  - `.venv/`, `venv/` - Python virtual environments
  - `.git/` - Git metadata
  - `dist/`, `build/` - Build artifacts
  - `__pycache__/`, `.next/`, `.pytest_cache/` - Cache directories

**Result:** Bandit now completes successfully on large codebases.

**File:** `src/qaagent/collectors/bandit.py`

### 2. New `qaagent fix` Command

Auto-fix common issues with a single command!

#### Usage

```bash
# Fix formatting issues in active target
qaagent fix

# Fix specific target
qaagent fix sonicgrid

# Use specific tool
qaagent fix --tool autopep8    # PEP 8 formatting
qaagent fix --tool black       # Black formatter
qaagent fix --tool isort       # Import sorting
qaagent fix --tool all         # Run all fixers

# Dry run (see what would be fixed)
qaagent fix --dry-run
```

#### What It Fixes

**Formatting Issues (autopep8/black):**
- Line length violations (E501)
- Trailing whitespace (W293)
- Missing newlines at end of file (W292)
- Indentation issues
- Whitespace around operators

**Import Issues (isort):**
- Unsorted imports
- Import grouping (stdlib, third-party, local)
- Consistent import style

#### Installation

Install formatting tools:

```bash
# Install all recommended tools
pip install autopep8 black isort

# Or individually
pip install autopep8  # PEP 8 auto-formatter
pip install black     # Opinionated formatter
pip install isort     # Import sorter
```

### 3. Enhanced Recommendations

Recommendations now include **actionable commands** instead of generic advice!

#### Before (Generic)
```
Focus on python-tests/ui/pages/mixins/navigable_mixin.py (critical risk)
Risk score 100.0 (band P0). Factors: security=162.0, coverage=0.0, churn=0.0
```

#### After (Actionable)
```
Focus on python-tests/ui/pages/mixins/navigable_mixin.py (critical risk)
Risk score 100.0 (band P0). Factors: security=162.0, coverage=0.0, churn=0.0

Recommended Actions:
  • Review security issues: Check evidence for bandit/security findings
  • Manual review required for: python-tests/ui/pages/mixins/navigable_mixin.py
  • Auto-fix formatting: qaagent fix --tool all
  • View detailed issues: grep 'navigable_mixin.py' ~/.qaagent/runs/*/evidence/quality.jsonl
  • PRIORITY: Address this critical risk immediately
```

## Complete Workflow

### 1. Scan Your Project

```bash
# Scan active target
qaagent analyze routes

# Or analyze specific target
cd /path/to/your/project
qaagent targets add myproject .
qaagent use myproject
qaagent analyze routes
```

### 2. View Results

```bash
# Open web dashboard
qaagent web-ui

# Or generate HTML dashboard
qaagent dashboard
open ~/.qaagent/workspace/myproject/reports/dashboard.html
```

### 3. Auto-Fix Issues

```bash
# Fix all formatting issues
qaagent fix --tool all

# Or fix specific issues
qaagent fix --tool autopep8  # Just formatting
qaagent fix --tool isort     # Just imports
```

### 4. Verify Fixes

```bash
# Re-scan to see improvements
qaagent analyze routes

# Compare results in dashboard
qaagent web-ui
# Navigate to "Runs" tab to see before/after comparison
```

## API Integration

The auto-fix module can be used programmatically:

```python
from pathlib import Path
from qaagent.autofix import AutoFixer

# Initialize fixer
fixer = AutoFixer(Path("/path/to/project"))

# Fix formatting
result = fixer.fix_formatting("autopep8")
print(f"Modified {result.files_modified} files")

# Fix imports
result = fixer.fix_imports()
print(f"Success: {result.success}")

# Generate fix commands from findings
findings = [...]  # List of finding dicts
commands = fixer.generate_fix_commands(findings)
for cmd in commands:
    print(f"{cmd['description']}: {cmd['command']}")
```

## Configuration

### Bandit Skip Patterns

Customize which directories to skip:

```python
from qaagent.collectors.bandit import BanditCollector, BanditConfig

config = BanditConfig(
    timeout=600,
    skip_patterns=[
        "*/node_modules/*",
        "*/custom_dir/*",
    ]
)

collector = BanditCollector(config)
```

## Troubleshooting

### "Tool not installed" Error

If you see errors like "autopep8 not installed":

```bash
# Install missing tools
pip install autopep8 black isort
```

### Bandit Still Timing Out

For extremely large projects (>100k LOC):

1. Add more skip patterns
2. Increase timeout further
3. Run bandit on specific subdirectories only

### Fixes Not Applied

Check file permissions:

```bash
# Ensure files are writable
chmod +w -R /path/to/project
```

## Best Practices

1. **Always run in a clean git state**
   ```bash
   git status  # Ensure no uncommitted changes
   qaagent fix --tool all
   git diff    # Review changes
   git commit -am "Auto-fix formatting issues"
   ```

2. **Use dry-run first**
   ```bash
   qaagent fix --dry-run  # See what will change
   qaagent fix            # Apply fixes
   ```

3. **Run tests after fixing**
   ```bash
   qaagent fix --tool all
   pytest  # Or your test command
   ```

4. **Fix incrementally on large codebases**
   ```bash
   # Fix one tool at a time
   qaagent fix --tool autopep8
   # Review, test, commit
   qaagent fix --tool isort
   # Review, test, commit
   ```

## Next Steps

After implementing auto-fix, consider:

1. **Add pre-commit hooks** to auto-fix on commit
   ```bash
   pip install pre-commit
   # Add .pre-commit-config.yaml
   ```

2. **CI/CD Integration** - Auto-fix in PR checks
   ```yaml
   # .github/workflows/qa.yml
   - name: Auto-fix issues
     run: |
       qaagent fix --tool all
       git diff --exit-code || exit 1
   ```

3. **LLM-powered fixes** (coming soon)
   - Context-aware security fixes
   - Generate test cases for untested code
   - Explain *why* a fix is needed

## Files Modified

- `src/qaagent/collectors/bandit.py` - Fixed timeout, added smart filtering
- `src/qaagent/autofix.py` - New auto-fix module
- `src/qaagent/cli.py` - Added `qaagent fix` command
- `src/qaagent/analyzers/recommender.py` - Enhanced recommendations with actionable commands

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/qaagent/issues
- Documentation: `docs/`
