# Phase 2: Autonomous QA Agent - Handoff to Codex

**Date**: 2025-10-22
**From**: Claude (Analysis) + User
**To**: Codex (Implementation)

---

## TL;DR

Build an **AI-powered autonomous QA Agent** that does 80% of a Senior QA Engineer's work:
1. 🔍 Auto-discovers routes (UI + API)
2. 🧪 Generates BDD (Behave) + unit tests
3. 🛡️ Assesses security, performance, reliability risks
4. 📊 Creates executive dashboards and technical reports

**Timeline**: 3-4 weeks, incremental delivery

---

## User's Vision

> "I want a QA Agent that does as much work as possible for me as a Senior QA engineer and SDET. It should analyze the functional routes in UI and API, and suggest API and UI tests in Python Behave and unit tests. It should analyze the system for non-functional issues such as risks, security, performance. It should create detailed reports."

---

## Phase 2 Structure

### **Week 1: Intelligent Analysis Engine**
```bash
qaagent analyze-all --target http://localhost:8000 --source src/
```

**Delivers**:
- Route discovery (API from OpenAPI + code, UI from crawling)
- Risk assessment (security, performance, reliability)
- Test strategy generation (what to test, how much, priorities)

**Output**: JSON analysis + Markdown strategy

### **Week 2: Test Generation Engine**
```bash
qaagent generate-tests --strategy strategy.yaml
```

**Delivers**:
- BDD/Behave feature files with scenarios
- Step definitions (Python)
- Unit tests (pytest) from source code analysis
- Test data/fixtures

**Output**: Complete test suites ready to run

### **Week 3: Comprehensive Scanning**
```bash
qaagent scan-all --target http://localhost:8000 --source src/
```

**Delivers**:
- Security scanning (OWASP ZAP, Bandit)
- Performance analysis (slow endpoints, N+1 queries)
- Code quality (complexity, coverage)
- Executive dashboard (HTML)

**Output**: Multi-format reports (HTML dashboard, MD, PDF)

### **Week 4: Polish & Integration**
- CI/CD integration
- Documentation and examples
- Error handling and edge cases

---

## Key Technical Decisions Needed

### 1. LLM Strategy
**Question**: Local Ollama or Cloud API (Claude/GPT)?

**Claude's Recommendation**: Hybrid
- **Ollama (7B-14B)** for: Test naming, simple generation, edge cases
- **Claude API** for: Complex analysis, risk assessment, recommendations
- Keep templates as fallback (no LLM required)

**Reasoning**:
- Ollama good enough for 70% of tasks
- Cloud API for complex reasoning (costs ~$0.01-0.10 per analysis)
- Always functional without LLM

### 2. BDD Framework
**Confirmed**: Python Behave ✅

Generate this style:
```gherkin
Feature: User Management
  Scenario: Create user
    Given I have valid user data
    When I POST to "/api/users"
    Then the response status should be 201
```

### 3. Security Scanner
**Recommendation**: Start with Bandit (Python), add ZAP later

**Reasoning**:
- Bandit: Easy integration, Python-native
- ZAP: More comprehensive but complex setup
- Phase 2 can add ZAP in Week 3

### 4. Architecture Pattern
**Recommendation**: Plugin-based analyzers

```python
# Clean, extensible
class RouteDiscoverer:
    def discover_from_openapi(spec): ...
    def discover_from_fastapi(code): ...
    def discover_from_django(code): ...

class RiskAssessor:
    def assess_security(routes): ...
    def assess_performance(routes): ...
    def assess_reliability(routes): ...
```

---

## Proposed File Structure

