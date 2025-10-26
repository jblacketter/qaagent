# Analyzers & Collectors Specification

## Overview
Collectors execute external quality tools in read-only mode, normalize results, and persist them through the evidence store. Analyzers consume normalized records to compute higher-order insights (risk scoring, CUJ coverage, recommendations).

## Collector Abstraction
```python
@dataclass
class CollectorResult:
    tool_name: str
    version: str
    exit_code: int
    findings: list[dict]
    diagnostics: list[str]
    errors: list[str]
    started_at: datetime
    finished_at: datetime

class Collector(Protocol):
    def run(self, target: TargetContext, config: CollectorConfig) -> CollectorResult: ...
```
- `TargetContext` includes repo path, virtualenv/bin paths, optional config overrides.
- `CollectorConfig` defines toggles per tool (enabled, arguments, timeout, path to binary).
- Each collector logs structured events (`collector.start`, `collector.finish`, `collector.error`).
- Results serialize through the evidence writer (see `quality.jsonl`, `churn.jsonl`, etc.).

## Tool Requirements
| Tool | Version Pin | Invocation | Output Handling | Failure Policy |
|------|-------------|------------|-----------------|----------------|
| flake8 | 6.1.x | `flake8 --format=json` | Parse JSON per file/line; attach `severity="warning"` | If binary missing: warn, mark executed=false |
| pylint | 3.2.x | `pylint --output-format=json` | Capture message id, symbol, confidence | On non-zero exit, still parse results; treat crash as failure |
| bandit | 1.7.x | `bandit -f json -q -r <root>` | Severity mapping (`LOW/MEDIUM/HIGH`) -> numeric confidence | If bandit unavailable, skip security weight |
| pip-audit (or safety fallback) | 2.7.x | detect `requirements*.txt` and run `pip-audit -r <file> --format=json` | Each vulnerability stored with package/version/CVE; log TODO when only poetry/pipenv manifests present | If no supported manifests found, record `diagnostics` |
| Coverage ingestion | n/a | Ingest `coverage.xml` or `lcov.info` if present | Parse via `xml.etree` or `coveragepy` to `CoverageMetric` | If absent, mark `coverage.found=false` |
| Git churn | git>=2.39 | `git log --stat --since=<window>` & diff against merge-base with `origin/main` | Produce per-path aggregates (commits, lines added/deleted) using default 90-day window | If repo not a git repo, set executed=false |

- Execution uses subprocess with deterministic environment: `PYTHONPATH` cleared, `LANG=C`, timeouts configurable (default 120s). Logs capture stdout/stderr to `artifacts/` for debugging.
- Collectors must never modify source (use `--exit-zero` if necessary or run in temp copy for tools that alter state).

## Normalization Guidelines
- Common fields: `evidence_id`, `tool`, `severity`, `message`, `file`, `line`, `tags`.
- Built-in severity mapping: lint/info -> `info`, style/warning -> `warning`, security high -> `high`, vulnerabilities critical -> `critical` (user override deferred).
- Each finding attaches `deterministic_hash` (hash of file path, code, message) to aid deduping across runs.
- Git churn outputs `churn.jsonl` with aggregated stats; additional analyzer may convert into `RiskScore` inputs.

## Analyzer Responsibilities
1. **Risk Aggregator**
   - Inputs: quality findings, churn signals, coverage metrics, dependency advisories.
   - Config: `risk_config.yaml.scoring` weights + normalization strategy.
   - Output: `risks.jsonl` with `score`, `band`, `confidence`, `related_evidence`.

2. **Coverage Analyzer**
   - Inputs: coverage metrics + CUJ mappings from `cuj.yaml`.
   - Output: per-CUJ coverage percentages, identify gaps vs `coverage_targets` thresholds.

3. **Recommendation Engine**
   - Derives actions from top risks and missing coverage (e.g., "Add integration tests for auth_login").
   - Writes to `findings.jsonl` as `type="recommendation"` with `evidence_refs`.

4. **API Surface Analyzer**
   - Ingests OpenAPI/route metadata (existing code) and ties to evidence store `apis.jsonl`.
   - Flags high-risk endpoints (public, low coverage, high churn).

## Error Handling & Degradation
- Any collector failure lowers overall risk confidence but does not abort the run unless `--strict` flag set.
- Warnings recorded in `CollectorResult.diagnostics` (e.g., "pip-audit skipped: requirements.txt not found").
- Analyzer pipeline respects missing inputs by zero-weighting absent factors and recording `confidence` penalty (`confidence_factor -= tool_diversity_weight`).

## Configuration Surfaces
- `qaagent.toml` (or CLI flags) allow enabling/disabling collectors, overriding binary paths, customizing git churn window.
- Provide `qaagent analyze --tools flake8,bandit` for selective execution.
- Tool versions pinned via internal mapping; CLI can output requirements snippet to help users install the right versions.

## Logging
- Structured log example:
```
{"event": "collector.finish", "tool": "flake8", "run_id": "20251024_193012Z", "findings": 128, "duration_ms": 4210}
```
- Logs stored under `~/.qaagent/logs/<run_id>.jsonl` (optional) for debugging.

## Testing Strategy
- Synthetic repo fixtures with known lint/security issues to validate parsers.
- Mock subprocesses in unit tests to ensure normalization.
- Integration tests run collectors against `examples/petstore-api` to verify evidence files populate correctly.
