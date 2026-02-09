# Handoff: Test Framework Generation — Implementation Review (Round 1)

**Date:** 2026-02-08
**From:** claude (Lead)
**To:** codex (Reviewer)
**Type:** Implementation Review — Phase 2 complete (3 milestones)

## Context

Phase 2 (Test Framework Generation Engine) was implemented in full based on a detailed plan. Implementation was done prior to a formal plan review cycle due to workflow timing. All 3 milestones are complete and passing tests.

The phase doc `docs/phases/test-framework-gen.md` has been updated with the full implementation details.

## What Was Implemented

### Milestone 2A: Generator Infrastructure + LLM Enhancement

**New files:**
- `src/qaagent/generators/base.py` — `BaseGenerator` ABC with uniform constructor `(routes, risks, output_dir, base_url, project_name, llm_settings)`. `GenerationResult` dataclass with `files`, `stats`, `warnings`, `llm_used`. `validate_python_syntax()` via `ast.parse()`.
- `src/qaagent/generators/llm_enhancer.py` — `LLMTestEnhancer` with 6 methods:
  - `enhance_assertions(route, response_schema)` → assertion lines
  - `generate_edge_cases(route, risks)` → edge case dicts
  - `generate_test_body(route, test_type)` → function body
  - `refine_code(code, error_message)` → fixed code
  - `generate_step_definitions(route, risk)` → Behave then steps
  - `generate_response_assertions(route)` → Behave body assertion steps
  - All methods have template fallbacks. All strip markdown fences from LLM output.

**Modified files:**
- `unit_test_generator.py` — Now extends `BaseGenerator`. When LLM enabled: uses `enhance_assertions()` for schema-derived assertions, `generate_edge_cases()` for parametrized tests. After rendering, validates with `TestValidator.validate_and_fix()`. Returns `GenerationResult`.
- `behave_generator.py` — Now extends `BaseGenerator`. When LLM enabled: `_baseline_scenario()` adds response body assertions instead of TODO comments. `_scenario_from_risk()` generates real step definitions instead of TODO placeholders. Validates Gherkin structure. Returns `GenerationResult`.
- `commands/generate_cmd.py` — Reads `active_profile.llm` and passes `llm_settings` to all generators. Prints LLM usage and warnings in summary. Added `--risks-file` option to `unit-tests` command.

### Milestone 2B: PlaywrightGenerator + `generate all`

**New files:**
- `src/qaagent/generators/playwright_generator.py` — Generates complete Playwright + TypeScript project:
  ```
  <output_dir>/
    package.json
    playwright.config.ts
    tests/
      auth.setup.ts          (if auth configured)
      smoke.spec.ts          (UI route smoke tests)
      api/<resource>.spec.ts (API tests via request context)
      <cuj-slug>.spec.ts     (one per CUJ)
    src/
      config.ts              (env-based config)
  ```
  Separates routes into UI (GET non-/api) and API. Groups API routes by resource. CUJ tests use LLM for meaningful flows or template fallback with structured TODOs.
- `src/qaagent/templates/playwright/` — 7 Jinja2 templates for the full project
- `src/qaagent/config/models.py` — Added `PlaywrightSuiteSettings(SuiteSettings)` with `browsers: List[str]`, `auth_setup: bool`, `cuj_path: Optional[str]`. Updated `TestsSettings.e2e` type.

**New commands:**
- `generate e2e` — Full Playwright project from routes/risks/CUJs. Reads CUJ file from config or default locations.
- `generate all` — Orchestrates all enabled suites (unit, behave, e2e, data) from `.qaagent.yaml` config. Prints summary table with file/test counts and LLM usage per suite.

### Milestone 2C: Validation Pipeline + End-to-End Polish

**New files:**
- `src/qaagent/generators/validator.py` — `TestValidator` with:
  - `validate_python(code)` → `ValidationResult` via `ast.parse()`
  - `validate_typescript(path)` → `ValidationResult` (runs `npx tsc --noEmit` if available, warning if not)
  - `validate_gherkin(text)` → `ValidationResult` (checks Feature/Scenario structure)
  - `validate_and_fix(code, language, enhancer, max_retries=2)` → `(code, was_fixed)`

**Modified files:**
- All three generators now use `TestValidator` for validation before writing
- `commands/report_cmd.py` — `plan-run` now accepts `--generate` flag that runs `generate all` before the existing run pipeline

## Test Results

```
tests/unit/generators/test_base.py              15 passed
tests/unit/generators/test_llm_enhancer.py       15 passed
tests/unit/generators/test_playwright_generator.py 12 passed
tests/unit/generators/test_validator.py          18 passed
tests/unit/generators/test_behave_generator.py    1 passed
tests/unit/generators/test_unit_test_generator.py 17 passed
tests/unit/generators/test_data_generator.py     34 passed
─────────────────────────────────────────────────────────
Total:                                          112 passed in 0.99s
```

**Full suite:** Same 4 pre-existing failures, 0 new regressions.

## Design Decisions Worth Reviewing

1. **Fragment-based LLM generation** — LLM never produces whole files. Templates own structure, LLM fills in assertions/edge cases/steps. This means generation always works (fallback) and LLM just makes it better.

2. **Lazy LLM init** — `_get_enhancer()` pattern on each generator. LLMTestEnhancer is only instantiated if LLM is enabled AND a method is actually called. No LLM imports at module level.

3. **Backward compatibility** — `UnitTestGenerator(routes, base_url)` still works (new params are optional with defaults). `BehaveGenerator(routes, risks, output_dir)` still works. Existing call sites in `generate_cmd.py` just pass extra kwargs. Existing tests only needed `.files` accessor update.

4. **TestValidator skip behavior** — TypeScript validation returns `valid=True` with a warning when `npx` isn't available, rather than failing. This means `generate e2e` works without Node installed.

## Review Focus Areas

1. **BaseGenerator design** — Is the ABC constructor signature reasonable? Any missing common functionality?
2. **LLMTestEnhancer prompt quality** — Review the system/user prompts in each method. Are the fallbacks adequate?
3. **PlaywrightGenerator route separation** — UI routes = GET non-/api, API routes = everything else. Is this heuristic sufficient?
4. **`generate all` orchestration** — Does the suite enable/disable logic match expectations from `.qaagent.yaml`?
5. **Backward compatibility** — Do the existing generator APIs still work for all existing callers?

---
*Implementation handoff. Reviewer: use `/handoff-review impl test-framework-gen` to review.*
