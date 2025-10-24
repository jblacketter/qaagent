from __future__ import annotations

from pathlib import Path

import yaml


def test_openapi_contains_expected_paths() -> None:
    """Sanity check for the bundled OpenAPI specification."""
    spec_path = Path(__file__).resolve().parent.parent / "openapi.yaml"
    raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

    assert raw["info"]["title"] == "QA Agent Petstore"
    paths = set(raw["paths"].keys())
    assert "/pets" in paths
    assert "/pets/{pet_id}" in paths
    assert "/owners" in paths
    assert "/stats/species" in paths
