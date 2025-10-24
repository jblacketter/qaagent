# Week 2 Handoff to Codex - Phase 2

**Date**: 2025-10-23
**From**: Claude (Analysis Agent)
**To**: Codex (Implementation Agent)
**Status**: Ready for Implementation

---

## Quick Summary

**Week 1 Status**: ✅ **APPROVED** - All tests passing (see [WEEK1_VALIDATION_REPORT.md](WEEK1_VALIDATION_REPORT.md))

**Week 2 Goal**: Build on the Intelligent Analysis Engine with:
1. **Configuration Management** - Multi-app support with `.qaagent.yaml` profiles
2. **BDD/Behave Test Generation** - Given/When/Then scenarios from routes/risks
3. **Unit Test Generation** - pytest-based unit tests with mocks
4. **Test Data Synthesis** - Realistic fixtures from schemas
5. **Week 1 Improvements** - Tool descriptions, refined risk rules, grouped priorities

**Why This Matters**: User wants to test real production apps like SonicGrid (Next.js app at `~/projects/sonic/sonicgrid`), not just petstore. Need configuration system to manage multiple target applications.

---

## The User's Problem

User has multiple applications to test:
- **SonicGrid**: `~/projects/sonic/sonicgrid` or `https://github.com/spherop/sonicgrid` (Next.js, 30+ API routes)
- **Petstore**: `examples/petstore-api/` (FastAPI, 12 routes)
- **Future apps**: Various stacks, local and remote

Current QA Agent requires explicit `--openapi` paths for every command. User wants:
```bash
# This workflow
qaagent config init ~/projects/sonic/sonicgrid
qaagent use sonicgrid
qaagent generate behave   # Uses sonicgrid config automatically
qaagent generate unit-tests
qaagent generate test-data

# Instead of this
qaagent analyze routes --openapi ~/projects/sonic/sonicgrid/some/path/openapi.yaml --out routes.json
qaagent analyze risks --routes-file routes.json --out risks.json
# ... repeat for every app
```

---

## Key Architecture Decisions

### 1. Configuration Files

**`.qaagent.yaml`** (in target app root, e.g., `~/projects/sonic/sonicgrid/.qaagent.yaml`):
- Describes the application (name, type, version)
- Environments (dev, staging, prod) with base URLs
- OpenAPI spec location or auto-generation settings
- Test output directories
- Auth configuration
- Risk assessment rules customization

**`~/.qaagent/targets.yaml`** (global registry):
- Lists all registered target applications
- Maps target names to paths/URLs
- Tracks currently active target

### 2. New CLI Commands

```bash
# Configuration
qaagent config init [PATH]      # Create .qaagent.yaml
qaagent config validate         # Validate config
qaagent config show             # Show current config

# Target management
qaagent targets list            # List all targets
qaagent targets add <name> <path>
qaagent targets remove <name>
qaagent use <name>              # Switch active target

# Test generation (NEW)
qaagent generate behave         # BDD tests
qaagent generate unit-tests     # pytest unit tests
qaagent generate test-data      # Test fixtures
```

### 3. Test Generation Strategy

**BDD/Behave Tests** (from risks):
- Input: Routes + Risks (from Week 1)
- Output: `.feature` files with Given/When/Then scenarios
- Focus: High-risk scenarios (auth, pagination, input validation)
- Example: "Scenario: Unauthenticated user attempts to create pet"

**Unit Tests** (from routes):
- Input: Routes + OpenAPI schemas
- Output: pytest test classes with mocks
- Focus: Route handlers, validation, edge cases
- Example: `test_create_pet_invalid_data()`

**Test Data** (from schemas):
- Input: OpenAPI schemas or database schemas
- Output: JSON/YAML fixtures with realistic data
- Uses: Faker library for names, emails, dates, etc.
- Example: 50 realistic pet records with names, species, ages

---

## Implementation Roadmap

### Day 1: Configuration System ⭐ **START HERE**

