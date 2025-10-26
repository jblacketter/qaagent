# qaagent API Specification

**Version:** 1.0.0-mvp
**Last Updated:** 2025-10-24
**Protocol:** REST over HTTP
**Format:** JSON
**Server:** FastAPI (read-only)

---

## Overview

The qaagent API provides read-only access to analysis results stored in the evidence store. The API is designed to:

- Serve data to the interactive dashboard
- Enable programmatic access to findings and metrics
- Support future integrations (CI/CD, IDE plugins, etc.)

**Key Principles:**
- **Read-only**: No mutations via API (analysis runs via CLI only)
- **Local-only**: No authentication/authorization (assumes local access)
- **Stateless**: No sessions; each request is independent
- **Versioned**: API version in path for future compatibility

---

## Base Configuration

### Development Server
```bash
qaagent api --host 127.0.0.1 --port 8765
```

**Defaults:**
- Host: `127.0.0.1` (localhost only, no external access)
- Port: `8765`
- Base Path: `/api/v1`

### CORS Policy
- **Disabled by default** (local-only access)
- If enabled via `--allow-cors`: only `http://localhost:*` origins

### Error Response Format
All errors follow consistent schema:
```json
{
  "error": {
    "code": "RUN_NOT_FOUND",
    "message": "Run with ID '20251024_193012Z' does not exist",
    "details": {
      "run_id": "20251024_193012Z",
      "available_runs": ["20251024_120000Z", "20251023_180000Z"]
    }
  }
}
```

**HTTP Status Codes:**
- `200 OK`: Successful request
- `400 Bad Request`: Invalid query parameters
- `404 Not Found`: Run or resource not found
- `500 Internal Server Error`: Unexpected server error

---

## Endpoints

### Run Management

#### `GET /api/v1/runs`
List all available analysis runs.

**Query Parameters:**
- `limit` (int, optional): Max runs to return (default: 50, max: 200)
- `offset` (int, optional): Pagination offset (default: 0)

**Response:**
```json
{
  "runs": [
    {
      "run_id": "20251024_193012Z",
      "created_at": "2025-10-24T19:30:12Z",
      "target": {
        "name": "sonicgrid",
        "path": "/Users/jack/projects/sonicgrid"
      },
      "counts": {
        "findings": 42,
        "risks": 10,
        "tests": 128
      }
    }
  ],
  "total": 15,
  "limit": 50,
  "offset": 0
}
```

#### `GET /api/v1/runs/{run_id}`
Get detailed manifest for a specific run.

**Path Parameters:**
- `run_id` (string): Run identifier (e.g., `20251024_193012Z` or `latest`)

**Response:** Returns complete `manifest.json` content (see EVIDENCE_STORE_SPEC)

**Special Values:**
- `latest`: Returns most recent run by timestamp

---

### Findings

#### `GET /api/v1/runs/{run_id}/findings`
Retrieve quality findings (lint, security, dependency issues).

**Query Parameters:**
- `tool` (string, optional): Filter by tool (e.g., `flake8`, `bandit`)
- `severity` (string, optional): Filter by severity (`info`, `warning`, `high`, `critical`)
- `file` (string, optional): Filter by file path (supports wildcards: `src/auth/*`)
- `limit` (int, optional): Max findings to return (default: 100, max: 1000)
- `offset` (int, optional): Pagination offset (default: 0)

**Response:**
```json
{
  "findings": [
    {
      "evidence_id": "FND-20251024-0001",
      "tool": "flake8",
      "severity": "warning",
      "code": "E302",
      "message": "expected 2 blank lines, found 1",
      "file": "src/app/main.py",
      "line": 57,
      "column": 1,
      "tags": ["style", "lint"],
      "confidence": 0.8,
      "collected_at": "2025-10-24T19:30:13Z"
    }
  ],
  "total": 42,
  "limit": 100,
  "offset": 0,
  "filters": {
    "tool": "flake8",
    "severity": null
  }
}
```

---

### Risk Scores

#### `GET /api/v1/runs/{run_id}/risks`
Get aggregated risk scores (Sprint 2+).

