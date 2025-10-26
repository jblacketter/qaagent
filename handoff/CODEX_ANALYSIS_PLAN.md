# Codex Analysis & Plan — qaagent MVP

_Date:_ 2025-10-24

## 0. Background & Constraints
- Follow Codex kickoff instructions: local-first, read-only analysis, deterministic tooling, no outbound data unless explicitly opted-in.
- MVP scope = TASK_BOARD Sprint 1→3 with evidence store, quality collectors, coverage + churn risk scoring, read-only API, dashboard, and local AI summaries citing evidence.
- Reference artifacts: `risk_config.yaml` weights, `cuj.yaml` journeys, acceptance criteria, privacy policy, prompt guidelines.
- External AI is disabled by default; Ollama-only summaries must cite evidence IDs sourced from the evidence store per spec.

## 1. Current Repository Assessment (as of commit in workspace)
- **Analysis tooling:** Existing code focuses on Next.js route discovery, heuristic risk scoring, strategy docs. No integration with flake8/pylint/bandit/pip-audit, no git churn or coverage ingestion.
- **Data handling:** No normalized evidence store; outputs currently go to ad-hoc JSON/Markdown in `reports/` and workspace directories.
- **API/Dashboard:** Dashboard generator renders static/enhanced HTML directly; no REST API endpoints that serve normalized data. Web UI exists but executes analysis inline rather than reading from an evidence API.
- **Run artifacts:** Workspace manager writes into `~/.qaagent/workspace/<target>/…`; acceptance criteria expect `.qaagent/runs/<ts>/…` with structured data.
- **LLM:** `llm.py` references external providers; no local-only Ollama summarization with evidence citations.
- **Guardrails:** Repo lacks pinned tool versions or deterministic wrappers; RUNBOOK is skeletal and developer notes absent.

## 2. Gap Analysis vs MVP Requirements
| Area | Required Outcome | Current State | Gap |
|------|------------------|---------------|-----|
| Evidence Store | JSON/SQLite layout per spec, populated per run under `.qaagent/runs/` | None | Must design schema, writer, loader abstractions, retention policy |
| Quality Collectors | flake8/pylint/bandit/pip-audit (or safety) executed read-only with pinned versions | Not implemented | Need adapters, result parsers, structured logging, graceful missing-tool handling |
| Coverage Signals | Ingest coverage.xml/lcov, map to journey/components, compute coverage deltas | Partial standalone report logic | Build ingestion pipeline + mapping to CUJs |
| Git Churn | Analyze git history/metadata to weight risk | None | Need git runner, heuristics respecting read-only constraint |
| Risk Scoring | Weighted aggregation using `risk_config.yaml` with confidence metrics | Simple heuristics unrelated to config | Implement scoring engine referencing config, produce evidence-linked findings |
| API Layer | `/api/report.json`, `/api/findings`, `/api/risks`, `/api/tests`, `/api/coverage`, `/api/apis` read-only | No API server; dashboard reads generated HTML | Need FastAPI (read-only) layer serving evidence store snapshots |
| Dashboard | Consume API, display Top Risks/Findings/Coverage/Recs | Static templates built from in-memory data | Rework front-end to call API, align views with acceptance criteria |
| AI Summaries | Local Ollama prompts referencing evidence IDs | LLM module uses remote options, no citation policy | Implement local client, prompt templates, citation enforcement |
| Logging & Privacy | Structured logs, secret redaction, external AI off by default | Not addressed | Instrument logging + config flags |
| Documentation | RUNBOOK, DEVELOPER_NOTES populated with implementation details | RUNBOOK partial, developer notes missing | Produce thorough docs post-implementation |

