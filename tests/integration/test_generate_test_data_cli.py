"""Integration tests for qaagent generate test-data CLI command."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml


def _run_cli(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run qaagent CLI command."""
    cmd = [sys.executable, "-m", "qaagent", *args]
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=180.0)


def test_generate_test_data_json_format(tmp_path: Path) -> None:
    """Test generate test-data with JSON output."""
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

    # Generate test data
    output_file = project_dir / "pets.json"
    gen_result = _run_cli(
        [
            "generate",
            "test-data",
            "Pet",
            "--count",
            "10",
            "--format",
            "json",
            "--out",
            str(output_file),
        ],
        cwd=project_dir,
        env=env,
    )
    assert gen_result.returncode == 0, f"stdout: {gen_result.stdout}\nstderr: {gen_result.stderr}"

    # Verify file was created
    assert output_file.exists(), f"Expected {output_file} to exist"

    # Verify content
    data = json.loads(output_file.read_text())
    assert len(data) == 10, "Should generate 10 records"

    # Verify data structure
    for record in data:
        assert "id" in record
        assert "name" in record
        assert "species" in record
        assert "age" in record

    # Verify data quality
    assert data[0]["species"] in ["dog", "cat", "bird", "fish"], "Species should be from enum"
    assert isinstance(data[0]["name"], str), "Name should be a string"
    assert isinstance(data[0]["age"], int), "Age should be an integer"


def test_generate_test_data_yaml_format(tmp_path: Path) -> None:
    """Test generate test-data with YAML output."""
    qa_home = tmp_path / ".qaagent-home"
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create minimal OpenAPI spec
    openapi_path = project_dir / "openapi.yaml"
    openapi_path.write_text(
        """
openapi: 3.0.3
info:
  title: Owner API
  version: '1.0'
paths:
  /owners:
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
            "ownerapi",
            "--register",
            "--activate",
        ],
        cwd=project_dir,
        env=env,
    )
    assert init_result.returncode == 0, init_result.stderr

    # Generate test data in YAML format
    output_file = project_dir / "owners.yaml"
    gen_result = _run_cli(
        [
            "generate",
            "test-data",
            "Owner",
            "--count",
            "5",
            "--format",
            "yaml",
            "--out",
            str(output_file),
        ],
        cwd=project_dir,
        env=env,
    )
    assert gen_result.returncode == 0, gen_result.stderr

    # Verify file was created
    assert output_file.exists()

    # Verify content
    data = yaml.safe_load(output_file.read_text())
    assert len(data) == 5, "Should generate 5 records"

    # Verify data structure
    for record in data:
        assert "id" in record
        assert "name" in record
        assert "email" in record

    # Verify email format
    assert "@" in data[0]["email"], "Email should have @ symbol"


def test_generate_test_data_csv_format(tmp_path: Path) -> None:
    """Test generate test-data with CSV output."""
    qa_home = tmp_path / ".qaagent-home"
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create minimal OpenAPI spec
    openapi_path = project_dir / "openapi.yaml"
    openapi_path.write_text(
        """
openapi: 3.0.3
info:
  title: User API
  version: '1.0'
paths:
  /users:
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
            "userapi",
            "--register",
            "--activate",
        ],
        cwd=project_dir,
        env=env,
    )
    assert init_result.returncode == 0, init_result.stderr

    # Generate test data in CSV format
    output_file = project_dir / "users.csv"
    gen_result = _run_cli(
        [
            "generate",
            "test-data",
            "User",
            "--count",
            "7",
            "--format",
            "csv",
            "--out",
            str(output_file),
        ],
        cwd=project_dir,
        env=env,
    )
    assert gen_result.returncode == 0, gen_result.stderr

    # Verify file was created
    assert output_file.exists()

    # Verify CSV content
    with output_file.open("r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 7, "Should generate 7 records"

    # Verify headers
    assert "id" in rows[0]
    assert "name" in rows[0]
    assert "email" in rows[0]


def test_generate_test_data_with_seed(tmp_path: Path) -> None:
    """Test generate test-data with seed for reproducibility."""
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

    # Generate test data with seed
    output_file1 = project_dir / "pets1.json"
    gen_result1 = _run_cli(
        [
            "generate",
            "test-data",
            "Pet",
            "--count",
            "3",
            "--seed",
            "42",
            "--out",
            str(output_file1),
        ],
        cwd=project_dir,
        env=env,
    )
    assert gen_result1.returncode == 0, gen_result1.stderr

    # Generate again with same seed
    output_file2 = project_dir / "pets2.json"
    gen_result2 = _run_cli(
        [
            "generate",
            "test-data",
            "Pet",
            "--count",
            "3",
            "--seed",
            "42",
            "--out",
            str(output_file2),
        ],
        cwd=project_dir,
        env=env,
    )
    assert gen_result2.returncode == 0, gen_result2.stderr

    # Verify both files exist
    assert output_file1.exists()
    assert output_file2.exists()

    # Load data
    data1 = json.loads(output_file1.read_text())
    data2 = json.loads(output_file2.read_text())

    # Same seed should produce same structure (at minimum)
    assert len(data1) == len(data2)
    assert data1[0].keys() == data2[0].keys()


def test_generate_test_data_custom_count(tmp_path: Path) -> None:
    """Test generate test-data with custom record count."""
    qa_home = tmp_path / ".qaagent-home"
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create minimal OpenAPI spec
    openapi_path = project_dir / "openapi.yaml"
    openapi_path.write_text(
        """
openapi: 3.0.3
info:
  title: Item API
  version: '1.0'
paths:
  /items:
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
            "itemapi",
            "--register",
            "--activate",
        ],
        cwd=project_dir,
        env=env,
    )
    assert init_result.returncode == 0, init_result.stderr

    # Generate different counts
    for count in [1, 5, 50]:
        output_file = project_dir / f"items_{count}.json"
        gen_result = _run_cli(
            [
                "generate",
                "test-data",
                "Item",
                "--count",
                str(count),
                "--out",
                str(output_file),
            ],
            cwd=project_dir,
            env=env,
        )
        assert gen_result.returncode == 0, gen_result.stderr

        data = json.loads(output_file.read_text())
        assert len(data) == count, f"Should generate exactly {count} records"
