# Week 2 Implementation Plan - Phase 2

**Date**: 2025-10-23
**From**: Claude (Analysis Agent)
**To**: Codex (Implementation Agent)
**Status**: Ready for Implementation

---

## Executive Summary

Week 2 builds on the **Intelligent Analysis Engine** (Week 1) to deliver **Test Generation & Configuration Management**. This week focuses on:

1. **Target Application Configuration** - Multi-app support with `.qaagent.yaml` profiles
2. **BDD/Behave Test Generation** - Given/When/Then scenarios from routes and risks
3. **Unit Test Generation** - pytest-based unit tests with mocks
4. **Test Data Synthesis** - Realistic test data generation from schemas
5. **Week 1 Improvements** - Tool descriptions, refined risk rules, grouped priorities

### Key Deliverable
By end of Week 2, users should be able to:
```bash
# Configure a target app
qaagent config init ~/projects/sonic/sonicgrid

# Generate BDD tests
qaagent generate behave --target sonicgrid --out tests/behave/

# Generate unit tests
qaagent generate unit-tests --target sonicgrid --out tests/unit/

# Generate test data
qaagent generate test-data --target sonicgrid --out fixtures/
```

---

## Problem Statement: Multi-Application Support

### Current State
- QA Agent works with petstore example (local)
- Commands require explicit `--openapi` paths
- No way to switch between multiple target applications
- No persistent configuration

### Target State
- Support multiple target applications simultaneously
- Named configurations (profiles) for each app
- Support both local and remote repositories
- Persistent configuration with sensible defaults
- Easy switching between targets

### Real-World Use Cases

**Use Case 1: SonicGrid (Production Next.js App)**
- Location: `~/projects/sonic/sonicgrid` (local) or `https://github.com/spherop/sonicgrid` (remote)
- Stack: Next.js 14, TypeScript, Supabase, API routes in `src/app/api/`
- Existing tests: E2E (Playwright), Python tests, some unit tests
- OpenAPI: May need to be discovered or generated from Next.js API routes
- Running app: `npm run dev` on http://localhost:3000

**Use Case 2: Petstore (Example API)**
- Location: `examples/petstore-api/` (embedded)
- Stack: FastAPI, Python
- OpenAPI: `examples/petstore-api/openapi.yaml`
- Running app: `uvicorn server:app --port 8765`

**Use Case 3: External GitHub Repository**
- Location: `https://github.com/some-org/some-api`
- Stack: Unknown (needs detection)
- OpenAPI: Needs auto-discovery
- Running app: Needs detection from package.json / README / docker-compose

---

## Architecture: Configuration System

### Design Decisions

**1. Configuration File: `.qaagent.yaml`**
- Located in project root (e.g., `~/projects/sonic/sonicgrid/.qaagent.yaml`)
- YAML format for human readability
- Supports profiles/environments (dev, staging, prod)
- Git-ignored by default (can contain sensitive URLs/tokens)

**2. Global Registry: `~/.qaagent/targets.yaml`**
- Lists all registered target applications
- Maps target names to paths/URLs
- Allows quick switching with `qaagent use <target>`

**3. Repository Support**
- **Local**: Direct filesystem paths (`~/projects/sonic/sonicgrid`)
- **Remote (cloned)**: Clone to `~/.qaagent/repos/<target-name>` on first use
- **Remote (URL only)**: Fetch OpenAPI specs without cloning (for APIs with public specs)

### Configuration Schema

