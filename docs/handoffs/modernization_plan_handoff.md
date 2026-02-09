# Handoff: Modernization - Plan Review

**Date:** 2026-02-07
**From:** claude (Lead)
**To:** codex (Reviewer)
**Type:** Planning Review

## Summary
Two-phase plan for qaagent's next evolution. Phase 1 (Modernization) cleans up technical debt that has accumulated over 3 sprints. Phase 2 (Test Framework Generation Engine) is the key feature: transforming qaagent from a tool that produces test stubs into one that generates complete, runnable test projects.

## What Needs Review
- Overall roadmap strategy (4 phases)
- Phase 1 (Modernization) technical approach and scope
- Phase 2 (Test Framework Gen) architecture and feasibility
- Whether Phase 1 and Phase 2 ordering is correct (or should we tackle test gen first)
- Open questions in both phase plans

## Context: Project Analysis (Feb 2026)

### Current Architecture
The project has ~60 Python source files in `src/qaagent/`:
- **CLI** (`cli.py`, 2048 lines) - monolithic Typer app with 30+ commands
- **Analyzers** - route discovery, risk assessment, strategy gen, CUJ config, evidence reader, recommender, coverage mapper, risk aggregator
- **Collectors** - flake8, pylint, bandit, pip-audit, git-churn, coverage (all produce evidence)
- **Generators** - Behave BDD, unit tests (pytest), test data (Faker)
- **Config** - dual system (legacy flat TOML + new YAML profiles)
- **Evidence** - run manager, writer, ID generator, models
- **MCP Server** - 12+ tools exposed via FastMCP
- **API** - FastAPI routes for evidence, runs, repositories
- **UI** - Web UI, dashboard, enhanced dashboard HTML

### Key Issues Identified
1. **cli.py monolith** - every command in one file makes navigation/maintenance hard
2. **Legacy config** - `config/legacy.py` has `LegacyQAAgentConfig` still used by CLI
3. **LLM locked to Ollama** - `llm.py` only supports local Ollama; no cloud provider support
4. **Test generators are template-only** - BehaveGenerator and UnitTestGenerator produce stubs with TODOs like "assert response body structure" but don't generate real assertions
5. **No Playwright test generation** - config has `e2e` settings but generation is `enabled=False` and unimplemented
6. **Mixed data model patterns** - Route/Risk are dataclasses with hand-written to_dict(); config uses Pydantic

### What Works Well
- Evidence pipeline is clean and extensible (collector → evidence writer → manifest)
- Risk assessment with CUJ weighting is unique and valuable
- Target/workspace system for managing multiple projects
- MCP server integration gives qaagent a strong AI-agent story

## Specific Questions for Reviewer
1. Is the CLI split approach the right granularity? (8 command modules vs fewer larger ones)
2. For LLM multi-provider: should we use `litellm` as an abstraction layer instead of hand-rolling provider adapters?
3. Is TypeScript Playwright the right choice for E2E generation, or should we generate Python Playwright tests for consistency?
4. Should Phase 1 and Phase 2 be done sequentially, or can parts be parallelized?
5. For the LLM test intelligence layer - is the proposed interface (generate_assertions, generate_edge_cases, generate_user_flow) the right abstraction?

## Phase Plan Locations
- Roadmap: `docs/ROADMAP.md`
- Phase 1: `docs/phases/modernization.md`
- Phase 2: `docs/phases/test-framework-gen.md`

## Review Checklist
- [ ] Technical approach is sound
- [ ] Scope is appropriate (not too big/small)
- [ ] Success criteria are testable
- [ ] No major risks overlooked
- [ ] File structure makes sense
- [ ] Dependencies are identified

## Response Instructions
Please provide feedback in `docs/handoffs/modernization_plan_feedback.md` using the feedback template.

---
*Handoff created by lead. Reviewer: use `/handoff-review plan modernization` to begin review.*
