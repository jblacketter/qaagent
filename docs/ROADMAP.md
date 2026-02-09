# QA Agent - Roadmap

**Last Updated:** 2026-02-09

## Overview

qaagent is a Python QA automation framework that discovers routes, assesses risks, generates test strategies, orchestrates test execution, and produces reports.

## Completed Work

### Phase 1: Codebase Modernization
- Split monolithic CLI (2000+ lines) into 9 command modules
- Legacy config migration with compatibility bridge
- Multi-provider LLM client via litellm (Ollama, Claude, GPT)
- Standardized all models to Pydantic v2

### Phase 2: Test Framework Generation Engine
- `BaseGenerator` ABC with `GenerationResult` for uniform output
- `LLMTestEnhancer` for schema-aware assertions and edge cases
- `PlaywrightGenerator` for TypeScript E2E projects from routes + CUJs
- `TestValidator` with syntax checking and LLM auto-fix
- `generate all` and `generate e2e` CLI commands
- `plan-run --generate` pipeline integration

### Phase 3: Intelligent Test Orchestration
- Unified test runners (pytest, Playwright, Behave) with JUnit parsing
- `RunOrchestrator` for config-driven suite execution with retry
- `FailureDiagnostics` with heuristic + LLM failure analysis
- `run-all` CLI command

### Phase 4: Enhanced Analysis
- AST-based route discovery for FastAPI, Flask, Django (+ Next.js migration)
- `FrameworkParser` ABC with normalized `RouteParam` model
- Pluggable risk rule engine: 16 rules (8 security, 4 performance, 4 reliability)
- `RiskRuleRegistry` with per-route and aggregate evaluation
- CI/CD template generation for GitHub Actions and GitLab CI
- `generate ci` CLI command

### Earlier Work (Sprints 1-3, Oct 2025)
- Evidence collection pipeline (flake8, pylint, bandit, pip-audit, git-churn, coverage)
- CLI (Typer) with 40+ commands
- MCP server with 12+ tools
- Route discovery from OpenAPI specs and Next.js App Router
- Risk assessment engine with CUJ integration
- Test generation: Behave BDD, pytest stubs, test data via Faker
- Reporting: Markdown, HTML dashboard
- Web UI with WebSocket updates
- Target/workspace management system
- FastAPI REST API for evidence/runs

## Future Directions

- Broader language support (Go, Ruby, Rust route parsers)
- Custom risk rule authoring via YAML
- Test coverage gap analysis from JUnit + source mapping
- Parallel test execution across runners
- RAG-powered context-aware test generation