**`.qaagent.yaml` (in target app root)**:
```yaml
# QA Agent Configuration
project:
  name: "SonicGrid"
  type: "nextjs"  # nextjs, fastapi, express, django, rails, etc.
  version: "0.1.0"

# Application details
app:
  # Local development
  dev:
    base_url: "http://localhost:3000"
    start_command: "npm run dev"
    health_endpoint: "/api/health"

  # Staging environment
  staging:
    base_url: "https://staging.sonicgrid.com"
    health_endpoint: "/api/health"

  # Production environment
  prod:
    base_url: "https://sonicgrid.com"
    health_endpoint: "/api/health"

# OpenAPI / API documentation
openapi:
  # For Next.js, may need to generate from route files
  auto_generate: true
  source_dir: "src/app/api"
  spec_path: ".qaagent/openapi.yaml"  # Generated or manual

  # Alternative: direct spec
  # spec_path: "swagger.yaml"

# Test configuration
tests:
  output_dir: "tests/qaagent"

  behave:
    enabled: true
    output_dir: "tests/qaagent/behave"

  unit:
    enabled: true
    output_dir: "tests/qaagent/unit"
    framework: "pytest"  # pytest, jest, mocha, rspec

  e2e:
    enabled: true
    output_dir: "tests/qaagent/e2e"
    framework: "playwright"  # playwright, cypress, selenium

  data:
    enabled: true
    output_dir: "tests/qaagent/fixtures"
    format: "json"  # json, yaml, csv

# Database (for data generation, migrations testing)
database:
  provider: "supabase"  # postgres, mysql, supabase, prisma
  # Connection details omitted (use env vars)

# Authentication (for testing protected endpoints)
auth:
  type: "jwt"  # jwt, oauth2, api-key, basic
  # Token/credentials from env vars for security

# Exclusions (paths to ignore)
exclude:
  paths:
    - "/api/debug/*"
    - "/api/admin/*"
  tags:
    - "internal"
    - "deprecated"

# Custom rules for risk assessment
risk_assessment:
  severity_thresholds:
    critical: ["authentication_bypass", "sql_injection"]
    high: ["missing_auth", "missing_rate_limit"]
    medium: ["missing_pagination", "missing_input_validation"]

  # Disable specific rules
  disable_rules:
    - "health_check_pagination"  # Don't flag /health for pagination

# LLM settings (for advanced test generation)
llm:
  enabled: true
  provider: "ollama"  # ollama, openai, anthropic
  model: "qwen2.5-coder:7b"
  fallback_to_templates: true
```

**`~/.qaagent/targets.yaml` (global registry)**:
```yaml
# Global registry of QA Agent targets
targets:
  sonicgrid:
    path: "/Users/jackblacketter/projects/sonic/sonicgrid"
    type: "local"

  petstore:
    path: "/Users/jackblacketter/projects/qaagent/examples/petstore-api"
    type: "local"

  stripe-api:
    url: "https://github.com/stripe/stripe-mock"
    type: "remote"
    clone_to: "~/.qaagent/repos/stripe-api"

# Current active target
active: "sonicgrid"
```

### New CLI Commands

```bash
# Configuration management
qaagent config init [PATH]          # Create .qaagent.yaml in target app
qaagent config validate             # Validate current config
qaagent config show                 # Show current config

# Target management
qaagent targets list                # List all registered targets
qaagent targets add <name> <path>   # Register a target
qaagent targets remove <name>       # Unregister a target
qaagent use <name>                  # Switch active target

# Clone remote repos
qaagent clone <github-url> [name]   # Clone repo to ~/.qaagent/repos/
```

---

## Feature 1: Configuration Management

### Files to Create/Modify

**New Files**:
- `src/qaagent/config/models.py` - Pydantic models for `.qaagent.yaml`
- `src/qaagent/config/loader.py` - Load and validate config files
- `src/qaagent/config/manager.py` - Target registry management
- `src/qaagent/config/templates.py` - Default config templates by project type
- `src/qaagent/templates/config/nextjs.yaml` - Next.js config template
- `src/qaagent/templates/config/fastapi.yaml` - FastAPI config template
- `src/qaagent/templates/config/generic.yaml` - Generic config template

**Modified Files**:
- `src/qaagent/cli.py` - Add `config` and `targets` command groups

### Implementation Details

**1. Config Models** (`src/qaagent/config/models.py`):
```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class AppEnvironment(BaseModel):
    base_url: str
    start_command: Optional[str] = None
    health_endpoint: Optional[str] = "/health"

class OpenAPIConfig(BaseModel):
    auto_generate: bool = False
    source_dir: Optional[str] = None
    spec_path: Optional[str] = None

class TestConfig(BaseModel):
    output_dir: str = "tests/qaagent"

class BehaveConfig(BaseModel):
    enabled: bool = True
    output_dir: str = "tests/qaagent/behave"

class QAAgentConfig(BaseModel):
    """Root configuration model for .qaagent.yaml"""
    project: Dict[str, str]
    app: Dict[str, AppEnvironment]  # dev, staging, prod
    openapi: OpenAPIConfig
    tests: TestConfig
    # ... etc

    @classmethod
    def load_from_file(cls, path: str) -> "QAAgentConfig":
        """Load and validate config from YAML file"""
        pass

    def get_active_env(self, env: str = "dev") -> AppEnvironment:
        """Get active environment config"""
        return self.app.get(env)
```

