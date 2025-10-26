from __future__ import annotations

from pathlib import Path

from qaagent.analyzers.cuj_config import CUJConfig


def test_cuj_config_loads_defaults(tmp_path: Path) -> None:
    config = CUJConfig.load(tmp_path / "missing.yaml")
    assert config.journeys == []
    assert config.coverage_targets == {}


def test_cuj_config_loads_file(tmp_path: Path) -> None:
    yaml_content = """
product: sonicgrid
journeys:
  - id: auth_login
    name: Login
    components: ["src/auth/*"]
    apis:
      - { method: POST, endpoint: "/api/auth/login" }
    acceptance:
      - "Users can login"
coverage_targets: {auth_login: 80}
"""
    path = tmp_path / "cuj.yaml"
    path.write_text(yaml_content, encoding="utf-8")

    config = CUJConfig.load(path)
    assert config.product == "sonicgrid"
    assert config.journeys[0].id == "auth_login"
    assert config.coverage_targets["auth_login"] == 80.0
