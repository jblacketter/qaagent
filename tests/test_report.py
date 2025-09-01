from pathlib import Path

from qaagent.report import generate_report


def test_generate_report_creates_file(tmp_path: Path):
    out = tmp_path / "findings.md"
    meta = generate_report(output=out, sources=[])
    assert out.exists()
    assert meta["output"] == out.as_posix()
    assert "summary" in meta and isinstance(meta["summary"], dict)

