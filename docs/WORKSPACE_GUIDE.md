# QA Agent Workspace Guide

**Version:** 1.0.0
**Date:** 2025-10-24

## Overview

The QA Agent workspace provides a **staging area** for generated artifacts (OpenAPI specs, tests, reports) before they're applied to your target project. This enables a safe, review-and-approve workflow without cluttering your project repository.

## Why Use Workspace?

### Problems Solved

1. **Non-Invasive:** Don't modify target project until you approve
2. **Path Resolution:** Generated files always in known location
3. **Easy Review:** Examine generated code before copying
4. **Safe Iteration:** Regenerate without polluting target
5. **Clean Separation:** Keep generated artifacts separate from source

### Before Workspace

```bash
# Generated directly in target project
cd /path/to/project
qaagent generate openapi --auto-discover --out openapi.json

# File created: /path/to/project/openapi.json
# Problem: Immediately in git working tree!
```

### After Workspace

```bash
# Generated in workspace (default behavior)
qaagent generate openapi --auto-discover

# File created: ~/.qaagent/workspace/myproject/openapi.json
# Benefits: Not in git, easy to find, can review first
```

## Workspace Structure

```
~/.qaagent/
  repos/              # Cloned repositories (existing)
  workspace/          # Generated artifacts (NEW)
    <target-name>/
      openapi.json    # Generated OpenAPI specs
      openapi.yaml
      tests/
        unit/         # Generated unit tests
        behave/       # Generated BDD scenarios
      reports/        # Test reports
      fixtures/       # Test data fixtures
```

## Commands

### Generate Files (uses workspace by default)

```bash
# Generate OpenAPI spec (workspace by default)
qaagent generate openapi --auto-discover

# Generate in workspace (explicit)
qaagent generate openapi --auto-discover --workspace

# Generate directly in target (opt-out)
qaagent generate openapi --auto-discover --no-workspace

# Generate unit tests (will support workspace soon)
qaagent generate unit-tests --out tests/unit
```

### View Workspace

```bash
# Show workspace for active target
qaagent workspace show

# Show workspace for specific target
qaagent workspace show sonicgrid

# List all workspaces
qaagent workspace list
```

**Example Output:**

```
Workspace for 'sonicgrid':
  Path: /Users/you/.qaagent/workspace/sonicgrid

Generated Files:
  ✓ openapi.json (222.4 KB)
  ✓ tests/unit/ (154 files)
  ✓ fixtures/ (3 files)
```

### Apply Files to Target

```bash
# Apply all files to target project
qaagent workspace apply

# Apply only OpenAPI spec
qaagent workspace apply --pattern "openapi.*"

# Apply only tests
qaagent workspace apply --pattern "tests/*"

# Dry run (show what would be copied)
qaagent workspace apply --dry-run

# Apply to specific target
qaagent workspace apply sonicgrid
```

**Example Output:**

```
✓ Copied 3 files to target:
  openapi.json → openapi.json
  test_users_api.py → tests/unit/test_users_api.py
  conftest.py → tests/unit/conftest.py
```

### Clean Workspace

```bash
# Clean workspace for active target
qaagent workspace clean

# Clean specific target
qaagent workspace clean sonicgrid

# Clean all workspaces
qaagent workspace clean --all

# Skip confirmation
qaagent workspace clean --force
```

## Workflow Examples

### Example 1: Generate and Review OpenAPI Spec

```bash
# 1. Generate OpenAPI spec (goes to workspace)
qaagent generate openapi --auto-discover

# Output:
# ✓ OpenAPI spec generated → ~/.qaagent/workspace/myproject/openapi.json
#   → Files in workspace (not in target project yet)
#   → Use 'qaagent workspace apply' to copy to target

# 2. Review the generated spec
cat ~/.qaagent/workspace/myproject/openapi.json
# Or open in editor/Swagger UI

# 3. View workspace contents
qaagent workspace show

# 4. If satisfied, apply to target project
qaagent workspace apply --pattern "openapi.*"

# 5. Generated file now in target project
ls -la openapi.json  # In project root
git add openapi.json
git commit -m "Add auto-generated OpenAPI spec"
```

