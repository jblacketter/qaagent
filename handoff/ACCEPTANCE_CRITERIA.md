# Acceptance Criteria — qaagent MVP

**Version:** 1.0.0-mvp
**Last Updated:** 2025-10-24
**Purpose:** Define testable criteria for MVP release

---

## Overview

This document defines the **Definition of Done** for qaagent MVP across all three sprints. Each criterion must be verifiable through automated tests or manual validation.

---

## Sprint 1: Evidence Store & Collectors

### AC-S1-01: Evidence Store Creation ✅

**Given:** A Python project repository
**When:** User runs `qaagent analyze`
**Then:**
- [ ] A new directory is created at `~/.qaagent/runs/<timestamp>/`
- [ ] Directory contains `manifest.json` with valid schema
- [ ] Directory contains `evidence/` subdirectory
- [ ] All evidence IDs follow convention: `<PREFIX>-<RUNDATE>-<####>`

**Verification:** Automated test inspecting filesystem

---

### AC-S1-02: flake8 Collector ✅

**Given:** A Python project with style violations
**When:** flake8 collector runs
**Then:**
- [ ] `quality.jsonl` contains findings with `tool="flake8"`
- [ ] Each finding has required fields: `evidence_id`, `file`, `line`, `code`, `message`
- [ ] `artifacts/flake8.log` contains raw tool output
- [ ] Manifest records `tools.flake8.executed=true` and version

**Verification:** Integration test with synthetic repo fixture

---

### AC-S1-03: Security Collectors (bandit, pip-audit) ✅

**Given:** A Python project with security issues
**When:** Security collectors run
**Then:**
- [ ] `quality.jsonl` contains bandit findings with `severity` mapped correctly
- [ ] `quality.jsonl` contains dependency findings with CVE IDs
- [ ] Manifest records both tools with execution status
- [ ] High-severity findings use correct severity level (`high`, `critical`)

**Verification:** Synthetic repo with known CVE in requirements.txt

---

### AC-S1-04: Coverage Ingestion ✅

**Given:** A project with `coverage.xml` present
**When:** Coverage collector runs
**Then:**
- [ ] `coverage.jsonl` contains line coverage metrics per component
- [ ] Metrics include `total_statements` and `covered_statements`
- [ ] Coverage values are between 0.0 and 1.0
- [ ] Manifest records `tools.coverage.found=true`

**Verification:** Test with fixture containing coverage.xml

---

### AC-S1-05: Git Churn Analysis ✅

**Given:** A git repository with commit history
**When:** Git churn collector runs with 90-day window
**Then:**
- [ ] `churn.jsonl` contains per-file metrics
- [ ] Each record includes `commits`, `lines_added`, `lines_deleted`
- [ ] Manifest records `tools.git.window="90d"`
- [ ] Files with zero churn are excluded

**Verification:** Test repo with controlled git history

---

### AC-S1-06: Graceful Degradation ✅

**Given:** A system missing optional tools (e.g., bandit not installed)
**When:** Analysis runs
**Then:**
- [ ] Console shows warning: "bandit not found, skipping security analysis"
- [ ] Manifest records `tools.bandit.executed=false`
- [ ] Other collectors still execute normally
- [ ] Exit code is 0 (success with warnings)

**Verification:** Test in clean environment without tools installed

---

### AC-S1-07: Structured Logging ✅

**Given:** Any analysis run
**When:** Collectors execute
**Then:**
- [ ] Console output includes collector progress
- [ ] Log file `~/.qaagent/logs/<run_id>.jsonl` contains structured events
- [ ] Each event has `timestamp`, `run_id`, `event`, `level`
- [ ] Log includes `collector.start` and `collector.finish` events

**Verification:** Parse log file and validate schema

---

## Sprint 2: Risk Engine & API

### AC-S2-01: Risk Score Calculation ✅

**Given:** Evidence from Sprint 1 collectors
**When:** Risk aggregator runs
**Then:**
- [ ] `risks.jsonl` contains risk records with scores 0-100
- [ ] Each risk has `band` assignment (P0/P1/P2/P3)
- [ ] Confidence scores are between 0.0 and 1.0
- [ ] `metadata.weights` shows which dimensions contributed

**Verification:** Unit tests with known input values

---

### AC-S2-02: Risk Configuration Loading ✅

**Given:** User has custom `~/.qaagent/config/risk_config.yaml`
**When:** Risk calculation occurs
**Then:**
- [ ] Custom weights are applied correctly
- [ ] Custom priority bands are used for band assignment
- [ ] Default values fill in missing config keys
- [ ] Invalid config triggers validation error

**Verification:** Test with various config files

---

### AC-S2-03: CUJ Coverage Mapping ✅

**Given:** Project with `cuj.yaml` and coverage data
**When:** Coverage analyzer runs
**Then:**
- [ ] Coverage metrics are grouped by CUJ ID
- [ ] Each CUJ shows actual vs target coverage
- [ ] CUJs below target are flagged
- [ ] Component-to-CUJ mapping follows glob patterns from cuj.yaml

**Verification:** Test with example cuj.yaml from handoff/

---

### AC-S2-04: API Server Launch ✅

**Given:** At least one analysis run exists
**When:** User runs `qaagent api`
**Then:**
- [ ] Server starts on http://127.0.0.1:8765
- [ ] GET /api/v1/health returns 200 OK
- [ ] GET /api/v1/runs lists available runs
- [ ] Server logs show startup message with port