**Priority**: This is the foundation - everything else depends on it.

**Tasks**:
1. Create `src/qaagent/config/` package
2. Implement models (`models.py`):
   - `QAAgentConfig` (Pydantic model for `.qaagent.yaml`)
   - `TargetRegistry` (model for `~/.qaagent/targets.yaml`)
3. Implement loader (`loader.py`):
   - `find_config()` - Walk up directory tree to find `.qaagent.yaml`
   - `load_config()` - Load and validate config
4. Implement manager (`manager.py`):
   - `TargetManager` class - Manage global registry
   - Methods: `list_targets()`, `add_target()`, `remove_target()`, `get_active()`, `set_active()`
5. Create config templates (`templates/config/`):
   - `nextjs.yaml` - Template for Next.js apps
   - `fastapi.yaml` - Template for FastAPI apps
   - `generic.yaml` - Fallback template
6. Implement CLI commands (in `cli.py`):
   - `config init/validate/show`
   - `targets list/add/remove`
   - `use <target>`
7. Write unit tests (`tests/unit/test_config_*.py`)

**Validation**:
```bash
# Should work by end of Day 1
qaagent config init examples/petstore-api --template fastapi
cat examples/petstore-api/.qaagent.yaml  # Should exist with sensible defaults
qaagent targets list  # Should show petstore
qaagent use petstore  # Should set as active
qaagent config show  # Should display config
```

### Day 2: Behave Test Generator

**Tasks**:
1. Create `src/qaagent/generators/behave_generator.py`
2. Create Jinja2 templates:
   - `templates/feature.j2` - For `.feature` files
   - `templates/steps.py.j2` - For step definitions