**Query Parameters:**
- `band` (string, optional): Filter by priority band (`P0`, `P1`, `P2`, `P3`)
- `category` (string, optional): Filter by category (`security`, `coverage`, `churn`)
- `min_score` (float, optional): Minimum risk score (0-100)
- `limit` (int, optional): Max risks to return (default: 50, max: 200)

**Response:**
```json
{
  "risks": [
    {
      "risk_id": "RSK-20251024-0003",
      "category": "security",
      "score": 78.2,
      "band": "P1",
      "confidence": 0.62,
      "summary": "High-churn auth module with failing bandit rule B101",
      "recommendation": "Add unit tests around auth handlers and fix hard-coded secrets.",
      "linked_cujs": ["auth_login"],
      "related_evidence": ["FND-20251024-0007", "CHN-20251024-0002"]
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

---

### Coverage Metrics

#### `GET /api/v1/runs/{run_id}/coverage`
Get code coverage metrics.

**Query Parameters:**
- `component` (string, optional): Filter by component path
- `cuj` (string, optional): Filter by linked CUJ ID (from cuj.yaml)
- `type` (string, optional): Coverage type (`line`, `branch`, `function`)

**Response:**
```json
{
  "coverage": [
    {
      "coverage_id": "COV-20251024-0012",
      "type": "line",
      "component": "src/auth/",
      "value": 0.62,
      "total_statements": 320,
      "covered_statements": 198,
      "sources": ["coverage.xml"],
      "linked_cujs": ["auth_login"],
      "collected_at": "2025-10-24T19:30:20Z"
    }
  ],
  "summary": {
    "overall_coverage": 0.64,
    "total_lines": 8450,
    "covered_lines": 5408
  }
}
```

#### `GET /api/v1/runs/{run_id}/coverage/summary`
Get aggregated coverage summary by CUJ.

**Response:**
```json
{
  "by_cuj": {
    "auth_login": {
      "coverage": 0.62,
      "target": 0.80,
      "status": "below_target",
      "components": ["src/auth/", "src/api/auth/"]
    },
    "dataset_upload": {
      "coverage": 0.71,
      "target": 0.70,
      "status": "meets_target",
      "components": ["src/datasets/", "src/storage/"]
    }
  },
  "overall": 0.64
}
```

---

### Test Inventory

#### `GET /api/v1/runs/{run_id}/tests`
Get test inventory.

**Query Parameters:**
- `kind` (string, optional): Filter by test kind (`unit`, `integration`, `e2e`)
- `status` (string, optional): Filter by status (`existing`, `generated`, `missing`)
- `tag` (string, optional): Filter by tag (typically CUJ ID)

**Response:**
```json
{
  "tests": [
    {
      "test_id": "TST-20251024-0045",
      "kind": "integration",
      "name": "tests/integration/test_login.py::test_valid_credentials",
      "status": "existing",
      "last_run": "2025-10-23T04:11:00Z",
      "evidence_refs": ["COV-20251024-0012"],
      "tags": ["auth_login"]
    }
  ],
  "summary": {
    "total": 128,
    "by_kind": {
      "unit": 85,
      "integration": 32,
      "e2e": 11
    },
    "by_status": {
      "existing": 128,
      "generated": 0,
      "missing": 0
    }
  }
}
```

---

### API Surface

#### `GET /api/v1/runs/{run_id}/apis`
Get API endpoint inventory (Sprint 2+).

**Query Parameters:**
- `method` (string, optional): Filter by HTTP method
- `auth_required` (bool, optional): Filter by auth requirement
- `tag` (string, optional): Filter by tag

**Response:**
```json
{
  "apis": [
    {
      "api_id": "API-20251024-0109",
      "method": "POST",
      "path": "/api/auth/login",
      "auth_required": true,
      "tags": ["auth"],
      "source": "openapi",
      "evidence_refs": ["RSK-20251024-0003"],
      "confidence": 0.95
    }
  ],
  "summary": {
    "total": 42,
    "by_method": {
      "GET": 22,
      "POST": 12,
      "PUT": 5,
      "DELETE": 3
    },
    "public_endpoints": 8,
    "authenticated_endpoints": 34
  }
}
```

---

### Git Churn

#### `GET /api/v1/runs/{run_id}/churn`
Get git churn metrics (Sprint 1).

**Query Parameters:**
- `path` (string, optional): Filter by file/directory path
- `min_commits` (int, optional): Minimum commit count
- `limit` (int, optional): Max records to return (default: 100)

**Response:**
```json
{
  "churn": [
    {
      "evidence_id": "CHN-20251024-0002",
      "path": "src/auth/session.py",
      "window": "90d",
      "commits": 14,
      "lines_added": 420,
      "lines_deleted": 318,
      "contributors": 6,
      "last_commit_at": "2025-10-20T12:45:09Z"
    }
  ],
  "summary": {
    "total_files": 187,
    "total_commits": 342,
    "total_contributors": 8,
    "window": "90d"
  }
}
```

---

### Health & Meta

#### `GET /api/v1/health`
API health check.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0-mvp",
  "evidence_store": "/Users/jack/.qaagent/runs",
  "run_count": 15,
  "latest_run": "20251024_193012Z"
}
```