### Example 2: Iterative Test Generation

```bash
# 1. Generate tests (first attempt)
qaagent generate unit-tests

# 2. Review generated tests
qaagent workspace show
cat ~/.qaagent/workspace/myproject/tests/unit/test_api.py

# 3. Not satisfied? Regenerate with different options
qaagent workspace clean --force
qaagent generate unit-tests --enhanced

# 4. Review again
qaagent workspace show

# 5. Satisfied? Apply to project
qaagent workspace apply --pattern "tests/*"
```

### Example 3: Use Workspace Files Directly

```bash
# 1. Generate OpenAPI spec
qaagent generate openapi --auto-discover

# 2. Run schemathesis against workspace file (automatic)
qaagent schemathesis-run --base-url https://api.example.com

# Output:
# Using OpenAPI spec from workspace: ~/.qaagent/workspace/myproject/openapi.json
# Running Schemathesis tests...

# 3. Generate tests from workspace spec (automatic)
qaagent generate unit-tests

# 4. Only copy final artifacts when ready
qaagent workspace apply
```

### Example 4: Multiple Targets

```bash
# Work with target A
qaagent use project-a
qaagent generate openapi --auto-discover
qaagent workspace show

# Switch to target B
qaagent use project-b
qaagent generate openapi --auto-discover
qaagent workspace show

# List all workspaces
qaagent workspace list

# Output:
# Workspaces (2 targets):
#   • project-a (3 files)
#   • project-b (5 files)

# Clean old workspaces
qaagent workspace clean project-a --force
```

## Integration with Commands

### Commands That Auto-Use Workspace

The following commands automatically look for files in the workspace:

1. **`qaagent schemathesis-run`**
   - Automatically uses `~/.qaagent/workspace/<target>/openapi.json` if no `--openapi` specified
   - Falls back to config or detection if not found

2. **`qaagent generate unit-tests`**
   - Can read OpenAPI spec from workspace
   - (Future: Will write tests to workspace by default)

3. **`qaagent generate test-data`**
   - Can read routes from workspace OpenAPI spec
   - (Future: Will write fixtures to workspace)

### Command Options

Most generate commands support `--workspace` / `--no-workspace`:

```bash
# Use workspace (default)
qaagent generate openapi --auto-discover

# Use workspace (explicit)
qaagent generate openapi --auto-discover --workspace

# Write directly to target project
qaagent generate openapi --auto-discover --no-workspace --out openapi.json
```

## Best Practices

### 1. Always Review Before Applying

```bash
# Generate
qaagent generate openapi --auto-discover

# Review
qaagent workspace show
cat ~/.qaagent/workspace/<target>/openapi.json

# Apply only when satisfied
qaagent workspace apply
```

### 2. Use Patterns for Selective Apply

```bash
# Apply only specs
qaagent workspace apply --pattern "openapi.*"

# Apply only tests
qaagent workspace apply --pattern "tests/*"

# Apply only fixtures
qaagent workspace apply --pattern "fixtures/*"
```

### 3. Use Dry Run for Safety

```bash
# See what would be copied
qaagent workspace apply --dry-run

# Output:
# Would copy 3 files:
#   openapi.json → openapi.json
#   test_api.py → tests/unit/test_api.py
#   conftest.py → tests/unit/conftest.py
```

### 4. Clean After Applying

```bash
# Apply files
qaagent workspace apply

# Clean workspace
qaagent workspace clean --force

# Or keep for reference/regeneration
```

### 5. Commit Workspace Path to Docs

Add to your project's documentation:

