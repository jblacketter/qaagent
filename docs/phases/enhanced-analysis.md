# Phase: Enhanced Analysis

## Status
- [x] Planning
- [x] In Review
- [x] Approved (round 3)
- [x] Implementation
- [ ] Implementation Review
- [ ] Complete

## Roles
- Lead: claude
- Reviewer: codex
- Arbiter: Human

## Summary
**What:** Add FastAPI, Flask, and Django route discovery via AST parsing. Build a pluggable risk rule engine with a library of 15+ rules. Generate CI/CD pipeline templates. After this phase, qaagent can analyze the three most popular Python web frameworks out of the box and produce actionable CI pipelines for discovered projects.

**Why:** Route discovery is currently limited to OpenAPI specs and Next.js source. This blocks qaagent from analyzing ~70% of Python API projects that don't ship an OpenAPI spec. The risk assessment has only 3 hardcoded rules, limiting its usefulness. CI/CD templates close the loop from analysis to automated testing.

**Depends on:** Phase 3 (Test Orchestration) — specifically RunOrchestrator and the evidence pipeline.

## Milestones

### Milestone 4A: Python Framework Route Discovery
AST-based route parsers for FastAPI, Flask, and Django. Extends `analyze routes` to auto-detect framework and extract routes from source code.

### Milestone 4B: Pluggable Risk Rule Engine
Replace hardcoded risk rules with a registry-based system. Ship 15+ rules covering OWASP top-10 patterns, performance anti-patterns, and reliability concerns.

### Milestone 4C: CI/CD Template Generation
Generate GitHub Actions and GitLab CI pipelines from project analysis. Templates include route discovery, test generation, test execution, and reporting steps.

---

## Scope

### In Scope
1. **FastAPI route parser** — AST-based extraction of `@app.get()`, `@router.post()`, path params, dependencies, response models
2. **Flask route parser** — AST-based extraction of `@app.route()`, `@bp.route()`, Blueprint composition, URL rules
3. **Django route parser** — Parse `urlpatterns`, class-based views, DRF `@action` decorators, ViewSet routes
4. **Framework auto-detection** — Extend existing `repo/validator.py` heuristics to select the right parser
5. **Risk rule registry** — `RiskRule` ABC with `evaluate(route) -> Optional[Risk]`, pluggable via config
6. **Rule library** — 15+ rules: auth gaps, CORS, input validation, rate limiting, pagination, deprecation, etc.
7. **CI/CD templates** — GitHub Actions and GitLab CI YAML generation from Jinja2 templates
8. **`analyze routes` enhancement** — Auto-select parser based on detected framework
9. **`generate ci` command** — New CLI command for CI/CD template generation
10. **ApiRecord population** — Wire discovered routes into the evidence system via `ApiRecord`

### Out of Scope
- Express.js / non-Python framework parsers (future)
- Runtime crawling / dynamic route discovery
- Custom risk rule authoring UI
- Jenkins / Azure DevOps pipeline templates
- OpenAPI spec generation from discovered routes (exists but not wired — separate effort)

## Technical Approach

### Design Decisions

1. **AST parsing, not regex.** Python's `ast` module gives reliable extraction of decorators, arguments, and function signatures. Regex is fragile for Python code (multiline decorators, nested calls). The Next.js parser uses regex because TS/JS AST requires Node.js; Python AST is stdlib.

2. **One parser class per framework.** Each implements `FrameworkParser` ABC with `parse(source_dir: Path) -> List[Route]`. Parsers are selected by `detect_framework()` in `repo/validator.py`.

3. **Two-tier risk rule evaluation.** `RiskRule` ABC has two evaluation methods: `evaluate(route: Route) -> Optional[Risk]` for per-route rules, and `evaluate_all(routes: List[Route]) -> List[Risk]` for aggregate/global rules. Per-route rules (e.g., "unauthenticated mutation") implement `evaluate()`. Aggregate rules (e.g., "missing health check endpoint", "inconsistent naming") implement `evaluate_all()`. The default `evaluate_all()` just calls `evaluate()` per route, so per-route rules only need to implement one method. `RiskRuleRegistry.run_all()` calls `evaluate_all()` on every rule, passing the full route list.

