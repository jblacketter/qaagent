# Review Cycle: test-framework-gen (impl)

## Metadata
- **Phase:** test-framework-gen
- **Type:** impl
- **Started:** 2026-02-08
- **Lead:** claude
- **Reviewer:** codex

## Reference
- Plan: `docs/phases/test-framework-gen.md`
- Round 1 handoff: `docs/handoffs/test-framework-gen_impl_handoff.md`
- Key files:
  - `src/qaagent/generators/base.py` — BaseGenerator ABC + GenerationResult
  - `src/qaagent/generators/llm_enhancer.py` — LLMTestEnhancer (6 methods)
  - `src/qaagent/generators/playwright_generator.py` — PlaywrightGenerator
  - `src/qaagent/generators/validator.py` — TestValidator
  - `src/qaagent/generators/unit_test_generator.py` — enhanced, extends BaseGenerator
  - `src/qaagent/generators/behave_generator.py` — enhanced, extends BaseGenerator
  - `src/qaagent/commands/generate_cmd.py` — `e2e`, `all` commands
  - `src/qaagent/commands/report_cmd.py` — `plan-run --generate`
  - `src/qaagent/config/models.py` — PlaywrightSuiteSettings
  - `src/qaagent/templates/playwright/` — 7 Jinja2 templates
  - `tests/unit/generators/` — 112 tests total

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Phase 2 (Test Framework Generation Engine) implementation complete — 3 milestones delivered:

**2A: Generator Infrastructure + LLM Enhancement** — `BaseGenerator` ABC unifies all generator constructors. `GenerationResult` replaces raw dict returns. `LLMTestEnhancer` provides 6 fragment-generation methods with template fallbacks. `validate_python_syntax()` catches broken code before writing.

**2B: PlaywrightGenerator + `generate all`** — Full Playwright TypeScript project generation from routes/risks/CUJs. `PlaywrightSuiteSettings` config model with browsers/auth/cuj_path. `generate e2e` and `generate all` commands. Summary table output.

**2C: Validation Pipeline + End-to-End Polish** — `TestValidator` validates Python/TypeScript/Gherkin with LLM fix loop. Integrated into all 3 generators. `plan-run --generate` flag for end-to-end pipeline.

112 generator tests pass (0.99s). 0 regressions. 4 pre-existing failures unchanged.

### Reviewer
**Action:** REQUEST_CHANGES

**Verdict:** 4 issues found (2 HIGH, 2 MEDIUM). See `docs/handoffs/test-framework-gen_impl_feedback.md`.

1. **[HIGH]** Playwright config emits wrong device keys (`Chromium Desktop` vs `Desktop Chrome`)
2. **[HIGH]** Happy-path unit tests use literal `{pet_id}` placeholders instead of concrete values
3. **[MEDIUM]** LLM edge-case dicts not normalized to scalars before parametrized template
4. **[MEDIUM]** PlaywrightGenerator instantiates TestValidator but never calls it

---

## Round 2

### Lead
**Action:** SUBMIT_FOR_REVIEW

All 4 issues accepted. Fix plan incorporated into phase doc (`docs/phases/test-framework-gen.md` → Revision History). Implementation changes:

1. **Playwright device keys** — Add `BROWSER_DEVICE_MAP` in `PlaywrightGenerator`, pass mapped device name to template. Update `playwright.config.ts.j2` to use `{{ device_name }}` directly.
2. **Happy-path sample paths** — Add `sample_path` field to happy-path case dict in `_create_test_cases()`. Replace `{param}` with concrete values (e.g., `1`). Update template to use `case.sample_path`.
3. **Edge-case normalization** — In `_generate_invalid_params()`, flatten LLM-returned dicts to extract first scalar value from `params`. Template fallback (scalars) unchanged.
4. **Playwright validation** — Call `self._validator.validate_typescript(path)` after each `_render_file()` in `generate()`. Append warnings to `result.warnings`.

New/updated tests for all 4 fixes.

### Reviewer
**Action:** APPROVE

Approved. All four Round 1 blockers are resolved in code and covered by updated tests:

1. Playwright device mapping now uses valid keys (`Desktop Chrome`, `Desktop Firefox`, `Desktop Safari`).
2. Happy-path parameterized-route tests now render concrete sample paths (`case.sample_path`).
3. LLM edge-case dict output is normalized to scalar values before template interpolation.
4. Playwright generator now validates generated `.ts` files and surfaces warnings in `GenerationResult`.

No blocking issues remain for this implementation cycle.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: lead
ROUND: 2
STATE: approved
<!-- /CYCLE_STATUS -->
