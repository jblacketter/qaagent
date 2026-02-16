# Project Roadmap

## Overview

**qaagent** is a Python QA automation framework that discovers routes, assesses risks, generates tests, orchestrates execution, and produces reports. Phases 1-4 (Modernization, Test Generation, Orchestration, Enhanced Analysis) are complete. This roadmap covers the next wave of development.

**Tech Stack:** Python 3.11+, Typer, Pydantic v2, Jinja2, litellm, FastAPI, Playwright, pytest, Behave

**Workflow:** Lead (claude) / Reviewer (codex) with Human Arbiter (see `ai-handoff.yaml`)

## Completed Work

- **Phase 1: Codebase Modernization** — CLI split, legacy migration, LLM client, Pydantic v2
- **Phase 2: Test Framework Generation** — BaseGenerator ABC, LLM enhancer, Playwright/Behave/pytest generators, validator
- **Phase 3: Intelligent Test Orchestration** — Unified runners, RunOrchestrator, FailureDiagnostics, `run-all`
- **Phase 4: Enhanced Analysis** — AST-based parsers (FastAPI/Flask/Django/Next.js), 16 risk rules, CI/CD templates

## Upcoming Phases

### Phase 5: Hardening & Test Coverage
- **Status:** Not Started
- **Description:** Fill test coverage gaps across core modules, harden utilities, improve reliability of the framework itself.
- **Key Deliverables:**
  - Tests for untested modules (behave_runner, evidence/writer, tools, autofix, command modules, API routes)
  - Config utility coverage (detect, templates, legacy)
  - Repo package coverage (cache, validator)

### Phase 6: Custom Risk Rules via YAML
- **Status:** Not Started
- **Description:** Allow users to define custom risk rules in YAML without writing Python code, extending the pluggable rule engine.
- **Key Deliverables:**
  - YAML rule schema and loader
  - Integration with RiskRuleRegistry
  - Documentation and example rules

### Phase 7: Parallel Test Execution
- **Status:** Not Started
- **Description:** Run test suites concurrently across runners for faster feedback loops.
- **Key Deliverables:**
  - Concurrent suite execution in RunOrchestrator
  - Result aggregation from parallel runs
  - Resource-aware scheduling (CPU, browser instances)

### Phase 8: Coverage Gap Analysis
- **Status:** Not Started
- **Description:** Map JUnit test results back to discovered routes and source code, identifying untested paths and coverage holes.
- **Key Deliverables:**
  - JUnit-to-route mapping engine
  - Coverage gap report generation
  - Integration with `analyze` and `report` commands

### Phase 9: RAG-Powered Test Generation
- **Status:** Not Started
- **Description:** Index repository code, docs, and specs to provide rich context for LLM-powered test generation.
- **Key Deliverables:**
  - Document/code indexing pipeline
  - RAG retrieval for test generation context
  - Enhanced LLMTestEnhancer with retrieval

### Phase 10: New Language Parsers
- **Status:** Not Started
- **Description:** Extend route discovery to Go, Ruby, and Rust web frameworks.
- **Key Deliverables:**
  - Go parser (net/http, Gin, Echo)
  - Ruby parser (Rails, Sinatra)
  - Rust parser (Actix, Axum)

### Phase 11: Notifications & Reporting
- **Status:** Not Started
- **Description:** Integrate Slack/email notifications for CI findings summaries and expand reporting capabilities.
- **Key Deliverables:**
  - Slack webhook integration
  - Email notification support
  - CI-friendly summary output formats

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
