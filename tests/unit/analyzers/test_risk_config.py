from __future__ import annotations

from pathlib import Path

from qaagent.analyzers.risk_config import RiskConfig


def test_risk_config_loads_defaults(tmp_path: Path) -> None:
    config = RiskConfig.load(tmp_path / "missing.yaml")
    assert config.max_total == 100.0
    assert config.weights.security == 3.0
    assert config.bands[0].name == "P0"


def test_risk_config_loads_file(tmp_path: Path) -> None:
    yaml_content = """
scoring:
  weights:
    security: 4.0
    coverage: 1.5
  caps:
    max_total: 90
prioritization:
  bands:
    - { name: "Critical", min_score: 85 }
    - { name: "High", min_score: 70 }
"""
    config_file = tmp_path / "risk.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    config = RiskConfig.load(config_file)
    assert config.max_total == 90.0
    assert config.weights.security == 4.0
    assert config.weights.coverage == 1.5
    assert config.bands[0].name == "Critical"
