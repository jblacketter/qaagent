# Phase 4: Enhanced Analysis — Implementation Log

## Milestone 4A: Python Framework Route Discovery

### Files Created
1. `src/qaagent/discovery/base.py` — `FrameworkParser` ABC + `RouteParam` internal model + `_normalize_route()`
2. `src/qaagent/discovery/fastapi_parser.py` — `FastAPIParser` with AST-based route extraction, `include_router()` prefix tracking, `Depends()` auth detection
3. `src/qaagent/discovery/flask_parser.py` — `FlaskParser` with Blueprint prefix composition, Flask converter type mapping
4. `src/qaagent/discovery/django_parser.py` — `DjangoParser` with URL pattern parsing + DRF ViewSet/router detection
5. `tests/unit/discovery/test_fastapi_parser.py` — 13 tests
6. `tests/unit/discovery/test_flask_parser.py` — 11 tests
7. `tests/unit/discovery/test_django_parser.py` — 11 tests
8. `tests/unit/discovery/test_route_normalization.py` — 10 cross-module regression tests
9. `tests/fixtures/discovery/{fastapi_project,flask_project,django_project}/` — Sample source files

### Files Modified
10. `src/qaagent/discovery/__init__.py` — Exports all parsers + `get_framework_parser()` factory
11. `src/qaagent/analyzers/route_discovery.py` — Added `discover_from_source()`, wired auto-detection into `discover_routes()`
12. `src/qaagent/commands/analyze_cmd.py` — Imported `discover_from_source`
13. `src/qaagent/repo/validator.py` — Added `get_framework_parser()` method to `RepoValidator`

### Key Implementation Decisions
- **Per-decorator router tracking**: FastAPI and Flask parsers track which variable (`router`, `app`, `bp`) owns each decorator, avoiding incorrect prefix application when multiple routers exist in one file.
- **`RouteParam` serialization**: Internal `RouteParam` objects are serialized to dicts via `.model_dump()` in `_normalize_route()`, preserving the existing `Dict[str, List[dict]]` shape.
- **Django two-strategy parsing**: URL patterns via regex, ViewSets via AST class inspection.

### Test Results
- 45 discovery tests pass
- Cross-module regression: source routes work through `risk_assessment`, `unit_test_generator`, `openapi_gen`

---

## Milestone 4B: Pluggable Risk Rule Engine

### Files Created
14. `src/qaagent/analyzers/rules/__init__.py` — Package with `default_registry()` factory
15. `src/qaagent/analyzers/rules/base.py` — `RiskRule` ABC (two-tier: `evaluate()` + `evaluate_all()`) + `RiskRuleRegistry`
16. `src/qaagent/analyzers/rules/security.py` — 8 rules (SEC-001 through SEC-008)
17. `src/qaagent/analyzers/rules/performance.py` — 4 rules (PERF-001 through PERF-004)
18. `src/qaagent/analyzers/rules/reliability.py` — 4 rules (REL-001 through REL-004), REL-003 and REL-004 are aggregate
19. `tests/unit/analyzers/test_rules.py` — 36 tests for individual rules
20. `tests/unit/analyzers/test_rule_registry.py` — 10 tests for registry + backward compat

### Files Modified
21. `src/qaagent/analyzers/risk_assessment.py` — Replaced hardcoded rules with `default_registry().run_all()`. Added `disabled_rules` parameter.

### Key Implementation Decisions
- **PERF-002 schema check**: Only flags when param has an explicit `schema` block without `maximum` — avoids false positives on source-parser params that have `type` at top level.
- **Existing 3 rules preserved as SEC-001, PERF-001, REL-001** with identical behavior.

### Test Results
- 46 analyzer rule tests pass
- Backward compatibility verified: `assess_risks()` produces identical output for same inputs

---

## Milestone 4C: CI/CD Template Generation

### Files Created
22. `src/qaagent/generators/cicd_generator.py` — `CICDGenerator` class + `SuiteFlags` model
23. `src/qaagent/templates/cicd/github_actions.yml.j2` — GitHub Actions template with bootstrap steps
24. `src/qaagent/templates/cicd/gitlab_ci.yml.j2` — GitLab CI template with stages
25. `tests/unit/generators/test_cicd_generator.py` — 16 tests

### Files Modified
26. `src/qaagent/generators/__init__.py` — Exports `CICDGenerator`, `SuiteFlags`
27. `src/qaagent/commands/generate_cmd.py` — Added `generate ci` command with `--platform`, `--project-name`, `--framework` flags
28. `tests/fixtures/cli_snapshots/pre_split_commands.json` — Added `ci` to generate subcommands

### Key Implementation Decisions
- **Bootstrap steps in all templates**: `qaagent config init . --template <framework> --name <project>` + `qaagent use <project>` + `BASE_URL` from CI secrets/variables.
- **Valid YAML output**: Both templates produce parseable YAML (verified by `yaml.safe_load` tests).
- **Auto-detect from profile**: `generate ci` reads framework and suite flags from active profile when not specified.

### Test Results
- 16 CI/CD generator tests pass
- Generated YAML is valid for all supported frameworks

---

## Summary

| Metric | Count |
|--------|-------|
| New files | 28 |
| Modified files | 8 |
| New tests | 127 |
| Pre-existing failures | 4 (unchanged) |
| New regressions | 0 |