```markdown
## Generated Files

OpenAPI specs and tests are generated using QA Agent.
Generated files are staged in: `~/.qaagent/workspace/myproject/`

To regenerate:
\`\`\`bash
qaagent generate openapi --auto-discover
qaagent workspace show
qaagent workspace apply --pattern "openapi.*"
\`\`\`
```

## Troubleshooting

### Issue: Can't Find Workspace Files

**Problem:**
```bash
qaagent schemathesis-run --base-url https://api.example.com
# Error: OpenAPI spec not found
```

**Solution:**
```bash
# Check workspace exists
qaagent workspace show

# If empty, generate first
qaagent generate openapi --auto-discover

# Then retry
qaagent schemathesis-run --base-url https://api.example.com
```

### Issue: Files Not Applying

**Problem:**
```bash
qaagent workspace apply
# No files matching '*' in workspace
```

**Solution:**
```bash
# Check what's in workspace
qaagent workspace show

# Generate files first
qaagent generate openapi --auto-discover
qaagent generate unit-tests

# Then apply
qaagent workspace apply
```

### Issue: Wrong Target

**Problem:**
Files applying to wrong project.

**Solution:**
```bash
# Check active target
qaagent targets list

# Switch if needed
qaagent use correct-target

# Or specify target explicitly
qaagent workspace apply correct-target
```

## Advanced Usage

### Custom Workspace Location

```python
from qaagent.workspace import Workspace

# Use custom base directory
ws = Workspace(base_dir="/custom/path")
workspace_path = ws.get_target_workspace("myproject")
```

### Programmatic Access

```python
from qaagent.workspace import Workspace

ws = Workspace()

# Get paths
openapi_path = ws.get_openapi_path("myproject", format="json")
tests_dir = ws.get_tests_dir("myproject", test_type="unit")
reports_dir = ws.get_reports_dir("myproject")

# Get workspace info
info = ws.get_workspace_info("myproject")
print(f"Workspace: {info['path']}")
print(f"Files: {info['files']}")

# Copy to target
copied = ws.copy_to_target(
    target_name="myproject",
    target_path="/path/to/project",
    file_pattern="openapi.*",
    dry_run=False
)
```

## Migration Guide

### Migrating Existing Workflows

**Old Workflow:**
```bash
cd /path/to/project
qaagent generate openapi --auto-discover --out openapi.json
git add openapi.json
```

**New Workflow (Recommended):**
```bash
# Generate goes to workspace automatically
qaagent generate openapi --auto-discover

# Review
qaagent workspace show

# Apply when ready
qaagent workspace apply --pattern "openapi.*"
cd /path/to/project
git add openapi.json
```

**Old Workflow (Direct):**
```bash
qaagent generate openapi --auto-discover --no-workspace --out openapi.json
```

## FAQ

**Q: Where is the workspace located?**
A: `~/.qaagent/workspace/<target-name>/`

**Q: Can I disable workspace?**
A: Yes, use `--no-workspace` flag: `qaagent generate openapi --no-workspace`

**Q: Do all commands use workspace?**
A: Currently only `generate openapi`. More commands coming soon.

**Q: How do I clean up workspace?**
A: `qaagent workspace clean` or `qaagent workspace clean --all`

**Q: Can I commit workspace files to git?**
A: No, workspace is outside your project. Use `workspace apply` to copy files to project first.

**Q: What happens if I delete workspace?**
A: Just regenerate: `qaagent generate openapi --auto-discover`

**Q: Can I customize workspace location?**
A: Yes, but requires code changes. Default `~/.qaagent/workspace/` is recommended.

## See Also

- [README.md](../README.md) - Main documentation
- [Week 3 Validation Report](WEEK3_FINAL_VALIDATION_REPORT.md) - Feature delivery report
- [OpenAPI Generator](../src/qaagent/openapi_gen/) - OpenAPI generation code
- [Workspace Manager](../src/qaagent/workspace.py) - Workspace implementation

---

**Questions or Issues?**
Open an issue: https://github.com/anthropics/qaagent/issues
