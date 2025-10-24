from pathlib import Path
import pytest

pytest.importorskip("jinja2")

from qaagent.report import generate_report


def test_generate_report_html(tmp_path: Path):
    out = tmp_path / "findings.html"
    meta = generate_report(output=out, sources=[], fmt="html")
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "<!doctype html>" in text.lower()
    assert meta["format"] == "html"