4. **CI/CD templates include bootstrap steps.** Generated pipelines do NOT assume a preconfigured active target. Templates include: (a) `qaagent config init . --template <framework> --name <project>` to create the profile, (b) `qaagent use <project>` to activate it, (c) environment variable injection for `BASE_URL` and secrets. This makes pipelines runnable from a clean CI runner. The `generate ci` command accepts `--project-name` and `--framework` to populate these steps.

5. **Route model normalization contract — preserves current `Route.params` shape.** The core `Route` model (`analyzers/models.py`) is NOT changed. `Route.params` remains `Dict[str, Any]`, used as `Dict[str, List[dict]]` grouped by location key (`"path"`, `"query"`, `"header"`, `"body"`). Each element dict has at minimum `{"name": str}`, optionally `{"type": str, "required": bool}`. This is the shape that OpenAPI discovery already produces and that all consumers rely on (`route.params.get("query", [])`, `route.params["path"]`, `route.params.items()`). Source parsers use `RouteParam` as an internal validation model during parsing, then serialize via `.model_dump()` into the existing dict shape within `_normalize_route()`. The `_normalize_route()` method also enforces: `path` uses `{param}` syntax (not `:param` or `<param>`), `auth_required` is explicitly set (not None). Cross-module regression tests verify that source-discovered routes work correctly through risk assessment, test generation, and OpenAPI generation — output must be equivalent to OpenAPI-discovered routes.

6. **CI/CD templates are Jinja2.** Same pattern as test generators. Templates accept project metadata (framework, test suites, base_url) and produce valid YAML.

7. **ApiRecord bridges discovery to evidence.** Each discovered route becomes an `ApiRecord` in the evidence system, enabling traceability from route → risk → test → result.

8. **Backward-compatible `analyze routes`.** Existing OpenAPI and Next.js discovery paths unchanged. Framework parsers are additive — if an OpenAPI spec exists, it takes priority; source parsing supplements it.

---

## Milestones — Detailed

### Milestone 4A: Python Framework Route Discovery

#### Files to Create

1. **`src/qaagent/discovery/__init__.py`** — Package init, exports
2. **`src/qaagent/discovery/base.py`** — `FrameworkParser` ABC + `RouteParam` internal model
   ```python
   class RouteParam(BaseModel):
       """Internal validation model for parser output. Serialized to dict for Route.params."""
       name: str
       type: str = "string"        # string, integer, uuid, etc.
       required: bool = True

   class FrameworkParser(ABC):
       framework_name: str

       @abstractmethod
       def parse(self, source_dir: Path) -> List[Route]: ...

       @abstractmethod
       def find_route_files(self, source_dir: Path) -> List[Path]: ...

       def _normalize_route(self, path: str, method: str, params: Dict[str, List[RouteParam]],
                            auth_required: bool, **kwargs) -> Route:
           """Build a Route with normalized fields.

           - Converts :param/<param> to {param} in path
           - Serializes RouteParam objects to dicts via .model_dump()
           - Ensures auth_required is explicit (not None)
           - Returns Route compatible with existing consumers
           """
           normalized_path = re.sub(r"[<:](\w+)>?", r"{\1}", path)
           serialized_params = {
               location: [p.model_dump() for p in param_list]
               for location, param_list in params.items()
           }
           return Route(
               path=normalized_path, method=method, auth_required=auth_required,
               params=serialized_params, **kwargs,
           )
   ```