**2. Config Loader** (`src/qaagent/config/loader.py`):
```python
from pathlib import Path
import yaml

def find_config(start_path: Path = Path.cwd()) -> Optional[Path]:
    """
    Walk up directory tree to find .qaagent.yaml
    Similar to how git finds .git/
    """
    current = start_path.resolve()
    while current != current.parent:
        config_file = current / ".qaagent.yaml"
        if config_file.exists():
            return config_file
        current = current.parent
    return None

def load_config(path: Optional[Path] = None) -> QAAgentConfig:
    """Load config from path or auto-discover"""
    if path is None:
        path = find_config()
    if path is None:
        raise ConfigNotFoundError("No .qaagent.yaml found")
    return QAAgentConfig.load_from_file(str(path))
```

**3. Target Manager** (`src/qaagent/config/manager.py`):
```python
class TargetManager:
    """Manage global target registry at ~/.qaagent/targets.yaml"""

    def __init__(self):
        self.config_dir = Path.home() / ".qaagent"
        self.targets_file = self.config_dir / "targets.yaml"
        self.config_dir.mkdir(exist_ok=True)

    def list_targets(self) -> Dict[str, Dict]:
        """List all registered targets"""

    def add_target(self, name: str, path: str, type: str = "local"):
        """Register a new target"""

    def remove_target(self, name: str):
        """Unregister a target"""

    def get_active(self) -> Optional[str]:
        """Get currently active target"""

    def set_active(self, name: str):
        """Set active target"""

    def get_target_config(self, name: str) -> QAAgentConfig:
        """Load config for specific target"""
```

**4. CLI Commands** (add to `src/qaagent/cli.py`):
```python
# Config command group
config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")

@config_app.command("init")
def config_init(
    path: str = typer.Argument(".", help="Path to target application"),
    template: str = typer.Option("generic", help="Config template: nextjs, fastapi, generic"),
    force: bool = typer.Option(False, help="Overwrite existing config")
):
    """
    Initialize .qaagent.yaml in target application directory.

    Detects project type and creates appropriate configuration.
    """
    # 1. Detect project type (package.json -> nextjs, pyproject.toml -> fastapi, etc.)
    # 2. Load template
    # 3. Write .qaagent.yaml
    # 4. Register in global targets.yaml
    pass

@config_app.command("validate")
def config_validate():
    """Validate current .qaagent.yaml configuration"""
    pass

@config_app.command("show")
def config_show():
    """Show current configuration"""
    pass

# Targets command group
targets_app = typer.Typer(help="Target application management")
app.add_typer(targets_app, name="targets")

@targets_app.command("list")
def targets_list():
    """List all registered target applications"""
    manager = TargetManager()
    targets = manager.list_targets()
    active = manager.get_active()

    # Rich table output
    table = Table(title="QA Agent Targets")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Path")
    table.add_column("Active")

    for name, info in targets.items():
        is_active = "✓" if name == active else ""
        table.add_row(name, info['type'], info['path'], is_active)

    console.print(table)

@targets_app.command("add")
def targets_add(
    name: str,
    path: str,
    type: str = typer.Option("local", help="Target type: local, remote")
):
    """Register a new target application"""
    pass

# Use command (top-level)
@app.command("use")
def use_target(name: str):
    """Switch to a different target application"""
    manager = TargetManager()
    manager.set_active(name)
    console.print(f"[green]Switched to target: {name}[/green]")
```

---

## Feature 2: BDD/Behave Test Generation

### Overview
Generate Python Behave (BDD) tests from discovered routes and risks.

### Example Output

**Input**: Routes + Risks from Week 1
**Output**: `tests/qaagent/behave/features/pets.feature`