```
src/qaagent/
├── analyzers/
│   ├── route_discovery.py       # Find all routes
│   ├── risk_assessment.py       # Security/perf/reliability
│   ├── strategy_generator.py    # Test strategy
│   └── code_analyzer.py         # Static analysis
│
├── generators/
│   ├── bdd_generator.py         # Behave features
│   ├── unit_test_generator.py  # pytest tests
│   ├── test_data_generator.py  # Fixtures
│   └── templates/               # Jinja2 templates
│       ├── feature.j2
│       ├── steps.j2
│       └── unit_test.j2
│
├── scanners/
│   ├── security_scanner.py      # Bandit, ZAP
│   ├── performance_scanner.py   # Profile, analyze
│   └── quality_scanner.py       # Coverage, complexity
│
├── reporters/
│   ├── dashboard_reporter.py    # HTML dashboard
│   ├── executive_reporter.py    # Summary for stakeholders
│   └── technical_reporter.py    # Detailed for engineers
│
└── cli.py  # Add new commands
```

---

## Week 1 Implementation Details

### Task 1.1: Route Discovery (2-3 days)

**Files to create**:
- `src/qaagent/analyzers/route_discovery.py`
- `src/qaagent/analyzers/models.py` (Pydantic models)

**Core function**:
```python
@dataclass
class Route:
    path: str
    method: str
    auth_required: bool
    params: dict
    response_schema: dict
    risk_level: str  # low, medium, high
    test_priority: str  # low, medium, high

def discover_routes(
    target_url: Optional[str],
    openapi_spec: Optional[str],
    source_code: Optional[Path]
) -> list[Route]:
    """Discover all routes from multiple sources."""
    routes = []

    if openapi_spec:
        routes.extend(discover_from_openapi(openapi_spec))

    if source_code:
        routes.extend(discover_from_code(source_code))

    if target_url:
        # Runtime discovery via crawling
        routes.extend(discover_from_runtime(target_url))

    return deduplicate_routes(routes)
```

**CLI command**:
```python
@app.command("discover-routes")
def discover_routes_cmd(
    target: Optional[str] = typer.Option(None),
    openapi: Optional[str] = typer.Option(None),
    source: Optional[str] = typer.Option(None),
    out: str = typer.Option("routes.json")
):
    """Discover all API and UI routes."""
    routes = discover_routes(target, openapi, Path(source) if source else None)
    Path(out).write_text(json.dumps([r.__dict__ for r in routes], indent=2))
    print(f"[green]Discovered {len(routes)} routes → {out}[/green]")
```

### Task 1.2: Risk Assessment (2 days)

**Core function**:
```python
@dataclass
class Risk:
    category: str  # security, performance, reliability
    severity: str  # low, medium, high, critical
    route: str
    description: str
    recommendation: str
    cwe_id: Optional[str] = None

def assess_risks(routes: list[Route]) -> list[Risk]:
    """Assess security, performance, and reliability risks."""
    risks = []

    # Security risks
    for route in routes:
        if not route.auth_required and route.method in ["POST", "PUT", "DELETE"]:
            risks.append(Risk(
                category="security",
                severity="high",
                route=route.path,
                description="Mutation endpoint without authentication",
                recommendation="Add authentication middleware"
            ))

    # Performance risks
    for route in routes:
        if "pagination" not in route.params and route.method == "GET":
            risks.append(Risk(
                category="performance",
                severity="medium",
                route=route.path,
                description="Missing pagination on list endpoint",
                recommendation="Add limit/offset or cursor pagination"
            ))

    # LLM-enhanced analysis (if available)
    if llm_available():
        risks.extend(llm_analyze_risks(routes))

    return sorted(risks, key=lambda r: severity_score(r.severity), reverse=True)
```

### Task 1.3: Strategy Generator (1-2 days)

**Output YAML**:
```yaml
test_strategy:
  summary:
    total_routes: 45
    critical_routes: 12
    high_risk_areas: 8

  recommended_tests:
    unit_tests:
      count: ~150
      focus: business_logic, validation

    integration_tests:
      count: ~50
      focus: api_contracts, database

    e2e_tests:
      count: ~15
      critical_flows:
        - user_registration_and_login
        - checkout_process
        - admin_user_management

  priorities:
    - name: Authentication flows
      reason: No tests exist, critical for security
      tests_needed: 25

    - name: Payment processing
      reason: High business risk
      tests_needed: 30
```

---

## Week 2 Implementation Details

### Task 2.1: BDD Generator (3 days)

