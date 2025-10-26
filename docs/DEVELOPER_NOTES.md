# Developer Notes — Sprint 1 & 2

## Evidence Store
- Evidence models (`qaagent/evidence/models.py`) define manifest, finding, coverage, churn, API, and test records with UTC timestamps.
- RunManager creates directories at `~/.qaagent/runs/<run_id>/` with manifest + evidence and artifact subfolders.
- EvidenceWriter writes JSONL files and updates manifest counts/registry.
- IDs generated via `EvidenceIDGenerator` (`FND-YYYYMMDD-####`, `COV-...`, etc.).

## Collectors
- All collectors live in `qaagent/collectors/` and are pure-python wrappers around external tools.
  - `flake8`: parses default text output via regex; artifact at `flake8.log`.
  - `pylint`: uses `--output-format=json`; artifact at `pylint.json`.
  - `bandit`: `bandit -f json`; artifact `bandit.json`, severity/confidence mapped.
  - `pip_audit`: detects requirements files, runs `pip-audit --format json` per file, artifacts `pip_audit_<manifest>.json`, metadata includes package/fix versions.
  - `coverage`: reads `coverage.xml`, falls back to `lcov.info`; outputs overall and per-file coverage records.
  - `git_churn`: `git log --since=<window> --numstat`, aggregates per-file churn stats, artifact `git_churn.log`.
- Integration tests in `tests/integration/collectors/` rely on `tests/fixtures/synthetic_repo` (git history seeded via `setup_git_history.py`).
- `CollectorsOrchestrator` runs collectors sequentially and logs structured events to `~/.qaagent/logs/<run_id>.jsonl`.

## CLI Commands
- `qaagent analyze collectors [TARGET]` runs the Sprint 1 collector pipeline and stores evidence under the configured runs directory.
- `qaagent analyze risks [RUN_ID]` loads or computes `risks.jsonl` via `RiskAggregator` and renders a Rich table.
- `qaagent analyze recommendations [RUN_ID]` maps coverage to CUJs and produces `recommendations.jsonl`.
- `qaagent api` starts the FastAPI server (uses `QAAGENT_RUNS_DIR` when provided).

## Risk Aggregation & Recommendations
- `qaagent/analyzers/risk_aggregator.py` merges findings, coverage, and churn using weights from `handoff/risk_config.yaml`.
- `qaagent/analyzers/cuj_config.py` + `coverage_mapper.py` load CUJ definitions and map coverage using glob patterns.
- `qaagent/analyzers/recommender.py` surfaces testing priorities driven by risk scores and coverage gaps.
- Evidence dataclasses now include `RiskRecord` and `RecommendationRecord` for JSONL persistence.

## API Layer
- FastAPI app lives in `qaagent/api/app.py`; routes in `qaagent/api/routes/{runs,evidence}.py`.
- `/api/runs` lists run manifests; `/api/runs/{id}/risks` and `/recommendations` expose aggregated outputs.
- Structured logs for collectors continue to live in `logs/<run_id>.jsonl` alongside evidence JSONL files.

## Testing
- Unit tests for evidence components and pip-audit collector; integration tests for each collector individually.
- Full suite command: see README or run `.venv/bin/pytest tests/...` (pylint/bandit tests skip when tools missing).

## Follow-ups
- Sprint 3: dashboard refactor to consume API + AI summarization polish.
- Expand E2E tests to exercise external tooling once binaries are installed in CI.
