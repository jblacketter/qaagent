from pathlib import Path

import pytest

pytest.importorskip("yaml")

from qaagent.report import analyze_extras


def test_analyze_extras_parses_a11y_lighthouse_perf_and_api(tmp_path: Path, monkeypatch):
    # Point working directory to project root so openapi.yaml is discoverable
    # Artifacts collected mimic the report.collect_artifacts output
    root = Path.cwd()
    artifacts = {
        "json": [
            str(root / "tests/data/a11y_example.json"),
            str(root / "tests/data/lighthouse_sample.json"),
        ],
        "csv": [str(root / "tests/data/perf_stats.csv")],
        "junit": [str(root / "tests/data/junit_schemathesis.xml")],
        "html_reports": [],
        "videos": [],
        "traces": [],
        "screenshots": [],
    }

    extras = analyze_extras(artifacts)
    assert "a11y" in extras and extras["a11y"]["violations"] >= 1
    assert "lighthouse" in extras and "scores" in extras["lighthouse"]
    assert "perf" in extras and "requests" in extras["perf"]
    # API coverage should be computed since tests/data/openapi.yaml exists and junit references GET /users
    assert "api_coverage" in extras and extras["api_coverage"]["total"] >= 1
