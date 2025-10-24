from qaagent.report import summarize_code_coverage


def test_summarize_code_coverage_parses_line_and_branch():
    meta = summarize_code_coverage(["tests/fixtures/data/coverage.xml"])
    assert meta is not None
    assert meta["line"] == 85.0
    assert meta["branch"] == 50.0
