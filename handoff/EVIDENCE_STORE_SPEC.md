# Evidence Store Spec

## Purpose
Provide a deterministic, local-only persistence layer for analysis artifacts so downstream services (API, dashboard, AI summaries) consume the same normalized data. Every `qaagent analyze` run produces a timestamped folder under `~/.qaagent/runs/<run_id>/` containing machine-readable JSON (mandatory) and optional SQLite mirrors.

## Directory Layout
```
~/.qaagent/runs/
  <YYYYMMDD_HHMMSSZ>/            # run_id (UTC timestamp + optional suffix)
    manifest.json                # top-level metadata + index of evidence files
    evidence/
      findings.jsonl             # one Finding record per line
      risks.jsonl                # RiskScore aggregation output
      coverage.jsonl             # Coverage metrics per component / CUJ
      tests.jsonl                # Test inventory (unit/integration/e2e)
      quality.jsonl              # Raw tool findings (flake8/pylint/bandit/pip-audit)
      churn.jsonl                # Git churn/complexity signals
      apis.jsonl                 # API surface inventory (if available)
    artifacts/
      flake8.log
      pylint.json
      bandit.json
      pip_audit.json
      coverage.xml
      lcov.info
      git_shortstat.txt
```
- JSONL is preferred for append-friendly streaming. Each record carries an `evidence_id` for cross-reference.
- If SQLite is enabled (`qaagent analyze --sqlite`), a mirrored `run.db` lives alongside `manifest.json` following the same schema (`findings`, `risks`, `coverage`, etc.).

## Manifest Schema (`manifest.json`)
```json
{
  "run_id": "20251024_193012Z",
  "created_at": "2025-10-24T19:30:12Z",
  "target": {
    "name": "sonicgrid",
    "path": "/Users/jack/.../sonicgrid",
    "git": {"commit": "abc123", "branch": "main"}
  },
  "tools": {
    "flake8": {"version": "6.1.0", "executed": true, "exit_code": 0},
    "pylint": {"version": "3.2.0", "executed": true, "exit_code": 0},
    "bandit": {"version": "1.7.9", "executed": true, "exit_code": 0},
    "pip_audit": {"version": "2.7.3", "executed": true, "exit_code": 0},
    "coverage": {"source": "coverage.xml", "found": true},
    "git": {"source": "git", "window": "90d"}
  },
  "counts": {
    "findings": 42,
    "risks": 10,
    "tests": 128,
    "coverage_components": 14
  },
  "evidence_files": {
    "findings": "evidence/findings.jsonl",
    "risks": "evidence/risks.jsonl",
    "coverage": "evidence/coverage.jsonl",
    "tests": "evidence/tests.jsonl",
    "quality": "evidence/quality.jsonl",
    "churn": "evidence/churn.jsonl",
    "apis": "evidence/apis.jsonl"
  }
}
```

## Core Record Types
### Finding (quality.jsonl)
```
{
  "evidence_id": "FND-20251024-0001",
  "tool": "flake8",
  "severity": "warning",
  "code": "E302",
  "message": "expected 2 blank lines, found 1",
  "file": "src/app/main.py",
  "line": 57,
  "column": 1,
  "link": null,
  "confidence": 0.8,
  "tags": ["style", "lint"],
  "collected_at": "2025-10-24T19:30:13Z"
}
```
- `tool` must match manifest entry. `confidence` defaults per tool (lint=0.8, security=0.7, dependency=0.9 unless overridden).

### RiskScore (risks.jsonl)
```
{
  "risk_id": "RSK-20251024-0003",
  "related_evidence": ["FND-20251024-0007", "CHN-20251024-0002"],
  "category": "security",
  "score": 78.2,
  "band": "P1",
  "confidence": 0.62,
  "summary": "High-churn auth module with failing bandit rule B101",
  "recommendation": "Add unit tests around auth handlers and fix hard-coded secrets.",
  "linked_cujs": ["auth_login"],
  "metadata": {
    "weights": {"security": 3.0, "churn": 2.0},
    "normalized_inputs": {"bandit_score": 0.9, "churn": 0.7}
  }
}
```
- `band` computed via `risk_config.yaml.prioritization` bands.
- `related_evidence` stores evidence IDs for traceability.

### CoverageMetric (coverage.jsonl)
```
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
```
- `linked_cujs` derived from `cuj.yaml` component mapping.

### TestInventory (tests.jsonl)
```
{
  "test_id": "TST-20251024-0045",
  "kind": "integration",
  "name": "tests/integration/test_login.py::test_valid_credentials",
  "status": "existing",
  "last_run": "2025-10-23T04:11:00Z",
  "evidence_refs": ["COV-20251024-0012"],
  "tags": ["auth_login"]
}
```
- `status` enumerates `existing|generated|missing`. Generated tests reference workspace outputs.

### Git Churn Signal (churn.jsonl)
```
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
```
- Derived from read-only `git log` and `git diff --stat`. No repo modifications permitted.

### API Surface (apis.jsonl)
```
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
```

## Identifier Conventions
- IDs use prefixes: `FND`, `RSK`, `COV`, `TST`, `CHN`, `API`. Format: `<PREFIX>-<RUNDATE>-<4-digit sequence>`.
- Sequence resets per run to maintain deterministic ordering in generated reports.

## Retention & Access
- Early MVP ships without automatic pruning; runs accumulate under `~/.qaagent/runs/`.
- CLI should surface a notice reminding users to clean up historical runs manually until retention is implemented.
- Future policy (pre-GA) will introduce configurable limits and an optional `index.json` catalog; track as follow-up before launch.
- API server reads from latest run by default with option `?run_id=`.

## Error Handling & Degradation
- If a collector fails, manifest marks `executed=false`, exit code, and optional error message; corresponding evidence file may be missing. Risk engine should treat missing inputs as neutral (score 0 for that factor) and lower confidence.
- Structured logs record event `evidence.write` with `run_id`, `record_type`, and count.

## Security & Privacy
- All files remain local; no outbound uploads.
- Tool outputs sanitized for secrets before storage (e.g., strip environment variables, redact tokens using configurable patterns).
- SQLite option uses WAL off to avoid additional files; file permissions `0600` to limit access.
