# Phase: Test Framework Generation Engine

## Status
- [x] Planning
- [x] In Review
- [x] Approved
- [x] Implementation
- [x] Implementation Review
- [x] Complete

## Roles
- Lead: claude
- Reviewer: codex
- Arbiter: Human

## Summary
**What:** Transform qaagent from a tool that generates test *stubs* into one that generates complete, runnable test frameworks. Given a QA analysis (routes, risks, strategy), produce a full Playwright project, pytest suite, or Behave project that a developer can run immediately.
**Why:** This is the key differentiator - closing the loop from "QA plan" to "executable tests." The current generators produce templates with TODOs; this phase makes them real.
**Depends on:** Phase 1 (Modernization) - specifically the multi-provider LLM and Pydantic models

## Implementation Note

Implementation was completed prior to formal plan review cycle. The lead implemented the full phase (3 milestones) based on a detailed implementation plan. The implementation is now ready for codex implementation review.

## Milestones

Phase 2 is split into 3 milestones, each independently valuable and testable.

### Milestone 2A: Generator Infrastructure + LLM Enhancement
Common generator base (`BaseGenerator` ABC), LLM-powered test intelligence (`LLMTestEnhancer`), syntax validation. After this, `generate unit-tests` and `generate behave` produce significantly better output when LLM is available.

### Milestone 2B: PlaywrightGenerator + `generate all`
Full Playwright TypeScript E2E test generation from routes + CUJs. Unified `generate all` command. `PlaywrightSuiteSettings` config model.

### Milestone 2C: Validation Pipeline + End-to-End Polish
`TestValidator` for Python/TypeScript/Gherkin validation with LLM fix loop. Integration into all generators. `plan-run --generate` flag for end-to-end pipeline.

---

## Scope

### In Scope
1. **BaseGenerator ABC** - Uniform constructor and `GenerationResult` return type for all generators
2. **LLMTestEnhancer** - LLM-powered fragment generation (assertions, edge cases, test bodies, code fixing)
3. **PlaywrightGenerator** - Generate complete Playwright+TypeScript project from UI routes and CUJs
4. **TestValidator** - Python/TypeScript/Gherkin validation with LLM fix loop
5. **Enhanced pytest API Generator** - LLM-derived assertions and edge cases, syntax validation
6. **Enhanced Behave Generator** - LLM-powered step definitions and response assertions (no TODOs)
7. **Config-Driven Generation** - `PlaywrightSuiteSettings`, `generate all` reads suite enable flags
8. **`generate e2e`** and **`generate all`** commands
9. **`plan-run --generate`** - End-to-end: discover -> assess -> generate -> run -> report

### Out of Scope
- Test execution/orchestration (Phase 3)
- Jest/Vitest JavaScript test generation (future)
- Visual regression test generation
- Performance test generation (Locust already works)

## Technical Approach

### Design Decisions
1. **LLM generates fragments, not full files.** Templates own file structure; LLM fills in smart parts (assertions, edge cases, CUJ flows). This keeps generation reliable when LLM is unavailable.
2. **BaseGenerator unifies constructors.** All generators accept `(routes, risks, output_dir, base_url, project_name, llm_settings)`. Backward-compat preserved on existing generators.
3. **Playwright targets TypeScript.** Matches the proven demoapp pattern and is the standard for Playwright projects.
4. **`generate all` reads `.qaagent.yaml` suite enables.** Each suite (unit, behave, e2e, data) has an `enabled` flag.
5. **Validation before writing.** `ast.parse()` for Python, optional `tsc --noEmit` for TS, structural check for Gherkin. Invalid code gets LLM fix attempt before writing.

## Files Created
- `src/qaagent/generators/base.py` — BaseGenerator ABC + GenerationResult + validate_python_syntax()
- `src/qaagent/generators/llm_enhancer.py` — LLMTestEnhancer (6 methods, all with fallbacks)
- `src/qaagent/generators/playwright_generator.py` — PlaywrightGenerator
- `src/qaagent/generators/validator.py` — TestValidator
- `src/qaagent/templates/playwright/` — 7 Jinja2 templates (package.json, playwright.config.ts, auth.setup.ts, smoke.spec.ts, api.spec.ts, cuj.spec.ts, config.ts)
- `tests/unit/generators/test_base.py` — 15 tests
- `tests/unit/generators/test_llm_enhancer.py` — 15 tests
- `tests/unit/generators/test_playwright_generator.py` — 12 tests
- `tests/unit/generators/test_validator.py` — 18 tests

## Files Modified
- `src/qaagent/generators/unit_test_generator.py` — extends BaseGenerator, LLM integration, TestValidator
- `src/qaagent/generators/behave_generator.py` — extends BaseGenerator, LLM integration, TestValidator
- `src/qaagent/generators/__init__.py` — exports new classes
- `src/qaagent/config/models.py` — added PlaywrightSuiteSettings
- `src/qaagent/commands/generate_cmd.py` — added `e2e`, `all` commands, LLM settings passthrough
- `src/qaagent/commands/report_cmd.py` — added `--generate` flag to plan-run
- `tests/unit/generators/test_unit_test_generator.py` — updated for GenerationResult (`.files` accessor)
- `tests/unit/generators/test_behave_generator.py` — updated for GenerationResult
- `tests/fixtures/cli_snapshots/pre_split_commands.json` — added `all`, `e2e` to generate subcommands