**Verification:** Integration test with test client

---

### AC-S2-05: API Endpoints (Findings) ✅

**Given:** API server running with test data
**When:** Client requests `GET /api/v1/runs/latest/findings`
**Then:**
- [ ] Response is valid JSON with `findings` array
- [ ] Findings match evidence store data
- [ ] Filter parameters work: `?severity=high`
- [ ] Pagination works: `?limit=10&offset=0`

**Verification:** API integration tests

---

### AC-S2-06: API Endpoints (Risks) ✅

**Given:** API server with risk data
**When:** Client requests `GET /api/v1/runs/latest/risks`
**Then:**
- [ ] Response contains risk scores with bands
- [ ] Filtering by band works: `?band=P0`
- [ ] Each risk includes `related_evidence` array
- [ ] Confidence scores are included

**Verification:** API integration tests

---

## Sprint 3: Dashboard & AI Summaries

### AC-S3-01: Dashboard Launch ✅

**Given:** At least one analysis run exists
**When:** User runs `qaagent dashboard`
**Then:**
- [ ] Browser opens to http://localhost:8765
- [ ] Dashboard loads without JavaScript errors
- [ ] Dashboard displays run selection dropdown
- [ ] Selecting a run updates displayed data

**Verification:** E2E test with Playwright/Selenium

---

### AC-S3-02: Dashboard Views ✅

**Given:** Dashboard is open with data loaded
**When:** User navigates tabs
**Then:**
- [ ] Overview tab shows summary stats (total findings, risk distribution)
- [ ] Risks tab shows sortable table of top risks
- [ ] Findings tab shows filterable findings list
- [ ] Coverage tab shows CUJ coverage chart

**Verification:** E2E tests checking DOM elements

---

### AC-S3-03: Ollama Integration ✅

**Given:** Ollama is installed with qwen2.5:7b model
**When:** User runs `qaagent analyze --summarize`
**Then:**
- [ ] Local Ollama client is used (no external API calls)
- [ ] Summary includes evidence citations (e.g., "RSK-...", "FND-...")
- [ ] Summary is written to `summary.md` in run directory
- [ ] Manifest records `ai.enabled=true`, `ai.model="qwen2.5:7b"`

**Verification:** Mock Ollama server + citation validation

---

### AC-S3-04: Privacy Compliance ✅

**Given:** Default configuration (no user changes)
**When:** Any command runs
**Then:**
- [ ] No network requests to external APIs (except explicitly enabled)
- [ ] Config shows `policies.allow_external_ai=false`
- [ ] Logs do not contain environment variables or secrets
- [ ] Evidence files do not contain secret patterns

**Verification:** Network monitoring + secret scanner on outputs

---

### AC-S3-05: Documentation Completeness ✅

**Given:** MVP codebase
**When:** User reviews documentation
**Then:**
- [ ] RUNBOOK.md has installation and first-run instructions
- [ ] API_SPEC.md documents all endpoints with examples
- [ ] DEVELOPER_NOTES.md explains architecture and design decisions
- [ ] README.md has quick start guide

**Verification:** Manual review checklist

---

## Cross-Cutting Criteria

### AC-CC-01: Performance ⚡

**Given:** A medium-sized project (10K LoC, 200 files)
**When:** Full analysis runs
**Then:**
- [ ] Analysis completes in <5 minutes
- [ ] Memory usage stays <500MB
- [ ] API responses return in <200ms (p95)

**Verification:** Benchmark tests

---

### AC-CC-02: Error Handling ❌

**Given:** Various error conditions (missing files, tool crashes)
**When:** Analysis runs
**Then:**
- [ ] No uncaught exceptions
- [ ] Error messages are user-friendly (not stack traces)
- [ ] Partial results are still saved
- [ ] Errors are logged with context

**Verification:** Chaos engineering tests

---

### AC-CC-03: Determinism 🔁

**Given:** Same project, same tool versions
**When:** Analysis runs twice
**Then:**
- [ ] Evidence IDs are consistent (same sequence)
- [ ] Risk scores are identical
- [ ] Confidence values match
- [ ] Manifest timestamps differ, all else matches

**Verification:** Snapshot testing

---

### AC-CC-04: Multi-Platform Support 🖥️

**Given:** qaagent installed on macOS, Linux, Windows (WSL2)
**When:** Analysis runs on each platform
**Then:**
- [ ] All core collectors work (flake8, pylint, bandit, git)
- [ ] Evidence store paths are correct for OS
- [ ] CLI commands work identically
- [ ] Tests pass on all platforms

**Verification:** CI matrix testing

---

## Release Checklist

Before declaring MVP complete:

- [ ] All Sprint 1-3 acceptance criteria pass
- [ ] Cross-cutting criteria verified
- [ ] Security audit completed (OWASP top 10 check)
- [ ] User acceptance testing with 3+ external users
- [ ] Performance benchmarks documented
- [ ] Known issues documented in GitHub
- [ ] Migration guide from old qaagent version (if applicable)
- [ ] Release notes drafted

---

## Success Metrics (Post-Launch)

Track these KPIs after MVP release:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Installation success rate | >95% | Telemetry (opt-in) |
| Time to first run | <10 min | User survey |
| False positive rate (security) | <20% | User feedback |
| Daily active users (internal) | 10+ | Usage logs |
| GitHub stars | 100+ | Public metrics |

---

**Status:** Living document - update as criteria evolve
**Next Review:** End of Sprint 1 (validate S1 criteria)

