"""Integration tests for qaagent generate unit-tests CLI command."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _run_cli(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run qaagent CLI command."""
    cmd = [sys.executable, "-m", "qaagent", *args]
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=180.0)


def test_generate_unit_tests_creates_files(tmp_path: Path) -> None:
    """Test that generate unit-tests creates pytest test files."""
    qa_home = tmp_path / ".qaagent-home"
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create minimal OpenAPI spec
    openapi_path = project_dir / "openapi.yaml"
    openapi_path.write_text(
        """
openapi: 3.0.3
info:
  title: Pet API
  version: '1.0'
paths:
  /pets:
    get:
      summary: List pets
      tags: [pets]
      responses:
        '200':
          description: OK
    post:
      summary: Create pet
      tags: [pets]
      responses:
        '201':
          description: Created
  /pets/{pet_id}:
    get:
      summary: Get pet
      tags: [pets]
      parameters:
        - name: pet_id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: OK
  /health:
    get:
      summary: Health check
      tags: [health]
      responses:
        '200':
          description: OK
""",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["QAAGENT_HOME"] = str(qa_home)
    pythonpath_parts = [str(Path.cwd() / "src")]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    # Initialize config
    init_result = _run_cli(
        [
            "config",
            "init",
            str(project_dir),
            "--template",
            "fastapi",
            "--name",
            "petapi",
            "--register",
            "--activate",
        ],
        cwd=project_dir,
        env=env,
    )
    assert init_result.returncode == 0, init_result.stderr

    # Generate unit tests
    gen_result = _run_cli(
        ["generate", "unit-tests", "--out", "tests/unit"],
        cwd=project_dir,
        env=env,
    )
    assert gen_result.returncode == 0, f"stdout: {gen_result.stdout}\nstderr: {gen_result.stderr}"

    # Verify test files were created
    test_dir = project_dir / "tests" / "unit"
    assert test_dir.exists()

    # Should have test files for pets and health resources
    test_pets = test_dir / "test_pets_api.py"
    test_health = test_dir / "test_health_api.py"

    assert test_pets.exists(), f"Expected {test_pets} to exist"
    assert test_health.exists(), f"Expected {test_health} to exist"

    # Verify conftest.py was created
    conftest = test_dir / "conftest.py"
    assert conftest.exists(), f"Expected {conftest} to exist"

    # Verify file contents
    pets_content = test_pets.read_text()
    assert "def test_" in pets_content, "Should contain test functions"
    assert "class Test" in pets_content, "Should contain test classes"

    conftest_content = conftest.read_text()
    assert "@pytest.fixture" in conftest_content or "pytest.fixture" in conftest_content, "Should contain fixtures"


def test_generate_unit_tests_with_custom_base_url(tmp_path: Path) -> None:
    """Test generate unit-tests with custom base URL."""
    qa_home = tmp_path / ".qaagent-home"
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create minimal OpenAPI spec
    openapi_path = project_dir / "openapi.yaml"
    openapi_path.write_text(
        """
openapi: 3.0.3
info:
  title: Test API
  version: '1.0'
paths:
  /test:
    get:
      responses:
        '200':
          description: OK
""",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["QAAGENT_HOME"] = str(qa_home)
    pythonpath_parts = [str(Path.cwd() / "src")]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    # Initialize config
    init_result = _run_cli(
        [
            "config",
            "init",
            str(project_dir),
            "--template",
            "fastapi",
            "--name",
            "testapi",
            "--register",
            "--activate",
        ],
        cwd=project_dir,
        env=env,
    )
    assert init_result.returncode == 0, init_result.stderr

    # Generate unit tests with custom base URL
    gen_result = _run_cli(
        [
            "generate",
            "unit-tests",
            "--out",
            "tests/unit",
            "--base-url",
            "http://testserver:9999",
        ],
        cwd=project_dir,
        env=env,
    )
    assert gen_result.returncode == 0, gen_result.stderr

    # Verify test files were created
    test_dir = project_dir / "tests" / "unit"
    assert test_dir.exists()

    # Check that base URL is in conftest
    conftest = test_dir / "conftest.py"
    conftest_content = conftest.read_text()
    assert "testserver:9999" in conftest_content, "Should use custom base URL"


def test_generate_unit_tests_from_routes_file(tmp_path: Path) -> None:
    """Test generate unit-tests using pre-discovered routes file."""
    qa_home = tmp_path / ".qaagent-home"
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create minimal OpenAPI spec
    openapi_path = project_dir / "openapi.yaml"
    openapi_path.write_text(
        """
openapi: 3.0.3
info:
  title: Items API
  version: '1.0'
paths:
  /items:
    get:
      tags: [items]
      responses:
        '200':
          description: OK
""",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["QAAGENT_HOME"] = str(qa_home)
    pythonpath_parts = [str(Path.cwd() / "src")]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    # Initialize config
    init_result = _run_cli(
        [
            "config",
            "init",
            str(project_dir),
            "--template",
            "fastapi",
            "--name",
            "itemsapi",
            "--register",
            "--activate",
        ],
        cwd=project_dir,
        env=env,
    )
    assert init_result.returncode == 0, init_result.stderr

    # First, discover routes
    routes_file = project_dir / "routes.json"
    discover_result = _run_cli(
        ["analyze", "routes", "--out", str(routes_file)],
        cwd=project_dir,
        env=env,
    )
    assert discover_result.returncode == 0, discover_result.stderr
    assert routes_file.exists()

    # Generate unit tests from routes file
    gen_result = _run_cli(
        [
            "generate",
            "unit-tests",
            "--routes-file",
            str(routes_file),
            "--out",
            "tests/unit",
        ],
        cwd=project_dir,
        env=env,
    )
    assert gen_result.returncode == 0, gen_result.stderr

    # Verify test files were created
    test_dir = project_dir / "tests" / "unit"
    assert test_dir.exists()

    test_items = test_dir / "test_items_api.py"
    assert test_items.exists()