3. Implement `BehaveGenerator` class:
   - `generate_features()` - Create .feature files from risks
   - `generate_step_definitions()` - Create steps/*.py files
   - `_create_auth_scenario()` - Generate auth test scenarios
   - `_create_pagination_scenario()` - Generate pagination test scenarios
   - `_create_validation_scenario()` - Generate validation test scenarios
4. Add CLI command: `generate behave`
5. Write unit tests

**Validation**:
```bash
# Should work by end of Day 2
qaagent use petstore
qaagent generate behave --out tests/behave
ls tests/behave/features/  # Should have .feature files
ls tests/behave/steps/     # Should have step definitions
cat tests/behave/features/pets.feature  # Should have auth scenarios
```

### Day 3: Unit Test & Data Generators

**Tasks (Unit Tests)**:
1. Create `src/qaagent/generators/unit_test_generator.py`
2. Create template: `templates/pytest_class.py.j2`
3. Implement `UnitTestGenerator` class:
   - `generate_test_classes()` - Create test_*.py files
   - `generate_parametrize_tests()` - Create @pytest.mark.parametrize tests
   - `generate_mocks()` - Auto-generate mock objects
4. Add CLI command: `generate unit-tests`

**Tasks (Test Data)**:
1. Create `src/qaagent/generators/data_generator.py`
2. Add `faker` dependency
3. Implement `DataGenerator` class:
   - `generate()` - Generate N records from schema
   - `_generate_field()` - Smart field generation based on name and type
   - Support for JSON, YAML, CSV output
4. Add CLI command: `generate test-data`

**Validation**:
```bash
# Should work by end of Day 3
qaagent generate unit-tests --out tests/unit
pytest tests/unit/  # Should run (may fail but should execute)

qaagent generate test-data --model Pet --count 50 --out fixtures/
cat fixtures/pets.json  # Should have 50 realistic pet records
```

### Day 4: Week 1 Improvements + Integration Testing

**Week 1 Improvements**:
1. Add MCP tool descriptions (in `mcp_server.py`)
2. Refine risk assessment rules:
   - Don't flag `/health` for pagination
   - Don't flag single-resource GET requests (with path params)
3. Group duplicate priorities in strategy generator
4. Fix validation script to use venv python

**Integration Testing**:
1. Create `tests/integration/test_week2_full_workflow.py`
2. Test complete workflow:
   - Init config for petstore
   - Generate behave tests
   - Generate unit tests
   - Generate test data
   - Verify all outputs exist and are valid
3. Create `scripts/validate_week2.sh`

**Documentation**:
1. Update README with Week 2 features
2. Create tutorial: "Setting up SonicGrid for QA Agent"
3. Document configuration schema

---

## Detailed Specs

### Configuration Schema (`.qaagent.yaml`)

See [WEEK2_PLAN.md](WEEK2_PLAN.md) for complete schema. Key sections:

```yaml
project:
  name: "SonicGrid"
  type: "nextjs"

app:
  dev:
    base_url: "http://localhost:3000"
    start_command: "npm run dev"
    health_endpoint: "/api/health"

openapi:
  auto_generate: true  # For Next.js, generate from src/app/api/
  source_dir: "src/app/api"
  spec_path: ".qaagent/openapi.yaml"

tests:
  output_dir: "tests/qaagent"
  behave:
    enabled: true
    output_dir: "tests/qaagent/behave"
  unit:
    enabled: true
    output_dir: "tests/qaagent/unit"
    framework: "pytest"

risk_assessment:
  disable_rules:
    - "health_check_pagination"  # Don't flag /health for pagination
```

### Behave Test Generation

**Input**: Routes + Risks from Week 1

**Output Structure**:
```
tests/qaagent/behave/
├── features/
│   ├── pets.feature
│   ├── owners.feature
│   └── health.feature
├── steps/
│   ├── api_steps.py
│   ├── auth_steps.py
│   └── validation_steps.py
├── environment.py
└── behave.ini
```

**Example Feature** (from high-severity auth risk):
```gherkin
Feature: Pet Creation Security
  @security @high-risk
  Scenario: Unauthenticated user attempts to create pet
    Given I am not authenticated
    When I send a POST request to "/pets" with:
      """
      {"name": "Fluffy", "species": "cat", "age": 3}
      """
    Then the response status should be 401
```

**Generation Logic**:
- Group routes by resource (pets, owners, etc.)
- Create one .feature per resource
- Generate scenarios from high/critical severity risks
- Priority: Security risks → Performance risks → Reliability risks

### Unit Test Generation

**Input**: Routes from Week 1

**Output Structure**:
```
tests/qaagent/unit/
├── test_pets_api.py
├── test_owners_api.py
└── conftest.py
```

**Example Test Class**:
```python
class TestPetsAPI:
    def test_list_pets_empty(self):
        """Test GET /pets returns empty list"""
        with patch('server.db.get_pets') as mock:
            mock.return_value = []
            response = client.get("/pets")
            assert response.status_code == 200
            assert response.json() == []

    @pytest.mark.parametrize("invalid_age", [-1, 0, 200, "abc"])
    def test_create_pet_invalid_age(self, invalid_age):
        """Test POST /pets validates age"""
        response = client.post("/pets", json={
            "name": "Test", "species": "dog", "age": invalid_age
        })
        assert response.status_code == 422
```

**Generation Logic**:
- One test file per resource/route group
- For each route, generate:
  - Happy path test
  - Empty/null data test
  - Invalid data tests (parametrized)
  - Edge case tests (from schema constraints)

### Test Data Generation

**Input**: OpenAPI schemas

**Output**: JSON/YAML/CSV fixtures

**Smart Field Generation**:
- `name` → `faker.name()`
- `email` → `faker.email()`
- `age` → `random.randint(1, 100)`
- `created_at` → `faker.iso8601()`
- Enums → `random.choice(enum_values)`
- Use schema constraints (min, max, pattern)

---

## Dependencies to Add

```toml
[project.dependencies]
faker = ">=20.0.0"  # Test data generation
# jinja2, pyyaml already present
```

---

## Testing Requirements

### Unit Tests (pytest)

**Config System**:
- `test_load_config_from_file()` - Load valid .qaagent.yaml
- `test_find_config_walks_up_tree()` - Config discovery in parent dirs
- `test_config_validation_fails()` - Pydantic validation catches errors
- `test_target_manager_add_remove()` - Target registry CRUD

**Generators**:
- `test_generate_feature_from_route()` - .feature file generation
- `test_generate_auth_scenarios()` - Auth scenario generation
- `test_generate_pytest_class()` - pytest class generation
- `test_generate_test_data()` - Data generation from schema

### Integration Tests

**Full Workflow**:
```python
def test_week2_full_workflow():
    """Test complete Week 2 workflow with petstore"""
    # 1. Init config
    run("qaagent config init examples/petstore-api --template fastapi")
    assert Path("examples/petstore-api/.qaagent.yaml").exists()

    # 2. Register and activate target
    run("qaagent targets add petstore examples/petstore-api")
    run("qaagent use petstore")

    # 3. Generate behave tests
    run("qaagent generate behave --out /tmp/behave")
    assert Path("/tmp/behave/features/pets.feature").exists()
    assert "Scenario:" in Path("/tmp/behave/features/pets.feature").read_text()

    # 4. Generate unit tests
    run("qaagent generate unit-tests --out /tmp/unit")
    assert Path("/tmp/unit/test_pets_api.py").exists()
    assert "def test_" in Path("/tmp/unit/test_pets_api.py").read_text()

    # 5. Generate test data
    run("qaagent generate test-data --model Pet --count 10 --out /tmp/fixtures")
    data = json.loads(Path("/tmp/fixtures/pets.json").read_text())
    assert len(data) == 10
    assert "name" in data[0]
```

---

## Success Criteria

Week 2 is **COMPLETE** when:

**Configuration**:
- [x] `qaagent config init` creates valid `.qaagent.yaml` with detected project type
- [x] `qaagent targets list` shows all registered targets with active indicator
- [x] `qaagent use <target>` switches active target
- [x] Config auto-discovered when running commands in target directory

**Behave Generation**:
- [x] `qaagent generate behave` creates runnable .feature files
- [x] Generated scenarios match high-severity risks from Week 1
- [x] Step definitions are complete and importable
- [x] `behave tests/qaagent/behave` executes without import errors

**Unit Test Generation**:
- [x] `qaagent generate unit-tests` creates valid pytest files
- [x] Generated tests include happy path + edge cases
- [x] Tests use proper mocking patterns
- [x] `pytest tests/qaagent/unit` executes without syntax errors

**Test Data Generation**:
- [x] `qaagent generate test-data` creates realistic fixtures
- [x] Data matches OpenAPI schema constraints
- [x] Faker integration produces varied, realistic values
- [x] Multiple output formats supported (JSON, YAML, CSV)

**Week 1 Improvements**:
- [x] MCP tools have descriptions
- [x] Risk assessment doesn't flag health checks for pagination
- [x] Strategy priorities are consolidated (no duplicates)
- [x] Validation script uses venv python

**Testing**:
- [x] All unit tests pass
- [x] Integration test validates full workflow
- [x] Validation script (`scripts/validate_week2.sh`) passes

**Documentation**:
- [x] Configuration schema documented
- [x] Generator usage examples provided
- [x] Tutorial for SonicGrid setup created

---

## Important Notes

### For Next.js Apps (like SonicGrid)

Next.js doesn't have built-in OpenAPI specs. You'll need to:

**Option 1: Manual OpenAPI** (Week 2)
- User provides OpenAPI spec manually
- Config: `openapi.spec_path: "openapi.yaml"`

**Option 2: Route Discovery** (Week 3+)
- Parse `src/app/api/*/route.ts` files to extract routes
- Use AST parsing or runtime introspection
- Auto-generate OpenAPI spec

For Week 2, assume Option 1 (manual spec). Document that auto-generation for Next.js is planned for Week 3.

### Authentication in Generated Tests

Generated tests should have **TODO placeholders** for auth:

```python
@given('I am authenticated as "{username}"')
def step_authenticated(context, username):
    # TODO: Replace with actual auth token generation
    # Options:
    # 1. Call /api/auth/login with test credentials
    # 2. Use JWT library to generate token
    # 3. Read from environment variable
    context.headers = {"Authorization": f"Bearer fake-token-{username}"}