## Success Criteria
- [x] `validate_python_syntax()` catches invalid code before writing
- [x] `generate unit-tests` with `llm.enabled: true` produces schema-derived assertions (mocked test)
- [x] `generate behave` with LLM produces step definitions without TODO placeholders (mocked test)
- [x] Template fallback still works when LLM is unavailable
- [x] `GenerationResult.stats` reports test count and file count
- [x] All existing generator tests pass unchanged (after `.files` accessor update)
- [x] `generate e2e` produces a Playwright project with valid TypeScript structure
- [x] Generated `playwright.config.ts` uses correct Playwright device keys *(R1 fix)*
- [x] CUJ-driven tests include meaningful flows (LLM) or structured TODOs (fallback)
- [x] `generate all` orchestrates unit + behave + e2e + data based on config enable flags
- [x] Smoke tests cover all UI routes; API tests cover all API routes
- [x] Generated Python always passes `ast.parse()` (or is LLM-fixed)
- [x] Happy-path tests for parameterized routes use concrete sample values *(R1 fix)*
- [x] LLM edge-case dicts are normalized before template rendering *(R1 fix)*
- [x] PlaywrightGenerator runs TestValidator on generated .ts files *(R1 fix)*
- [x] Validation warnings surface in CLI output
- [x] `plan-run --generate` flag added for end-to-end pipeline
- [x] No regressions in existing tests (same 4 pre-existing failures)

## Test Results
- **118 generator tests** — all pass (112 original + 6 new for R1 fixes)
- **0 regressions** introduced
- **4 pre-existing failures** unchanged (MCP server x2, API workflow x1, route dedup x1)

## Risks
- **LLM prompt reliability:** Generated code may not parse. Mitigated by validate-retry loop (max 2 attempts) and template fallback.
- **Template/LLM fragment mixing:** Injecting LLM strings into Jinja2 templates needs careful escaping. Tested at boundary.
- **Breaking existing generator APIs:** `UnitTestGenerator(routes, base_url)` -> `BaseGenerator(routes, risks, output_dir, ...)`. Backward-compat preserved (old positional args still work).
- **TypeScript quality:** No `ast.parse` equivalent without Node. Optional `tsc` check, or skip with warning if node unavailable.

---

## Revision History

### Round 1 Feedback (codex, 2026-02-08)

**Verdict:** REQUEST CHANGES — 4 issues identified.

#### Issue 1: [HIGH] Playwright config uses wrong device keys
- **Location:** `templates/playwright/playwright.config.ts.j2:28,40`
- **Problem:** Template emits `devices['Chromium Desktop']` etc. via `{{ browser | capitalize }} Desktop`. Playwright's device registry uses `Desktop Chrome`, `Desktop Firefox`, `Desktop Safari`.
- **Fix:** Add a `BROWSER_DEVICE_MAP` dict in `PlaywrightGenerator` mapping browser names to correct Playwright device keys. Pass the mapped device name into the template instead of using the `| capitalize` filter.
- **Files:** `playwright_generator.py` (add map, pass to template), `playwright.config.ts.j2` (use mapped key directly)
- **Tests:** Add test asserting generated config contains `Desktop Chrome` not `Chromium Desktop`.

#### Issue 2: [HIGH] Happy-path unit tests use literal `{pet_id}` placeholders
- **Location:** `templates/unit/test_class_enhanced.py.j2:47` (and line 24)
- **Problem:** Template renders `api_client.get("{{ case.route.path }}")` which outputs `/pets/{pet_id}` literally for parameterized routes. Happy-path tests should use concrete sample values.
- **Fix:** In `_create_test_cases()`, generate a `sample_path` field for happy-path cases by replacing `{param}` with a concrete sample value (e.g., `1` for IDs, `"test"` for strings). Template uses `case.sample_path` instead of `case.route.path` for happy-path GET/DELETE.
- **Files:** `unit_test_generator.py` (add `sample_path` to happy_path case dict), `test_class_enhanced.py.j2` (use `case.sample_path` where appropriate)
- **Tests:** Add test asserting generated happy-path test for `/pets/{pet_id}` uses `/pets/1` not `/pets/{pet_id}`.

#### Issue 3: [MEDIUM] LLM edge-case dict shape doesn't match parametrized template
- **Location:** `unit_test_generator.py:231`, `test_class_enhanced.py.j2:90,102`
- **Problem:** `generate_edge_cases()` returns `list[dict]` with keys `{name, params, expected_status, description}`. Template treats each item as a scalar `invalid_param` and interpolates directly into the URL path. When LLM returns dicts, generated code is `"/pets/{'name': 'negative_id', ...}"`.
- **Fix:** In `_generate_invalid_params()`, after getting LLM edge cases, normalize to extract scalar param values. Extract the first value from each case's `params` dict. Template fallback already returns scalars `[-1, 0, "invalid", None, ""]`, so only the LLM path needs normalization.
- **Files:** `unit_test_generator.py` (normalize LLM edge cases in `_generate_invalid_params()`)
- **Tests:** Add test verifying that LLM-returned dicts are flattened to scalar param values.

#### Issue 4: [MEDIUM] PlaywrightGenerator doesn't call TestValidator
- **Location:** `playwright_generator.py:57,66`
- **Problem:** `TestValidator` is instantiated but `generate()` never calls it. Generated `.ts` files are written without validation, despite the plan claiming validation is integrated into all generators.
- **Fix:** After rendering each `.ts` file via `_render_file()`, call `self._validator.validate_typescript(path)` and append any warnings/errors to `result.warnings`.
- **Files:** `playwright_generator.py` (add validation calls in `generate()`), `test_playwright_generator.py` (verify warnings surface)
- **Tests:** Add test with mocked `npx` unavailable confirming a warning is appended to result.