**Template** (`templates/feature.j2`):
```jinja2
Feature: {{ feature_name }}
  As a {{ role }}
  I want to {{ goal }}
  So that {{ benefit }}

  Background:
    Given the API is running at "{{ base_url }}"
    {% if requires_auth %}And I have valid authentication credentials{% endif %}

  {% for scenario in scenarios %}
  Scenario: {{ scenario.name }}
    {% for step in scenario.steps %}
    {{ step }}
    {% endfor %}
  {% endfor %}

  {% if edge_cases %}
  Scenario Outline: {{ feature_name }} edge cases
    Given I have <condition>
    When I {{ action }}
    Then {{ expected_result }}

    Examples:
      | condition | action | expected_result |
      {% for case in edge_cases %}
      | {{ case.condition }} | {{ case.action }} | {{ case.result }} |
      {% endfor %}
  {% endif %}
```

### Task 2.2: Unit Test Generator (2-3 days)

**Uses AST parsing**:
```python
import ast

def generate_unit_tests(source_file: Path) -> str:
    """Generate pytest tests from source code."""
    tree = ast.parse(source_file.read_text())

    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

    tests = []
    for func in functions:
        tests.append(generate_function_tests(func))

    for cls in classes:
        tests.append(generate_class_tests(cls))

    return render_template("unit_test.j2", tests=tests)
```

---

## Integration with Existing Code

### Extend CLI (`cli.py`)
Add new command group:
```python
analyze_app = typer.Typer(help="Intelligent analysis commands")
app.add_typer(analyze_app, name="analyze")

@analyze_app.command("all")
def analyze_all(...):
    """Run full analysis."""
    pass

@analyze_app.command("routes")
def analyze_routes(...):
    """Discover routes only."""
    pass
```

### Extend MCP Server (`mcp_server.py`)
Add new tools:
```python
@mcp.tool()
def analyze_application(args: AnalyzeArgs):
    """Discover routes and assess risks."""
    return {"routes": [...], "risks": [...]}

@mcp.tool()
def generate_tests(args: GenerateTestsArgs):
    """Generate BDD and unit tests."""
    return {"features": [...], "unit_tests": [...]}
```

---

## Questions for Codex

Before starting implementation:

1. **LLM Integration**: Should we start with Ollama local-only, or add Claude API support from day 1?

2. **Route Discovery**: Which should we prioritize?
   - OpenAPI/Swagger (easiest, most reliable)
   - Code analysis (FastAPI, Flask, Django)
   - Runtime crawling (most complete but slowest)

3. **Test Generation Approach**:
   - Template-based with LLM enhancement (fast, good enough)
   - Pure LLM (flexible but slower, costs money)
   - Hybrid (templates for structure, LLM for scenarios)

4. **Week 1 vs Week 2-3**: Should we finish Week 1 completely before starting Week 2, or start generating tests earlier?

5. **Dependencies**: Any concerns about adding:
   - `behave` (BDD framework)
   - `bandit` (security scanner)
   - `ast` / `libcst` (code parsing)
   - `playwright` for crawling (already have it)

---

## Success Criteria

### Week 1
- [ ] Can discover all routes from petstore example
- [ ] Identifies 5+ risks in petstore
- [ ] Generates sensible test strategy YAML

### Week 2
- [ ] Generates valid Behave features
- [ ] Generates runnable unit tests
- [ ] Tests actually pass when run

### Week 3
- [ ] Security scan finds known issues
- [ ] Performance analysis identifies slow endpoints
- [ ] Dashboard looks professional

---

## Next Steps

1. **Codex Review**: Read full plan in [PHASE_2_AUTONOMOUS_QA_AGENT.md](PHASE_2_AUTONOMOUS_QA_AGENT.md)
2. **Technology Decisions**: Answer the 5 questions above
3. **Implementation Approach**: Propose how you'd build Week 1
4. **Iteration**: Claude and you discuss until agreement
5. **Build**: Start with Week 1, demo early and often

---

**Ready?** This is an ambitious but achievable plan that will make QA Agent truly autonomous! 🚀