## 3. Proposed Architecture
```
qaagent/
  collectors/        # Tool runners: flake8, pylint, bandit, pip-audit, coverage ingestors, git churn
  evidence/          # Models, writers, SQLite/JSON backends, run manager (.qaagent/runs/...)
  analyzers/         # Risk scoring engine, CUJ coverage analyzer, aggregations
  config/            # risk_config loader, cue for pinned tool versions, privacy toggles
  api/               # FastAPI app exposing read-only endpoints backed by evidence store
  dashboard/         # Front-end assets consuming API (could serve via api or static files)
  llm/               # Local summary generator enforcing citation policy
  cli/commands/      # `qaagent analyze`, `qaagent api`, `qaagent dashboard`, orchestrating runs
  utils/logging.py   # Structured logging helpers
```
- Evidence store writer should emit both JSON (for portability) and optional SQLite per spec; align IDs for findings/tests/coverage referencing `EVIDENCE_STORE_SPEC.md` (needs fleshing-out during implementation).
- Collectors emit structured records tagged with `evidence_id`, timestamp, tool metadata; orchestrator merges into run store.
- Risk engine reads collector outputs + config to compute `RiskScore` objects with band classification + confidence factors defined in `risk_config.yaml`.
- API layer serves latest run snapshot or user-selected run; multi-run indexing handled by evidence store manager.
- Dashboard (initially simple) fetches via API; reuse existing enhanced HTML as placeholder but refactor data source to API JSON before delivering acceptance criteria.
- CLI tasks wrap orchestrator: `qaagent analyze` runs collectors + analyzers + persists evidence, `qaagent api` hosts REST server, `qaagent dashboard` serves static UI backed by API.

## 4. Sprint Roadmap (High-level)
### Sprint 1 — Evidence Store & Quality Collectors (current focus)
**Objectives**
1. Define evidence schemas (JSON + optional SQLite); implement run manager writing to `.qaagent/runs/<timestamp>/`.
2. Implement flake8, pylint, bandit, pip-audit adapters with deterministic invocation, tool version pinning, graceful degradation.
3. Capture coverage artifacts (if provided) into standardized format; store metadata for CUJ linking.
4. Structured logging + configuration to specify tool paths, timeouts, enable/disable collectors.

**Key Deliverables**
- `qaagent/evidence/` package with models, writer, and loader utilities.
- `qaagent/collectors/{lint.py,security.py,dependencies.py,coverage.py}` modules orchestrated by analyzer runner.
- CLI command `qaagent analyze` producing populated run directory and JSON manifest referencing evidence IDs.
- Updated RUNBOOK outline describing setup + analyze workflow (details finalized later).

### Sprint 2 — Risk Engine, Coverage Mapping, API Layer
- Implement risk aggregation referencing `risk_config.yaml`; compute scores, bands, confidence metrics.
- Ingest git churn/complexity metrics (read-only using `git` commands) and merge with lint/security findings.
- Map coverage + CUJ definitions (`cuj.yaml`) to expose coverage deltas per journey.
- Build FastAPI read-only service exposing `/api/report.json`, `/api/findings`, `/api/risks`, `/api/tests`, `/api/coverage`, `/api/apis` served from evidence store snapshots.
- Begin populating RUNBOOK & developer notes with operational guidance.

### Sprint 3 — Dashboard, Local AI Summaries, Polish
- Front-end/dashboard consuming API endpoints (either rewrite existing template or React-lite static assets).
- Local Ollama summary generator with prompt guidelines + evidence citation enforcement; CLI/API toggles for AI.
- Privacy guardrails + configuration (external AI opt-in, log redaction).
- Documentation completion: acceptance criteria validation, runbook, developer notes, prompt catalog.

## 5. Risks & Open Questions
- **Spec clarity:** Handoff docs are terse; require expansion (evidence schema, API payload structure). Action: codify during Sprint 1 planning session with Claude/user.
- **Tool availability:** Users may lack certain linters/security tools; need optional installation guidance + skip logic.
- **Runtime constraints:** Running multiple tools sequentially may be slow; consider parallel execution or configurable subsets.
- **Data volume:** Storing raw tool outputs vs normalized data — determine retention policy (raw logs vs summaries) early.
- **Dashboard technology:** Reusing existing enhanced HTML may conflict with new API-first requirement; may need new lightweight frontend.
- **Ollama models:** Need confirmation on default local model (from kickoff: qwen2.5:7b?). Ensure prompts align with `PROMPT_GUIDELINES.md` once expanded.

## 6. Immediate Next Steps (Pre-Claude Alignment)
1. Flesh out detailed evidence store schema draft (JSON structure, IDs, relationships) — likely augment `EVIDENCE_STORE_SPEC.md`.
2. Specify collector interfaces (input params, outputs, error handling) and confirm tool version pinning strategy.
3. Prepare Sprint 1 task breakdown with estimates and dependencies for review with Claude/user.
4. Identify missing documentation (`DEVELOPER_NOTES.md`, fuller RUNBOOK) to co-author after design sign-off.