```

Document in generated tests that user needs to implement actual auth.

### Local vs Remote Repositories

**Week 2 Scope**: Local repositories only (`~/projects/sonic/sonicgrid`)

**Week 3+**: Remote repository cloning from GitHub URLs

For Week 2:
- `qaagent config init` only accepts local filesystem paths
- `qaagent targets add` only accepts local paths
- Document that remote cloning is planned for Week 3

### LLM vs Templates

**Week 2**: Template-based generation only (Jinja2)

**Week 3+**: LLM-enhanced generation for:
- Smarter scenario descriptions
- Context-aware test assertions
- Natural language test data

For Week 2, focus on high-quality Jinja2 templates that produce good tests without LLM.

---

## Questions to Resolve Before Starting

1. **Next.js OpenAPI**: Should Week 2 include basic route parsing for Next.js, or require manual OpenAPI spec?
   - **Recommendation**: Manual spec for Week 2, auto-generation for Week 3

2. **Auth implementation**: How detailed should auth placeholders be in generated tests?
   - **Recommendation**: TODO comments with options listed, let user implement

3. **Database fixtures**: Should we support SQL inserts for test data, or just JSON/YAML/CSV?
   - **Recommendation**: JSON/YAML/CSV for Week 2, SQL for Week 3

4. **Config validation**: Should we validate that base_url is reachable during `config init`?
   - **Recommendation**: No, just validate YAML schema. User may init before app is running.

---

## Files to Create

### New Packages
- `src/qaagent/config/` (configuration system)
- `src/qaagent/generators/` (test generators)

### New Files
```
src/qaagent/
├── config/
│   ├── __init__.py
│   ├── models.py           # Pydantic models for .qaagent.yaml
│   ├── loader.py           # Config loading and discovery
│   ├── manager.py          # Target registry management
│   └── templates.py        # Config template selection
├── generators/
│   ├── __init__.py
│   ├── behave_generator.py      # BDD test generator
│   ├── unit_test_generator.py   # Unit test generator
│   ├── data_generator.py        # Test data generator
│   ├── mock_builder.py          # Mock object generation
│   ├── scenario_builder.py      # BDD scenario building
│   └── schema_parser.py         # OpenAPI schema parsing
└── templates/
    ├── config/
    │   ├── nextjs.yaml
    │   ├── fastapi.yaml
    │   └── generic.yaml
    ├── feature.j2           # Behave .feature template
    ├── steps.py.j2          # Behave step definitions template
    └── pytest_class.py.j2   # pytest test class template

tests/
├── unit/
│   ├── test_config_loader.py
│   ├── test_config_manager.py
│   ├── test_behave_generator.py
│   ├── test_unit_test_generator.py
│   └── test_data_generator.py
└── integration/
    └── test_week2_full_workflow.py

scripts/
└── validate_week2.sh

docs/
└── WEEK2_TUTORIAL_SONICGRID.md
```

---

## Ready to Start?

**Prerequisites**:
- [x] Week 1 validated and approved
- [x] Week 2 plan reviewed
- [x] Architecture decisions made
- [x] Success criteria defined

**Recommended Order**:
1. Day 1: Configuration system (foundation)
2. Day 2: Behave generator (builds on config)
3. Day 3: Unit test + data generators (builds on config)
4. Day 4: Week 1 improvements + integration testing

**Communication**:
- Commit after each major feature
- Run existing tests before committing
- Update validation script as you go
- Document any deviations from this plan

---

## Codex, you're cleared for Week 2 implementation! 🚀

**Start with Day 1: Configuration System**

Good luck, and let us know if you have any questions!

---

**Claude & User**