```gherkin
# Auto-generated by QA Agent
# Source: POST /pets risk assessment

Feature: Pet Creation Security
  As a security tester
  I want to verify authentication requirements
  So that unauthorized users cannot create pets

  Background:
    Given the API is running at "http://localhost:8765"

  @security @high-risk
  Scenario: Unauthenticated user attempts to create pet
    Given I am not authenticated
    When I send a POST request to "/pets" with:
      """
      {
        "name": "Fluffy",
        "species": "cat",
        "age": 3
      }
      """
    Then the response status should be 401
    And the response should contain "authentication required"

  @security @high-risk
  Scenario: Authenticated user creates pet successfully
    Given I am authenticated as "test-user"
    When I send a POST request to "/pets" with:
      """
      {
        "name": "Fluffy",
        "species": "cat",
        "age": 3
      }
      """
    Then the response status should be 201
    And the response should match the Pet schema
    And the pet should be stored in the database

  @performance @pagination
  Scenario: Search endpoint handles pagination
    Given the database contains 100 pets
    When I send a GET request to "/pets/search?species=cat"
    Then the response status should be 200
    And the response should have pagination metadata
    And the response should contain at most 20 items
```

**Output**: `tests/qaagent/behave/steps/api_steps.py`

```python
# Auto-generated by QA Agent

from behave import given, when, then
import requests
import json

@given('the API is running at "{base_url}"')
def step_api_running(context, base_url):
    context.base_url = base_url
    response = requests.get(f"{base_url}/health")
    assert response.status_code == 200

@given('I am not authenticated')
def step_not_authenticated(context):
    context.headers = {}

@given('I am authenticated as "{username}"')
def step_authenticated(context, username):
    # TODO: Replace with actual auth token generation
    context.headers = {"Authorization": f"Bearer fake-token-{username}"}

@when('I send a {method} request to "{path}" with')
def step_send_request_with_body(context, method, path):
    url = f"{context.base_url}{path}"
    data = json.loads(context.text)
    context.response = requests.request(
        method, url, json=data, headers=context.headers
    )

@then('the response status should be {status_code:d}')
def step_check_status(context, status_code):
    assert context.response.status_code == status_code

# ... more step definitions
```

### Implementation Details

**New Files**:
- `src/qaagent/generators/behave_generator.py` - Main BDD generator
- `src/qaagent/generators/templates/feature.j2` - Jinja2 template for .feature files
- `src/qaagent/generators/templates/steps.py.j2` - Template for step definitions
- `src/qaagent/generators/behave_scenarios.py` - Scenario builders from risks

**CLI Command**:
```python
generate_app = typer.Typer(help="Test generation commands")
app.add_typer(generate_app, name="generate")

@generate_app.command("behave")
def generate_behave(
    target: Optional[str] = typer.Option(None, help="Target name (uses active if not specified)"),
    routes_file: Optional[str] = typer.Option(None, help="Routes JSON file (overrides target)"),
    risks_file: Optional[str] = typer.Option(None, help="Risks JSON file (overrides target)"),
    out: str = typer.Option("tests/qaagent/behave", help="Output directory"),
    env: str = typer.Option("dev", help="Environment to test (dev, staging, prod)"),
    overwrite: bool = typer.Option(False, help="Overwrite existing tests")
):
    """
    Generate Behave (BDD) tests from routes and risks.

    Examples:
      qaagent generate behave --target sonicgrid
      qaagent generate behave --routes-file routes.json --risks-file risks.json
    """
    # 1. Load config (from target or current)
    # 2. Load routes and risks (from files or run analysis)
    # 3. Generate .feature files (one per route or grouped by tag)
    # 4. Generate step_definitions/*.py
    # 5. Generate behave.ini config
    # 6. Print summary with run instructions
    pass
```

