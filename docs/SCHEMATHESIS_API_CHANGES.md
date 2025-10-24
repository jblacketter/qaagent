# Schemathesis CLI API Changes

**Date**: 2025-10-22
**Issue**: Integration tests failing due to Schemathesis CLI breaking changes
**Schemathesis Version**: 4.3.10

## Summary of Changes

The Schemathesis CLI has undergone significant API changes. The following changes need to be applied to both `src/qaagent/cli.py` and `src/qaagent/mcp_server.py`:

## Changes Already Applied ✅

1. **Base URL**: `--base-url` → `--url`
2. **Hypothesis Deadline**: `--hypothesis-deadline=500` → Removed (no longer exists)
3. **JUnit XML**: `--junit-xml PATH` → `--report junit --report-junit-path PATH`

## Changes Still Needed ❌

### 1. Tag Filtering

**Old API**:
```bash
schemathesis run SPEC --tag TAG1 --tag TAG2
```

**New API**:
```bash
schemathesis run SPEC --include-tag TAG1 --include-tag TAG2
```

**Files to Update**:
- `src/qaagent/cli.py:290` - Change `cmd += ["--tag", t]` to `cmd += ["--include-tag", t]`
- `src/qaagent/mcp_server.py:93` - Change `cmd += ["--tag", t]` to `cmd += ["--include-tag", t]`

### 2. Operation ID Filtering

**Old API**:
```bash
schemathesis run SPEC --operation-id OP1 --operation-id OP2
```

**New API**:
```bash
schemathesis run SPEC --include-operation-id OP1 --include-operation-id OP2
```

**Files to Update**:
- `src/qaagent/cli.py` - Look for `--operation-id` usage
- `src/qaagent/mcp_server.py` - Look for `--operation-id` usage

### 3. Endpoint Pattern Filtering

**Old API**:
```bash
schemathesis run SPEC --endpoint PATTERN
```

**New API**:
```bash
schemathesis run SPEC --include-path-regex PATTERN
```

**Files to Update**:
- `src/qaagent/cli.py` - Change `--endpoint` to `--include-path-regex`
- `src/qaagent/mcp_server.py` - Change `--endpoint` to `--include-path-regex`

## Current CLI Code (Lines to Fix)

### src/qaagent/cli.py

Around line 288-298:
```python
# Filters
if tag:
    for t in tag:
        cmd += ["--tag", t]  # ❌ Change to --include-tag
if operation_id:
    for op in operation_id:
        cmd += ["--operation-id", op]  # ❌ Change to --include-operation-id
if endpoint_pattern:
    cmd += ["--endpoint", endpoint_pattern]  # ❌ Change to --include-path-regex
```

### src/qaagent/mcp_server.py

Around line 91-99:
```python
# Filters
if args.tag:
    for t in args.tag:
        cmd += ["--tag", t]  # ❌ Change to --include-tag
if args.operation_id:
    for oid in args.operation_id:
        cmd += ["--operation-id", oid]  # ❌ Change to --include-operation-id
if args.endpoint_pattern:
    cmd += ["--endpoint", args.endpoint_pattern]  # ❌ Change to --include-path-regex
```

## Testing Integration Tests

After making these changes, the integration tests should pass:

```bash
pytest tests/integration/test_api_workflow.py -v
```

## Additional Issue: Async Tests

The MCP server tests need `pytest-asyncio`:

```bash
pip install pytest-asyncio
```

Or add to `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = [
    "pytest-asyncio>=0.23",
    # ... other dev deps
]
```

## Verification Commands

Test the changes with:

```bash
# Test with tag filtering
qaagent schemathesis-run \
  --openapi examples/petstore-api/openapi.yaml \
  --base-url http://localhost:8765 \
  --tag pets

# Test with operation-id filtering
qaagent schemathesis-run \
  --openapi examples/petstore-api/openapi.yaml \
  --base-url http://localhost:8765 \
  --operation-id listPets

# Test with path pattern
qaagent schemathesis-run \
  --openapi examples/petstore-api/openapi.yaml \
  --base-url http://localhost:8765 \
  --endpoint-pattern "^/pets"
```

## Reference

Schemathesis CLI help:
```bash
schemathesis run --help
```

Key section:
```
Filtering options:
  Filter operations by path, method, name, tag, or operation-id using:
  --include-TYPE VALUE          Match operations with exact VALUE
  --include-TYPE-regex PATTERN  Match operations using regular expression
  --exclude-TYPE VALUE          Exclude operations with exact VALUE
  --exclude-TYPE-regex PATTERN  Exclude operations using regular expression
```

Where TYPE can be: `path`, `method`, `name`, `tag`, `operation-id`
