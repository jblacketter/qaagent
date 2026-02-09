# QA Agent - Project Roadmap (v2)

**Last Updated:** 2026-02-08
**Lead:** claude
**Reviewer:** codex
**Arbiter:** Human

## Overview

qaagent is a Python QA automation framework that discovers routes, assesses risks, generates test strategies, and produces reports. This roadmap replaces the original (Oct 2025) and reflects the project's evolution and new priorities.

## Completed Work (Sprints 1-3, Oct 2025)

- Evidence collection pipeline (flake8, pylint, bandit, pip-audit, git-churn, coverage)
- CLI (Typer) with 30+ commands across subgroups
- MCP server with 12+ tools
- Route discovery (OpenAPI specs, Next.js App Router)
- Risk assessment engine with CUJ integration
- Strategy generation
- Test generation: Behave BDD features, pytest unit stubs, test data via Faker
- Reporting: Markdown, HTML dashboard
- Web UI (`qaagent web-ui`) with WebSocket updates
- Target/workspace management system
- LLM module (Ollama-only, basic chat + summarize)
- Configuration system (YAML profiles, target registry)
- FastAPI REST API for evidence/runs

## Current State Assessment (Feb 2026)

### Strengths
- Solid modular architecture: analyzers, collectors, generators, evidence
- Good test coverage (~50 test files)
- Well-designed evidence pipeline with manifest tracking
- Config system with profile templates per framework

### Technical Debt (addressed in Phase 1)
1. ~~**cli.py is 2048 lines**~~ — Split into 9 command modules (Phase 1)
2. ~~**Dual config system**~~ — Compatibility bridge + migration utility (Phase 1)
3. ~~**LLM module is Ollama-only**~~ — Multi-provider via litellm (Phase 1)
4. ~~**Test generators produce stubs**~~ — LLM-enhanced generation (Phase 2)
5. ~~**Dataclass/Pydantic inconsistency**~~ — Standardized to Pydantic (Phase 1)
6. ~~**No E2E test framework generation**~~ — PlaywrightGenerator (Phase 2)
7. **Route discovery limited** - no FastAPI/Flask/Django source parsing (Phase 4)
8. ~~**No actual test runner orchestration**~~ — RunOrchestrator + diagnostics (Phase 3)

---

## Phase Plan

### Phase 1: Codebase Modernization
- Status: **Complete** (approved by codex, 4-round review cycle)
- Priority: High
- Description: Split CLI into command modules, legacy config migration, multi-provider LLM via litellm, Pydantic standardization
- Details: `docs/phases/modernization.md`

### Phase 2: Test Framework Generation Engine
- Status: **Complete** (approved by codex, 2-round review cycle)
- Priority: Critical (key differentiator)
- Description: BaseGenerator ABC, LLMTestEnhancer, PlaywrightGenerator, TestValidator, `generate all`/`e2e` commands, `plan-run --generate`
- Details: `docs/phases/test-framework-gen.md`

### Phase 3: Intelligent Test Orchestration
- Status: **Complete** (approved by codex, 3-round review cycle)
- Priority: High
- Description: Unified test runners, orchestration engine, LLM-powered failure diagnostics, enhanced `plan-run` pipeline
- Details: `docs/phases/test-orchestration.md`

### Phase 4: Enhanced Analysis
- Status: **Plan Approved** (approved by codex, 3-round review cycle) — Implementation in progress
- Priority: Medium
- Description: FastAPI/Flask/Django route discovery, pluggable risk rule engine, CI/CD templates
- Details: `docs/phases/enhanced-analysis.md`

---

## Decision Log
See `docs/decision_log.md`