**Generation Logic**:
```python
class BehaveGenerator:
    def __init__(self, routes: List[Route], risks: List[Risk], config: QAAgentConfig):
        self.routes = routes
        self.risks = risks
        self.config = config

    def generate_features(self, output_dir: Path):
        """Generate .feature files"""
        # Group routes by tag or resource
        grouped = self._group_routes_by_resource()

        for resource, routes in grouped.items():
            feature_path = output_dir / "features" / f"{resource}.feature"

            # Get relevant risks for these routes
            risks = self._get_risks_for_routes(routes)

            # Generate scenarios from risks
            scenarios = self._generate_scenarios(routes, risks)

            # Render template
            template = self._load_template("feature.j2")
            content = template.render(
                resource=resource,
                scenarios=scenarios,
                base_url=self.config.get_active_env().base_url
            )

            feature_path.write_text(content)

    def _generate_scenarios(self, routes: List[Route], risks: List[Risk]) -> List[Scenario]:
        """Generate BDD scenarios from risks"""
        scenarios = []

        for risk in risks:
            if risk.category == "security" and "authentication" in risk.description:
                # Generate auth test scenarios
                scenarios.append(self._create_auth_scenario(risk))
            elif risk.category == "performance" and "pagination" in risk.description:
                # Generate pagination test scenarios
                scenarios.append(self._create_pagination_scenario(risk))
            # ... more scenario types

        return scenarios
```

---

## Feature 3: Unit Test Generation

### Overview
Generate pytest-based unit tests from route handlers and business logic.

### Example Output

**Input**: Routes from Week 1
**Output**: `tests/qaagent/unit/test_pets_api.py`

```python
# Auto-generated by QA Agent

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from server import app  # Import from target app

client = TestClient(app)

class TestPetsAPI:
    """Unit tests for /pets endpoints"""

    def test_list_pets_empty(self):
        """Test GET /pets returns empty list when no pets exist"""
        with patch('server.db.get_pets') as mock_get_pets:
            mock_get_pets.return_value = []

            response = client.get("/pets")

            assert response.status_code == 200
            assert response.json() == []
            mock_get_pets.assert_called_once()

    def test_list_pets_returns_data(self):
        """Test GET /pets returns pet data"""
        with patch('server.db.get_pets') as mock_get_pets:
            mock_get_pets.return_value = [
                {"id": 1, "name": "Fluffy", "species": "cat", "age": 3}
            ]

            response = client.get("/pets")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "Fluffy"

    def test_create_pet_success(self):
        """Test POST /pets creates a pet with valid data"""
        with patch('server.db.create_pet') as mock_create:
            mock_create.return_value = {"id": 1, "name": "Spot", "species": "dog", "age": 2}

            response = client.post("/pets", json={
                "name": "Spot",
                "species": "dog",
                "age": 2
            })

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Spot"
            assert data["id"] == 1

    def test_create_pet_invalid_data(self):
        """Test POST /pets rejects invalid data"""
        response = client.post("/pets", json={
            "name": "",  # Invalid: empty name
            "species": "dog",
            "age": -1  # Invalid: negative age
        })

        assert response.status_code == 422

    @pytest.mark.parametrize("invalid_age", [-1, 0, 200, "abc", None])
    def test_create_pet_invalid_age(self, invalid_age):
        """Test POST /pets validates age field"""
        response = client.post("/pets", json={
            "name": "Test",
            "species": "dog",
            "age": invalid_age
        })

        assert response.status_code == 422
```

### Implementation Details

**New Files**:
- `src/qaagent/generators/unit_test_generator.py` - Main unit test generator
- `src/qaagent/generators/templates/pytest_class.py.j2` - Template for test classes
- `src/qaagent/generators/mock_builder.py` - Auto-generate mocks from schemas

**CLI Command**:
```python
@generate_app.command("unit-tests")
def generate_unit_tests(
    target: Optional[str] = typer.Option(None, help="Target name"),
    routes_file: Optional[str] = typer.Option(None, help="Routes JSON file"),
    out: str = typer.Option("tests/qaagent/unit", help="Output directory"),
    framework: str = typer.Option("pytest", help="Test framework: pytest, jest"),
    coverage_threshold: int = typer.Option(80, help="Target coverage percentage"),
    overwrite: bool = typer.Option(False, help="Overwrite existing tests")
):
    """
    Generate unit tests from routes and schemas.

    Examples:
      qaagent generate unit-tests --target sonicgrid
      qaagent generate unit-tests --routes-file routes.json --framework pytest
    """
    pass
```

---

## Feature 4: Test Data Synthesis

### Overview
Generate realistic test data from OpenAPI schemas, database schemas, and response examples.

### Example Output

**Output**: `tests/qaagent/fixtures/pets.json`

