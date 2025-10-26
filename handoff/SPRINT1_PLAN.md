# Sprint 1 Plan — Evidence Store & Quality Collectors

_Date:_ 2025-10-24
_Duration:_ 3–4 focused work sessions

## Objectives
1. Stand up evidence store infrastructure (JSON + optional SQLite) under `~/.qaagent/runs/`.
2. Implement lint/security/dependency collectors with deterministic tool invocation.
3. Capture coverage + git churn signals and persist normalized outputs.
4. Wire CLI entry point (`qaagent analyze`) to orchestrate collectors and persist manifest.

## Work Breakdown
| ID | Task | Description | Owner | Est. | Dependencies |
|----|------|-------------|-------|------|--------------|
| S1-01 | Evidence data models | Implement Python dataclasses/TypedDicts for findings, risks (stub), coverage, churn, manifest. | Codex | 0.5d | `EVIDENCE_STORE_SPEC` |
| S1-02 | Run manager | Create `qaagent/evidence/run_manager.py` to create run dirs, write manifest, handle retention, generate IDs. | Codex | 0.5d | S1-01 |
| S1-03 | JSON writer | Implement streaming JSONL writer + optional SQLite backend (feature-flag). | Codex | 0.5d | S1-02 |
| S1-04 | flake8 collector | Runner + parser producing normalized findings, logs artifacts. | Codex | 0.5d | S1-03 |
| S1-05 | pylint collector | Runner + parser (JSON output). | Codex | 0.5d | S1-03 |
| S1-06 | bandit collector | Runner + parser, severity mapping. | Codex | 0.5d | S1-03 |
| S1-07 | pip-audit collector | Runner + parser; fallback to safety when pip-audit unavailable. | Codex | 0.5d | S1-03 |
| S1-08 | coverage ingestor | Parse coverage.xml / lcov if present, emit coverage metrics + diagnostics. | Codex | 0.5d | S1-03 |
| S1-09 | git churn analyzer | Read-only git stats (window configurable), emit churn evidence. | Codex | 0.5d | S1-03 |
| S1-10 | Analyzer orchestrator | Module coordinating collectors, handling skips/errors, feeding evidence writer. | Codex | 0.5d | S1-04→S1-09 |
| S1-11 | CLI command | Add `qaagent analyze` flow: argument parsing, config loading, run manager orchestration, summary output. | Codex | 0.5d | S1-10 |
| S1-12 | Structured logging | Implement logging helpers + integrate with collectors/orchestrator. | Codex | 0.25d | S1-04→S1-11 |
| S1-13 | Unit tests | Collector parser tests, run manager tests, CLI smoke using synthetic repo fixture. | Codex | 0.75d | S1-04→S1-11 |
| S1-14 | Docs update | Expand RUNBOOK (setup + analyze workflow) and seed `docs/DEVELOPER_NOTES.md` with architecture decisions. | Codex | 0.5d | All |

_Total estimate_: ~6 developer-days (can be compressed with parallel work once schematics validated).

## Deliverables Checklist
- [ ] `qaagent/evidence/` package with run manager + writers
- [ ] `qaagent/collectors/{flake8,pylint,bandit,pip_audit,coverage,git_churn}.py`
- [ ] `qaagent/analyze.py` (or similar) orchestrator invoked from CLI
- [ ] `qaagent analyze` command writing manifest + evidence files
- [ ] Synthetic fixtures / tests in `tests/integration/test_analyze_collectors.py`
- [ ] Documentation updates (RUNBOOK, DEVELOPER_NOTES)

## Decisions & Open Items
- **Evidence store backend**: ship JSON-only in Sprint 1; document SQLite backend as a post-MVP enhancement.
- **Git churn analysis**: default to a 90-day lookback against the current branch's merge-base with `origin/main`; explain rationale in docs so users can adjust later.
- **Dependency audit scope**: run `pip-audit` against discovered requirements files (`requirements*.txt`). Detect `poetry.lock`/`Pipfile.lock` and log guidance for future support.
- **Lint severity mapping**: keep built-in mappings; expose overrides later if user demand arises.
- **Retention**: no automated cleanup yet—inform users that runs accumulate and policy will be added pre-launch (workspace retention remains manual for now).

## Pre-Work Before Implementation
- Verify availability of pinned tool versions on target platform; add to `requirements-dev.txt` or dedicated installer doc.
- Prepare synthetic repo fixture with known lint + security issues to validate collectors quickly (`tests/fixtures/synthetic_repo`).
- Align on responses to open questions to avoid rework mid Sprint.