3. **`src/qaagent/discovery/fastapi_parser.py`** — `FastAPIParser(FrameworkParser)`
   - Uses `ast.parse()` to walk Python files for:
     - `@app.get("/path")`, `@router.post("/path")` decorators
     - Path parameters from type hints: `item_id: int` → `{item_id}`
     - `Depends()` for auth detection (common: `Depends(get_current_user)`)
     - Response model from `response_model=` kwarg
     - Tags from `tags=["tag"]` kwarg
     - APIRouter prefix composition (`router = APIRouter(prefix="/api/v1")`)
     - `include_router()` call chain for prefix accumulation
   - Confidence: 0.85 (AST is reliable but can't resolve dynamic routes)

4. **`src/qaagent/discovery/flask_parser.py`** — `FlaskParser(FrameworkParser)`
   - AST extraction of:
     - `@app.route("/path", methods=["GET", "POST"])` decorators
     - `@bp.route()` on Blueprints
     - `Blueprint("name", __name__, url_prefix="/api")` prefix tracking
     - `app.register_blueprint(bp, url_prefix="/v1")` prefix composition
     - `login_required` / custom auth decorator detection
   - Confidence: 0.80

5. **`src/qaagent/discovery/django_parser.py`** — `DjangoParser(FrameworkParser)`
   - Two parsing strategies:
     - **URL patterns**: Parse `urlpatterns = [path("api/", include(...))]` from `urls.py` files
     - **DRF ViewSets**: Detect `ModelViewSet`, `@action(detail=True)`, `DefaultRouter` registrations
   - Uses AST for decorator/class extraction + regex for `urlpatterns` list parsing (mixed approach since `path()` calls are often dynamic)
   - Confidence: 0.75 (Django URL routing is more complex)

6. **`tests/unit/discovery/__init__.py`**
7. **`tests/unit/discovery/test_fastapi_parser.py`** — Tests with sample FastAPI source files
8. **`tests/unit/discovery/test_flask_parser.py`** — Tests with sample Flask source files
9. **`tests/unit/discovery/test_django_parser.py`** — Tests with sample Django source files
10. **`tests/fixtures/discovery/`** — Sample source files for each framework

#### Files to Modify

11. **`src/qaagent/discovery/nextjs_parser.py`** — Extend `FrameworkParser` ABC (backward-compat)
12. **`src/qaagent/analyzers/route_discovery.py`** — Add `discover_from_source(source_dir, framework)` function that selects and runs the appropriate parser
13. **`src/qaagent/commands/analyze_cmd.py`** — Wire `analyze routes --source-dir` to use framework parsers when no OpenAPI spec available
14. **`src/qaagent/repo/validator.py`** — Return framework name (not just bool) from detection, add `get_framework_parser()` factory

#### Files to Create (additional)

- **`tests/unit/discovery/test_route_normalization.py`** — Cross-module regression tests: source-discovered routes through risk assessment, test generation, and OpenAPI generation

#### Success Criteria
- [ ] `FastAPIParser.parse()` extracts routes with methods, params, auth, tags from sample FastAPI app
- [ ] `FlaskParser.parse()` extracts routes with Blueprint prefix composition
- [ ] `DjangoParser.parse()` extracts URL patterns and DRF ViewSet routes
- [ ] `analyze routes --source-dir examples/petstore-api` discovers FastAPI routes
- [ ] All parsers produce `Route` objects with normalized `{param}` syntax, `Dict[str, List[dict]]` params (grouped by location), and explicit `auth_required`
- [ ] `Route.params` shape from source parsers matches OpenAPI discovery output (`route.params.get("query", [])`, `route.params["path"]` work identically)
- [ ] Cross-module regression: source-discovered routes pass through `risk_assessment`, `unit_test_generator`, and `openapi_gen` without errors and produce equivalent output to OpenAPI-discovered routes
- [ ] Existing OpenAPI and Next.js discovery paths unchanged (no regression)
- [ ] Next.js parser output after `FrameworkParser` adoption is byte-equivalent to current output for the same input
- [ ] Framework auto-detection selects correct parser
- [ ] Next.js parser updated to extend `FrameworkParser` ABC and emit normalized routes

---

### Milestone 4B: Pluggable Risk Rule Engine

#### Files to Create

15. **`src/qaagent/analyzers/rules/__init__.py`** — Package init, exports
16. **`src/qaagent/analyzers/rules/base.py`** — `RiskRule` ABC + `RiskRuleRegistry`
    ```python
    class RiskRule(ABC):
        rule_id: str           # e.g., "SEC-001"
        category: RiskCategory
        severity: RiskSeverity
        title: str
        description: str

        def evaluate(self, route: Route) -> Optional[Risk]:
            """Per-route evaluation. Override for single-route rules."""
            return None

        def evaluate_all(self, routes: List[Route]) -> List[Risk]:
            """Aggregate evaluation. Default: call evaluate() per route.
            Override for global rules (e.g., missing health check, naming consistency)."""
            risks = []
            for route in routes:
                risk = self.evaluate(route)
                if risk:
                    risks.append(risk)
            return risks

    class RiskRuleRegistry:
        def register(self, rule: RiskRule) -> None: ...
        def run_all(self, routes: List[Route], disabled: List[str] = None) -> List[Risk]:
            """Run evaluate_all() on every enabled rule, passing full route list."""
            ...
    ```

17. **`src/qaagent/analyzers/rules/security.py`** — Security rules (8 rules):
    - `SEC-001`: Unauthenticated mutation endpoints
    - `SEC-002`: Missing CORS configuration indicators
    - `SEC-003`: Path traversal risk (file-related params without validation)
    - `SEC-004`: Mass assignment risk (PUT/PATCH without explicit field list)
    - `SEC-005`: Missing rate limiting on auth endpoints
    - `SEC-006`: Sensitive data in query params (password, token, secret)
    - `SEC-007`: Missing input validation on POST/PUT bodies
    - `SEC-008`: Admin endpoints without elevated auth

18. **`src/qaagent/analyzers/rules/performance.py`** — Performance rules (4 rules):
    - `PERF-001`: Missing pagination on collection endpoints
    - `PERF-002`: Unbounded query params (no max limit)
    - `PERF-003`: N+1 risk on nested resource endpoints
    - `PERF-004`: Missing caching headers on GET endpoints

19. **`src/qaagent/analyzers/rules/reliability.py`** — Reliability rules (4 rules):
    - `REL-001`: Deprecated operations still active (per-route)
    - `REL-002`: Missing error response schemas (per-route)
    - `REL-003`: Inconsistent path naming conventions (aggregate — overrides `evaluate_all()`)
    - `REL-004`: Missing health check endpoint (aggregate — overrides `evaluate_all()`)

20. **`tests/unit/analyzers/test_rules.py`** — Tests for all 16 rules
21. **`tests/unit/analyzers/test_rule_registry.py`** — Registry tests (register, evaluate, disable)

#### Files to Modify

22. **`src/qaagent/analyzers/risk_assessment.py`** — Replace hardcoded rules with `RiskRuleRegistry.run_all()`. Keep existing 3 rules as `SEC-001`, `PERF-001`, `REL-001`.
23. **`src/qaagent/config/models.py`** — Wire `RiskAssessmentSettings.severity_thresholds` (currently unused)

#### Success Criteria
- [ ] `RiskRuleRegistry` loads and runs all enabled rules
- [ ] `RiskAssessmentSettings.disable_rules` disables specific rule IDs
- [ ] Existing 3 rules produce identical output (no regression)
- [ ] 16 rules ship with clear documentation (rule_id, description, remediation)
- [ ] `analyze risks` uses the registry (no behavior change for users)
- [ ] Rules are unit-tested with representative Route fixtures

---

### Milestone 4C: CI/CD Template Generation

#### Files to Create

24. **`src/qaagent/generators/cicd_generator.py`** — `CICDGenerator`
    - Accepts: framework, test suites (unit/behave/e2e), base_url, python version, project_name
    - Generates: GitHub Actions YAML or GitLab CI YAML
    - Templates are Jinja2 with conditional sections based on detected capabilities
    - All generated pipelines include bootstrap steps that work from a clean CI runner:
      1. `pip install qaagent`
      2. `qaagent config init . --template <framework> --name <project>`
      3. `qaagent use <project>`
      4. Environment variable injection for `BASE_URL` via CI secrets

25. **`src/qaagent/templates/cicd/github_actions.yml.j2`** — GitHub Actions template
    - Matrix: Python versions, OS
    - Steps: checkout, setup-python, install deps, **qaagent bootstrap** (config init + use), route discovery, risk assessment, test generation, test execution (via RunOrchestrator), report generation
    - Conditional: Playwright install if e2e enabled, Behave if BDD enabled
    - Secrets: `BASE_URL` from `${{ secrets.BASE_URL }}`, optional `API_TOKEN`

26. **`src/qaagent/templates/cicd/gitlab_ci.yml.j2`** — GitLab CI template
    - Stages: setup, analyze, generate, test, report
    - Setup stage: qaagent bootstrap (config init + use)
    - Variables: `BASE_URL` from CI/CD variables
    - Artifacts: JUnit XML, coverage, HTML reports

27. **`tests/unit/generators/test_cicd_generator.py`** — Template rendering tests, including bootstrap step validation

#### Files to Modify

28. **`src/qaagent/commands/generate_cmd.py`** — Add `generate ci` command with `--platform`, `--project-name`, `--framework` flags
29. **`src/qaagent/generators/__init__.py`** — Export `CICDGenerator`

#### Success Criteria
- [ ] `generate ci --platform github` produces valid GitHub Actions YAML
- [ ] `generate ci --platform gitlab` produces valid GitLab CI YAML
- [ ] Generated pipelines include bootstrap steps (`config init`, `use`) that work without preconfigured active target
- [ ] Generated pipelines inject `BASE_URL` and secrets from CI environment
- [ ] Templates are configurable (Python version, test suites, base_url, project name)
- [ ] Generated YAML passes basic schema validation
- [ ] CI-mode test verifies pipeline renders correctly for each supported framework

---

## Risks

- **AST parsing complexity:** FastAPI's `include_router()` chain and Django's `include()` nesting can be arbitrarily deep. Mitigated by setting a max depth (3 levels) and logging warnings for unresolved routes.
- **Framework version differences:** FastAPI 0.95+ vs 0.100+ have different patterns. Django 4.x vs 5.x URL patterns differ. Mitigated by targeting current stable versions and documenting supported ranges.
- **Risk rule false positives:** Heuristic rules may flag non-issues. Mitigated by confidence scores and the `disable_rules` config.
- **CI/CD template drift:** Generated pipelines may not work with all project structures. Mitigated by generating comments explaining each step and making templates easily customizable.

## Revision History

### Round 1 Feedback (codex, 2026-02-09)

**Verdict:** REQUEST CHANGES — 3 blocking issues.

1. **[HIGH] Risk rule engine contract inconsistent** — Resolved: Introduced two-tier evaluation. `RiskRule` has `evaluate(route)` for per-route rules and `evaluate_all(routes)` for aggregate rules. Default `evaluate_all()` delegates to `evaluate()` per route. Aggregate rules (`REL-003`, `REL-004`) override `evaluate_all()`. `RiskRuleRegistry.run_all()` always calls `evaluate_all()` on every rule.

2. **[HIGH] CI/CD templates assume active profile** — Resolved: Added design decision 4 (bootstrap steps). Generated pipelines include `qaagent config init` + `qaagent use` steps. `generate ci` accepts `--project-name` and `--framework` flags. Templates inject `BASE_URL` from CI secrets/variables.

3. **[HIGH] Route model normalization under-specified** — Resolved: Added design decision 5 (normalization contract). All parsers must produce `{param}` syntax, typed `RouteParam` list, explicit `auth_required`. `FrameworkParser._normalize_route()` enforces invariants. Cross-module regression tests added to 4A. Next.js parser updated to extend ABC.

### Round 2 Feedback (codex, 2026-02-09)

**Verdict:** REQUEST CHANGES — 1 blocking issue.

1. **[HIGH] Route.params contract incompatible with current model** — Resolved: Design decision 5 now explicitly preserves the current `Route.params` shape (`Dict[str, List[dict]]` grouped by location). Core `Route` model in `analyzers/models.py` is NOT changed. `RouteParam` is an internal validation model used by parsers during extraction; `_normalize_route()` serializes via `.model_dump()` into the existing dict shape. All current consumers (`route.params.get("query", [])`, `route.params["path"]`, `route.params.items()`) continue to work without migration. Success criteria updated with explicit output-equivalence checks for OpenAPI and Next.js paths.

**Non-blocking suggestions addressed:**
- Naming consistency: `RiskRuleRegistry.run_all()` used consistently across design sections and file-change notes (was mixed with `evaluate_all`).
- Explicit Next.js/OpenAPI equivalence criterion added: "Next.js parser output after FrameworkParser adoption is byte-equivalent to current output for the same input."

---

## Verification

After each milestone:
1. `python -m pytest tests/unit/discovery/ -q` — discovery tests pass (4A)
2. `python -m pytest tests/unit/analyzers/ -q` — risk rule tests pass (4B)
3. `python -m pytest tests/unit/generators/test_cicd_generator.py -q` — CI/CD tests pass (4C)
4. `python -m pytest tests/ -q --tb=no` — no regressions
5. Manual: `qaagent analyze routes --source-dir examples/petstore-api` — discovers FastAPI routes (4A)
6. Manual: `qaagent generate ci --platform github` — produces valid YAML (4C)