```json
[
  {
    "id": 1,
    "name": "Fluffy",
    "species": "cat",
    "age": 3,
    "owner_id": 101,
    "tags": ["friendly", "indoor"],
    "created_at": "2024-01-15T10:30:00Z"
  },
  {
    "id": 2,
    "name": "Max",
    "species": "dog",
    "age": 5,
    "owner_id": 102,
    "tags": ["energetic", "outdoor"],
    "created_at": "2024-02-20T14:45:00Z"
  },
  {
    "id": 3,
    "name": "Tweety",
    "species": "bird",
    "age": 1,
    "owner_id": 101,
    "tags": ["small", "cage"],
    "created_at": "2024-03-10T09:15:00Z"
  }
]
```

### Implementation Details

**New Files**:
- `src/qaagent/generators/data_generator.py` - Main data synthesis engine
- `src/qaagent/generators/faker_builder.py` - Use Faker library for realistic data
- `src/qaagent/generators/schema_parser.py` - Parse OpenAPI/JSON schemas

**CLI Command**:
```python
@generate_app.command("test-data")
def generate_test_data(
    target: Optional[str] = typer.Option(None, help="Target name"),
    schema: Optional[str] = typer.Option(None, help="OpenAPI spec or JSON schema"),
    model: Optional[str] = typer.Option(None, help="Model/entity name (e.g., 'Pet')"),
    count: int = typer.Option(10, help="Number of records to generate"),
    out: str = typer.Option("tests/qaagent/fixtures", help="Output directory"),
    format: str = typer.Option("json", help="Output format: json, yaml, csv"),
    seed: Optional[int] = typer.Option(None, help="Random seed for reproducibility")
):
    """
    Generate realistic test data from schemas.

    Examples:
      qaagent generate test-data --target sonicgrid --model Pet --count 50
      qaagent generate test-data --schema openapi.yaml --model User --format yaml
    """
    pass
```

**Data Generation Logic**:
```python
from faker import Faker
import random

class DataGenerator:
    def __init__(self, schema: dict, seed: Optional[int] = None):
        self.schema = schema
        self.faker = Faker()
        if seed:
            Faker.seed(seed)
            random.seed(seed)

    def generate(self, count: int) -> List[dict]:
        """Generate N records matching schema"""
        records = []
        for i in range(count):
            record = self._generate_record(self.schema)
            records.append(record)
        return records

    def _generate_record(self, schema: dict) -> dict:
        """Generate single record from schema"""
        record = {}
        properties = schema.get("properties", {})

        for field, field_schema in properties.items():
            record[field] = self._generate_field(field, field_schema)

        return record

    def _generate_field(self, field_name: str, schema: dict):
        """Generate single field value based on schema and field name"""
        field_type = schema.get("type")

        # Use faker for common field names
        if "email" in field_name.lower():
            return self.faker.email()
        elif "name" in field_name.lower():
            return self.faker.name()
        elif "age" in field_name.lower():
            return random.randint(1, 100)
        elif "date" in field_name.lower() or "created" in field_name.lower():
            return self.faker.iso8601()

        # Fallback to type-based generation
        if field_type == "string":
            if "enum" in schema:
                return random.choice(schema["enum"])
            return self.faker.word()
        elif field_type == "integer":
            minimum = schema.get("minimum", 0)
            maximum = schema.get("maximum", 1000)
            return random.randint(minimum, maximum)
        # ... more types
```

---

## Feature 5: Week 1 Improvements

### 1. Add MCP Tool Descriptions

**File**: `src/qaagent/mcp_server.py`

**Change**:
```python
@mcp.tool()
def discover_routes(args: DiscoverRoutesArgs):
    """
    Discover API and UI routes from OpenAPI specs or source code.

    Returns a list of routes with metadata including paths, methods,
    authentication requirements, and confidence scores.
    """
    # ... existing implementation

@mcp.tool()
def assess_risks(args: AssessRisksArgs):
    """
    Assess security, performance, and reliability risks for API routes.

    Analyzes routes and returns categorized risks with severity levels,
    CWE references, OWASP Top 10 mappings, and remediation recommendations.
    """
    # ... existing implementation

@mcp.tool()
def analyze_application(args: AnalyzeApplicationArgs):
    """
    Perform comprehensive application analysis (routes + risks + strategy).

    Convenience wrapper that discovers routes, assesses risks, and generates
    a complete testing strategy in one call.
    """
    # ... existing implementation
```

