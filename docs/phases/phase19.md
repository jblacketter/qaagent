# Phase 19: Enhanced Product Documentation Engine

## Summary

Extend the documentation engine to produce richer, human-readable product documentation. Add new data models for app overview, user roles, and user journeys. Enhance the doc generator to extract this information from the codebase heuristically. Update the React UI with new sections to display this enhanced documentation.

## Scope

### P1: Extend Documentation Models
- **File:** `src/qaagent/doc/models.py`
- Add new models:
  - `UserRole`: `id`, `name`, `description`, `permissions` (list of strings), `associated_features` (list of feature IDs)
  - `UserJourney`: `id`, `name`, `description`, `actor` (role ID or "anonymous"), `steps` (list of `JourneyStep`), `feature_ids`, `priority` (high/medium/low)
  - `JourneyStep`: `order`, `action` (human-readable), `page_or_route`, `expected_outcome`
- Add fields to `AppDocumentation`:
  - `app_overview: str = ""` — human-readable overview (paragraph form, not technical)
  - `user_roles: List[UserRole] = Field(default_factory=list)`
  - `user_journeys: List[UserJourney] = Field(default_factory=list)`
  - `tech_stack: List[str] = Field(default_factory=list)` — detected technologies

### P2: Enhance Doc Generator — App Overview & Tech Stack
- **Files:** `src/qaagent/doc/generator.py`, `src/qaagent/doc/prose.py`
- Add `_detect_tech_stack(source_dir)` function: scan `package.json`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod` etc. to detect frameworks and languages.
- Add new template function `_template_app_overview()` that generates a 2-3 paragraph human-readable narrative of the application.
- **`summary` vs `app_overview` contract:**
  - `summary` — concise one-paragraph synopsis (one-liner style, existing behavior preserved). Always populated. Template-generated deterministically.
  - `app_overview` — richer multi-paragraph narrative describing app purpose, capabilities, and tech stack in human-readable prose. Always populated via template fallback. When LLM is available, LLM refines the template output; when unavailable, template output is used as-is.
  - Both fields are always populated (never empty string after generation). No duplication — `summary` is a brief headline, `app_overview` is the detailed body.

### P3: Enhance Doc Generator — User Roles
- **File:** `src/qaagent/doc/generator.py` (new helper module: `src/qaagent/doc/role_discoverer.py`)
- Heuristic role discovery from:
  - Auth-related routes (login, register, invite) → infer "User" role
  - Admin routes (`/admin/*`, role-checking middleware) → infer "Admin" role
  - API key / token routes → infer "API Consumer" role
  - If no auth routes found → single "User (unauthenticated)" role
- Map roles to features based on auth requirements on routes.

### P4: Enhance Doc Generator — User Journeys
- **File:** `src/qaagent/doc/cuj_discoverer.py` (extend existing) or new `src/qaagent/doc/journey_builder.py`
- Build on existing CUJ patterns (auth_flow, crud_lifecycle, search_filter, file_upload, payment_checkout).
- Convert discovered CUJs into human-readable `UserJourney` objects with step-by-step descriptions.
- Add new patterns: onboarding flow, settings/profile management, data export.
- Each journey step gets a human-readable `action` and `expected_outcome`.

### P5: Update React UI — Enhanced Doc Display
- **File:** `src/qaagent/dashboard/frontend/src/types/index.ts`
  - Add new TypeScript interfaces: `UserRole`, `UserJourney`, `JourneyStep`.
  - Add new fields to existing `AppDocumentation` interface: `app_overview`, `user_roles`, `user_journeys`, `tech_stack`.
- **File:** `src/qaagent/dashboard/frontend/src/pages/AppDoc.tsx`
  - Add new sections to the doc page:
    - **App Overview**: Rich text section at the top displaying `app_overview` (multi-paragraph narrative). Falls back to `summary` if `app_overview` is empty.
    - **Tech Stack**: Pill/badge display of detected technologies.
    - **User Roles**: Card grid showing each role with permissions and associated features.
    - **User Journeys**: Expandable accordion/timeline showing each journey with steps.
  - All new sections hidden gracefully when their data arrays are empty.
- **File:** `src/qaagent/dashboard/frontend/src/services/api.ts`
  - No interface changes needed here (types live in `types/index.ts`), but verify API methods pass new fields through correctly.

### P6: Tests
- Unit tests for role discoverer.
- Unit tests for journey builder (extend existing CUJ tests).
- Contract test: verify new fields appear in `GET /api/doc` response.
- **Legacy payload backward-compatibility test:** verify that `AppDocumentation.model_validate()` (or `load_documentation()`) successfully loads an `appdoc.json` file that was generated before Phase 19 (i.e., missing `app_overview`, `user_roles`, `user_journeys`, `tech_stack` fields). Assert all new fields take their defaults and existing fields are preserved.

## Files Changed

| File | Change |
|------|--------|
| `src/qaagent/doc/models.py` | New models: UserRole, UserJourney, JourneyStep; new fields on AppDocumentation |
| `src/qaagent/doc/generator.py` | Tech stack detection, wire role/journey discoverers |
| `src/qaagent/doc/prose.py` | Enhanced app overview template |
| `src/qaagent/doc/role_discoverer.py` | NEW — heuristic role discovery |
| `src/qaagent/doc/journey_builder.py` | NEW — convert CUJs to user journeys |
| `src/qaagent/doc/cuj_discoverer.py` | Add new CUJ patterns |
| `src/qaagent/dashboard/frontend/src/types/index.ts` | New TS interfaces: UserRole, UserJourney, JourneyStep; new fields on AppDocumentation |
| `src/qaagent/dashboard/frontend/src/pages/AppDoc.tsx` | New UI sections |
| `tests/unit/doc/test_role_discoverer.py` | NEW — role discovery tests |
| `tests/unit/doc/test_journey_builder.py` | NEW — journey builder tests |
| `tests/unit/doc/test_legacy_compat.py` | NEW — backward-compatibility test for old appdoc.json payloads |

## Success Criteria

1. `generate_documentation()` populates `app_overview`, `tech_stack`, `user_roles`, and `user_journeys` fields.
2. Existing doc tests still pass (backward compatible — new fields have defaults).
3. React UI shows new sections when data is present, gracefully hides them when empty.
4. Frontend builds successfully.

## Dependencies

- Phase 18 must be completed first (landing page and bug fix).