#### `GET /api/v1/config`
Get current risk configuration.

**Response:** Returns processed `risk_config.yaml` content with defaults applied.

---

## Pagination

All list endpoints support pagination via `limit` and `offset`:

```
GET /api/v1/runs/{run_id}/findings?limit=50&offset=100
```

**Pagination Response Headers:**
```
X-Total-Count: 342
X-Limit: 50
X-Offset: 100
Link: </api/v1/runs/latest/findings?limit=50&offset=150>; rel="next"
```

---

## Filtering

### Wildcard Patterns
File path filters support glob patterns:
- `src/auth/*` - all files in src/auth/
- `**/*.py` - all Python files
- `src/*/test_*.py` - test files in immediate subdirs

### Multi-value Filters
Some filters accept comma-separated values:
```
GET /api/v1/runs/latest/findings?severity=high,critical
```

---

## Future Enhancements (Post-MVP)

- **WebSocket endpoint** for real-time analysis progress
- **Export formats**: `/export?format=csv` for findings
- **Diff endpoint**: `/api/v1/diff/{run_id_a}/{run_id_b}` to compare runs
- **Recommendations endpoint**: `/api/v1/runs/{run_id}/recommendations`
- **Authentication**: Optional API key for remote access (if enabled)

---

## Implementation Notes

### FastAPI Structure
```python
# src/qaagent/api/main.py
from fastapi import FastAPI, Query, Path, HTTPException
from qaagent.evidence import RunManager

app = FastAPI(title="qaagent", version="1.0.0-mvp")
run_manager = RunManager()

@app.get("/api/v1/runs")
async def list_runs(limit: int = Query(50, le=200), offset: int = Query(0, ge=0)):
    # Implementation
    pass
```

### Evidence Store Access
API reads from evidence store via `RunManager`:
```python
class RunManager:
    def list_runs(self) -> list[RunMetadata]: ...
    def load_manifest(self, run_id: str) -> Manifest: ...
    def query_findings(self, run_id: str, filters: FindingFilters) -> list[Finding]: ...
```

### Caching Strategy
- **Manifest files**: Cache in memory, invalidate on new runs
- **JSONL data**: Stream from disk, no caching (files can be large)
- **Summary stats**: Compute on-demand, cache for 60s

---

## Testing Strategy

### Unit Tests
- Mock RunManager
- Test query parameter validation
- Test pagination logic
- Test filter application

### Integration Tests
- Start API server against test fixtures
- Make actual HTTP requests
- Validate response schemas
- Test error conditions

### Example Test
```python
def test_list_runs_pagination(client):
    response = client.get("/api/v1/runs?limit=10&offset=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["runs"]) <= 10
    assert data["offset"] == 5
```

---

## Security Considerations

### Local-Only Binding
- Default to `127.0.0.1` (not `0.0.0.0`)
- Warn if user binds to external interface

### Path Traversal Prevention
- Validate `run_id` against allowlist pattern: `[0-9]{8}_[0-9]{6}Z`
- Reject `../` in file path filters

### Resource Limits
- Max response size: 10MB (configurable)
- Max query complexity: prevent wildcard explosions

### No Secret Exposure
- Never return raw tool output that might contain env vars
- Evidence store sanitization happens during write, not read

---

**Status:** Draft for review before Sprint 2 implementation
**Next Steps:** User/Codex sign-off, then implementation in Sprint 2