### 2. Refine Risk Assessment Rules

**File**: `src/qaagent/analyzers/risk_assessment.py`

**Changes**:
```python
def _should_check_pagination(route: Route) -> bool:
    """
    Determine if route should be checked for pagination.

    Exclude:
    - Health check endpoints
    - Single-resource GET requests (e.g., /pets/{id})
    - Non-collection endpoints
    """
    # Don't flag health checks
    if "health" in route.path.lower():
        return False

    # Don't flag single-resource fetches (with path params)
    if "{" in route.path and route.method == "GET":
        return False

    # Only flag GET endpoints that return collections
    if route.method != "GET":
        return False

    # Check if response is array type
    response_schema = route.responses.get("200", {})
    content = response_schema.get("content", {}).get("application/json", {})
    schema = content.get("schema", {})

    return schema.get("type") == "array"
```

### 3. Group Duplicate Priorities in Strategy

**File**: `src/qaagent/analyzers/strategy_generator.py`

**Change**:
```python
def _consolidate_priorities(risks: List[Risk]) -> List[Priority]:
    """
    Group similar risks into consolidated priorities.

    Example:
      Instead of:
        - Mutation endpoint without authentication (POST /pets)
        - Mutation endpoint without authentication (PUT /pets/{id})
        - Mutation endpoint without authentication (DELETE /pets/{id})

      Return:
        - Mutation endpoints without authentication (3 routes: POST /pets, PUT /pets/{id}, DELETE /pets/{id})
    """
    from collections import defaultdict

    grouped = defaultdict(list)
    for risk in risks:
        key = (risk.description, risk.severity)
        grouped[key].append(risk)

    priorities = []
    for (description, severity), risk_group in grouped.items():
        routes = [r.route for r in risk_group]
        priorities.append(Priority(
            name=risk_group[0].description,
            reason=risk_group[0].recommendation,
            severity=severity,
            affected_routes=routes,
            tests_needed=len(routes) * 5
        ))

    return sorted(priorities, key=lambda p: SEVERITY_ORDER[p.severity])
```

### 4. Add Configuration to Validation Script

**File**: `scripts/validate_week1.sh`

**Change** (line 15):
```bash
# Use python from venv if available
if [ -f "${PROJECT_ROOT}/.venv/bin/python" ]; then
  PYTHON="${PROJECT_ROOT}/.venv/bin/python"
else
  PYTHON="python"
fi

print_step "Discovering routes from petstore OpenAPI"
$PYTHON -m qaagent.cli analyze routes \
  --openapi "${OPENAPI}" \
  --out "${TMP_DIR}/routes.json" \
  --format json > /dev/null
```

---

## Testing Plan

### Unit Tests (pytest)
```python
# tests/unit/test_config_loader.py
def test_load_config_from_file():
    """Test loading .qaagent.yaml"""

def test_find_config_walks_up_tree():
    """Test config discovery walks up directories"""

def test_config_validation_fails_on_invalid():
    """Test Pydantic validation catches errors"""

# tests/unit/test_behave_generator.py
def test_generate_feature_from_route():
    """Test .feature file generation"""

def test_generate_auth_scenarios():
    """Test authentication scenario generation"""

# tests/unit/test_unit_test_generator.py
def test_generate_pytest_class():
    """Test pytest class generation"""

def test_generate_parametrize_tests():
    """Test parametrized test generation"""

# tests/unit/test_data_generator.py
def test_generate_from_schema():
    """Test data generation from JSON schema"""

def test_faker_integration():
    """Test Faker integration for realistic data"""
```

### Integration Tests
```python
# tests/integration/test_week2_full_workflow.py
def test_full_workflow_sonicgrid():
    """
    Test complete Week 2 workflow:
    1. Initialize config for SonicGrid
    2. Analyze routes
    3. Generate Behave tests
    4. Generate unit tests
    5. Generate test data
    6. Verify all outputs
    """

def test_config_init_and_use():
    """Test config init and target switching"""
```

---

## Deliverables

