from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from qaagent.commands import app
from qaagent.config.models import AuthSettings, EnvironmentSettings, OpenAPISettings, ProjectSettings, QAAgentProfile
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator, FindingRecord, CoverageRecord, ChurnRecord
from qaagent.evidence.run_manager import RunManager

runner = CliRunner()


def _run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "qaagent", *args]
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=120.0)


def test_analyze_routes_cli_generates_output(project_root: Path, tmp_path: Path) -> None:
    openapi_path = project_root / "examples" / "petstore-api" / "openapi.yaml"
    out_file = tmp_path / "routes.json"
    result = _run_cli([
        "analyze",
        "routes",
        "--openapi",
        str(openapi_path),
        "--out",
        str(out_file),
    ], project_root)
    assert result.returncode == 0, result.stderr
    data = json.loads(out_file.read_text())
    assert isinstance(data, list) and data


def _seed_run(runs_dir: Path) -> str:
    manager = RunManager(base_dir=runs_dir)
    repo = runs_dir / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    handle = manager.create_run("repo", repo)
    writer = EvidenceWriter(handle)
    id_gen = EvidenceIDGenerator(handle.run_id)

    writer.write_records(
        "quality",
        [
            FindingRecord(
                evidence_id=id_gen.next_id("fnd"),
                tool="flake8",
                severity="high",
                code="E302",
                message="expected blank lines",
                file="src/auth/login.py",
                line=10,
                column=1,
            ).to_dict()
        ],
    )
    writer.write_records(
        "coverage",
        [
            CoverageRecord(
                coverage_id=id_gen.next_id("cov"),
                type="line",
                component="src/auth/login.py",
                value=0.4,
            ).to_dict()
        ],
    )
    writer.write_records(
        "churn",
        [
            ChurnRecord(
                evidence_id=id_gen.next_id("chn"),
                path="src/auth/login.py",
                window="90d",
                commits=5,
                lines_added=40,
                lines_deleted=15,
                contributors=2,
            ).to_dict()
        ],
    )
    return handle.run_id


def test_analyze_risks_cli_runs(project_root: Path, tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    run_id = _seed_run(runs_dir)
    risks_out = tmp_path / "risks.json"

    result_risks = _run_cli([
        "analyze",
        "risks",
        run_id,
        "--runs-dir",
        str(runs_dir),
        "--config",
        str(project_root / "handoff" / "risk_config.yaml"),
        "--json-out",
        str(risks_out),
    ], project_root)
    assert result_risks.returncode == 0, result_risks.stderr
    data = json.loads(risks_out.read_text())
    assert isinstance(data, list) and data


def test_analyze_routes_cli_passes_crawl_options(tmp_path: Path) -> None:
    out_file = tmp_path / "routes.json"
    fake_routes = [
        {
            "path": "/",
            "method": "GET",
            "auth_required": False,
            "source": "runtime",
            "confidence": 0.6,
        }
    ]
    with patch("qaagent.commands.analyze_cmd.discover_routes") as mock_discover:
        mock_discover.return_value = []
        with patch("qaagent.commands.analyze_cmd.export_routes") as mock_export:
            result = runner.invoke(
                app,
                [
                    "analyze",
                    "routes",
                    "--crawl",
                    "--crawl-url",
                    "https://app.example.com",
                    "--crawl-depth",
                    "1",
                    "--crawl-max-pages",
                    "25",
                    "--crawl-allow-external",
                    "--crawl-auth-header",
                    "Authorization",
                    "--crawl-auth-token-env",
                    "API_TOKEN",
                    "--out",
                    str(out_file),
                ],
                env={"API_TOKEN": "secret"},
            )

    assert result.exit_code == 0
    kwargs = mock_discover.call_args.kwargs
    assert kwargs["crawl"] is True
    assert kwargs["crawl_url"] == "https://app.example.com"
    assert kwargs["crawl_depth"] == 1
    assert kwargs["crawl_max_pages"] == 25
    assert kwargs["crawl_same_origin"] is False
    assert kwargs["crawl_headers"]["Authorization"] == "Bearer secret"
    mock_export.assert_called_once()


def test_analyze_routes_cli_uses_active_profile_for_crawl_url(tmp_path: Path) -> None:
    out_file = tmp_path / "routes.json"

    entry = MagicMock()
    entry.resolved_path.return_value = tmp_path
    profile = QAAgentProfile(
        project=ProjectSettings(name="demo", type="web"),
        openapi=OpenAPISettings(),
        app={
            "dev": EnvironmentSettings(
                base_url="https://secure.example.com",
                headers={"X-Tenant": "acme"},
                auth=AuthSettings(header_name="Authorization", token_env="API_TOKEN", prefix="Bearer "),
            )
        },
    )

    with patch("qaagent.commands.analyze_cmd.load_active_profile", return_value=(entry, profile)), \
         patch("qaagent.commands.analyze_cmd.discover_routes") as mock_discover, \
         patch("qaagent.commands.analyze_cmd.export_routes"):
        mock_discover.return_value = []
        result = runner.invoke(
            app,
            [
                "analyze",
                "routes",
                "--crawl",
                "--out",
                str(out_file),
            ],
            env={"API_TOKEN": "secret"},
        )

    assert result.exit_code == 0
    kwargs = mock_discover.call_args.kwargs
    assert kwargs["crawl_url"] == "https://secure.example.com"
    assert kwargs["crawl_headers"]["X-Tenant"] == "acme"
    assert kwargs["crawl_headers"]["Authorization"] == "Bearer secret"
