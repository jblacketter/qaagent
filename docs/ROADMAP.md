# Project Roadmap

## Overview

**qaagent** is a Python QA automation framework that discovers routes, assesses risks, generates tests, orchestrates execution, and produces reports. Phases 1-4 (Modernization, Test Generation, Orchestration, Enhanced Analysis) are complete. This roadmap covers the next wave of development.

**Tech Stack:** Python 3.11+, Typer, Pydantic v2, Jinja2, litellm, FastAPI, Playwright, pytest, Behave

**Workflow:** Lead (codex) / Reviewer (claude) with Human Arbiter (see `ai-handoff.yaml`)

## Completed Work

- **Phase 1: Codebase Modernization** — CLI split, legacy migration, LLM client, Pydantic v2
- **Phase 2: Test Framework Generation** — BaseGenerator ABC, LLM enhancer, Playwright/Behave/pytest generators, validator
- **Phase 3: Intelligent Test Orchestration** — Unified runners, RunOrchestrator, FailureDiagnostics, `run-all`
- **Phase 4: Enhanced Analysis** — AST-based parsers (FastAPI/Flask/Django/Next.js), 16 risk rules, CI/CD templates
- **Phase 5: Hardening & Test Coverage** — 22 new test files, 305 tests across P1-P5 (core infra, config/repo, utilities, CLI commands, API routes)
- **Phase 6: App Documentation & Architecture Mapping** — Doc engine (feature grouping, integration detection, CUJ discovery, architecture graphs), CLI (`doc generate/show/export/cujs`), API endpoints, 13 React dashboard components, 179 doc-specific tests
- **Phase 7: Custom Risk Rules via YAML** — YAML rule schema (`yaml_loader.py`, `yaml_rule.py`), match conditions (path/method/auth/tags/deprecated), severity escalation, severity overrides (post-processing), merge semantics (file+inline), collision protection, CLI (`rules list/show/validate`), 78 new tests
- **Phase 8: Parallel Test Execution** — Concurrent orchestration support for generated suites with merged result handling and failure diagnostics integration
- **Phase 9: Coverage Gap Analysis** — Route-level coverage mapping from JUnit/OpenAPI with `analyze coverage-gaps` CLI and report integration
- **Phase 10: RAG-Powered Test Generation** — Local repo indexing (`rag index/query`) and retrieval-aware prompt enhancement for test generation
- **Phase 11: New Language Parsers** — Source route discovery support for Go (net/http, Gin, Echo), Ruby (Rails, Sinatra), and Rust (Actix, Axum)
- **Phase 12: Notifications & Reporting** — CI summary formatting plus Slack webhook and SMTP email notifications via `qaagent notify`
- **Phase 13: Live DOM Inspection** — `analyze dom` command for Playwright-based selector coverage analysis (inventory, forms, nav links, and recommendations)
- **Phase 14: Live UI Route Crawling** — `analyze routes --crawl` for Playwright-based runtime UI route discovery with depth/page bounds and profile-aware auth/session defaults
- **Phase 15: AI-Assisted Test Recording** — `qaagent record` for browser flow capture and export to Playwright/Behave test assets with selector ranking and sensitive input redaction
- **Phase 25: Branch Board** — Branch lifecycle tracker with kanban board UI, auto-generated test checklists from code diffs, automated test generation/execution per branch, and promote-to-regression workflow

## Upcoming Phases

- No additional roadmap phases are defined yet.

### Phase 12: Security Scanning Integration
- **Status:** Not Started (low priority — revisit when core framework is stable)
- **Description:** Re-integrate security scanning tools that existed in an earlier prototype.
  An earlier version of qaagent had working CLI commands and CI pipeline steps for dependency
  auditing, static code analysis, and dynamic web scanning. These were removed during the
  Phase 1-4 architectural rewrite (monolithic CLI → modular commands). The functionality
  could be re-implemented as proper command modules in the new architecture.
- **Prior Art:** Implementations existed in the pre-rewrite codebase (preserved in git stash
  `Pre-pull Windows local changes` if not yet dropped, or see details below).
- **Key Deliverables:**

  **1. Dependency Audit (`sec-deps`) — pip-audit wrapper**
  - Scan Python dependencies for known CVEs
  - CLI: `qaagent sec-deps --outdir reports/security --json-out`
  - Wraps `pip-audit -f json -o <path>`
  - Requires: `pip-audit` (add to `[security]` extras in pyproject.toml)
  - Output: `reports/security/pip_audit.json`

  **2. Static Code Analysis (`sec-code`) — bandit wrapper**
  - SAST scanning for Python source code
  - CLI: `qaagent sec-code --target src --outdir reports/security --json-out`
  - Wraps `bandit -r <target> -f json -o <path> -q`
  - Requires: `bandit` (add to `[security]` extras)
  - Output: `reports/security/bandit.json`

  **3. Dynamic Web Scanning (`sec-zap-baseline`) — OWASP ZAP via Docker**
  - Baseline DAST scan against a running target URL
  - CLI: `qaagent sec-zap-baseline --url <target> --outdir reports/zap --minutes 1`
  - Runs `owasp/zap2docker-stable` container with `zap-baseline.py`
  - Options: `--ajax-spider` flag, configurable scan duration
  - Requires: Docker
  - Output: `reports/zap/zap.json` + `reports/zap/zap.html`

  **4. Report Integration**
  - Summarize pip-audit results (total vulns, by severity)
  - Summarize bandit results (total issues, by severity)
  - Summarize ZAP results (total alerts, by risk level)
  - Render security sections in HTML/Markdown findings report

  **5. CI Pipeline Steps**
  - GitHub Actions workflow steps (all `continue-on-error: true`):
    ```yaml
    - name: Dependency audit (pip-audit)
      run: qaagent sec-deps --outdir reports/security --json-out
    - name: Code scan (bandit)
      run: qaagent sec-code --target src --outdir reports/security --json-out
    - name: ZAP baseline scan
      env:
        ZAP_TARGET: https://example.com
      run: qaagent sec-zap-baseline --url "$ZAP_TARGET" --outdir reports/zap
    ```

  **6. MCP Tools**
  - `security_deps` — run pip-audit from MCP client
  - `security_code` — run bandit from MCP client

- **Implementation Notes:**
  - Should follow the current modular pattern: new `commands/security_cmd.py`
  - Report summarizers should integrate with existing `report.py` artifact collection
  - All three tools are thin wrappers around external binaries — keep them simple
  - `[security]` extras group in pyproject.toml: `pip-audit`, `bandit`
  - ZAP requires Docker (no pip package) — detect and error gracefully

## Decision Log
See `docs/decision_log.md`

## Getting Started
1. Use `/handoff-phase` to check current phase
2. Use `/handoff-plan create [phase]` to start planning
3. Use `/handoff-status` for project overview