### Code
- [ ] Configuration system (`src/qaagent/config/`)
- [ ] Behave test generator (`src/qaagent/generators/behave_generator.py`)
- [ ] Unit test generator (`src/qaagent/generators/unit_test_generator.py`)
- [ ] Test data generator (`src/qaagent/generators/data_generator.py`)
- [ ] CLI commands (`config`, `targets`, `use`, `generate`)
- [ ] Config templates (Next.js, FastAPI, generic)
- [ ] Week 1 improvements (tool descriptions, refined rules, grouped priorities)

### Tests
- [ ] Unit tests for config system
- [ ] Unit tests for generators
- [ ] Integration test for full workflow
- [ ] Validation script for Week 2

### Documentation
- [ ] Configuration schema documentation
- [ ] Generator usage examples
- [ ] Tutorial: Setting up SonicGrid for QA Agent
- [ ] Week 2 validation report template

### Examples
- [ ] `.qaagent.yaml` for petstore
- [ ] `.qaagent.yaml` for SonicGrid (Next.js)
- [ ] Generated Behave tests (petstore)
- [ ] Generated unit tests (petstore)
- [ ] Generated test data (petstore)

---

## Timeline

**Estimated Effort**: 3-4 days

### Day 1: Configuration System
- Implement config models, loader, manager
- CLI commands: `config init/validate/show`, `targets list/add/remove`, `use`
- Templates for Next.js, FastAPI, generic
- Unit tests for config system

### Day 2: Behave Test Generator
- Implement BehaveGenerator class
- Jinja2 templates for .feature and steps
- Scenario generation from risks
- Integration with config system

### Day 3: Unit Test & Data Generators
- Implement UnitTestGenerator class
- Implement DataGenerator class
- Faker integration
- Templates for pytest tests

### Day 4: Week 1 Improvements + Testing
- Add MCP tool descriptions
- Refine risk assessment rules
- Group duplicate priorities
- Integration tests
- Validation script
- Documentation

---

## Success Criteria

Week 2 is complete when:

- [ ] User can run `qaagent config init ~/projects/sonic/sonicgrid` to initialize config
- [ ] User can run `qaagent targets list` to see all registered targets
- [ ] User can run `qaagent use sonicgrid` to switch targets
- [ ] User can run `qaagent generate behave` to generate BDD tests
- [ ] User can run `qaagent generate unit-tests` to generate pytest tests
- [ ] User can run `qaagent generate test-data` to generate fixtures
- [ ] Generated tests are runnable (behave tests/qaagent/behave, pytest tests/qaagent/unit)
- [ ] All Week 1 improvements are implemented
- [ ] Configuration supports both local and remote repositories
- [ ] All unit tests pass
- [ ] Integration test validates full workflow
- [ ] Documentation is complete

---

## Notes for Codex

### Implementation Priorities
1. **Configuration system first** - Everything else depends on this
2. **Start with local paths** - Remote cloning can be Week 3
3. **Template-based generation** - Use Jinja2 extensively for maintainability
4. **Make it runnable** - Generated tests should work out-of-the-box with minimal edits

### Design Principles
- **Convention over configuration** - Smart defaults based on project type
- **Fail gracefully** - If OpenAPI not found, offer to generate from source
- **Extensible** - Easy to add new project types, test frameworks, risk rules
- **User-friendly** - Rich console output, helpful error messages

### Questions to Consider
1. **Next.js OpenAPI generation** - How to extract routes from `src/app/api/` structure? (May need AST parsing or runtime introspection)
2. **Authentication in generated tests** - How to handle different auth schemes? (JWT, OAuth2, API keys)
3. **Database fixtures** - Should we support SQL inserts in addition to JSON fixtures?
4. **LLM integration** - When should we use LLM vs templates for test generation?

### Dependencies to Add
```toml
[project.dependencies]
faker = ">=20.0.0"  # Test data generation
jinja2 = ">=3.1.0"  # Already have this
pyyaml = ">=6.0"    # Already have this
```

---

## Handoff Checklist

Before starting implementation:
- [x] Week 1 validation complete and approved
- [x] Week 2 plan reviewed and approved
- [x] Success criteria clear
- [x] Timeline agreed upon
- [ ] Any questions resolved

**Ready for Implementation**: Yes

**Codex, you may begin Week 2 implementation. Good luck!** 🚀

---

**End of Plan**
