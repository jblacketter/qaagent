"""Tests for a11y.py — A11yResult and run_axe."""
from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock

from qaagent.a11y import A11yResult, AXE_CDN


class TestA11yResult:
    def test_fields(self):
        result = A11yResult(
            url="https://example.com",
            violations=[{"id": "color-contrast", "impact": "serious"}],
            passes=10,
            incomplete=2,
            inapplicable=5,
        )
        assert result.url == "https://example.com"
        assert len(result.violations) == 1
        assert result.passes == 10


def _setup_playwright_mock(mock_pw_cls, page_evaluate_return):
    """Helper to set up the full playwright mock chain."""
    mock_page = MagicMock()
    mock_page.url = "https://example.com"
    mock_page.evaluate.return_value = page_evaluate_return

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser

    # sync_playwright() returns a context manager
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_pw)
    mock_cm.__exit__ = MagicMock(return_value=False)
    mock_pw_cls.return_value = mock_cm

    return mock_page


class TestRunAxe:
    @patch("playwright.sync_api.sync_playwright")
    def test_run_axe_basic(self, mock_pw_cls, tmp_path):
        from qaagent.a11y import run_axe

        mock_page = _setup_playwright_mock(mock_pw_cls, {
            "violations": [
                {"id": "color-contrast", "impact": "serious", "help": "fix colors", "nodes": [{}]}
            ],
            "passes": [{}] * 5,
            "incomplete": [],
            "inapplicable": [{}] * 3,
        })

        result = run_axe(["https://example.com"], tmp_path)

        assert result["violations"] == 1
        assert result["urls"] == ["https://example.com"]
        assert (tmp_path / "report.md").exists()

        report = (tmp_path / "report.md").read_text()
        assert "color-contrast" in report

    @patch("playwright.sync_api.sync_playwright")
    def test_run_axe_no_violations(self, mock_pw_cls, tmp_path):
        from qaagent.a11y import run_axe

        _setup_playwright_mock(mock_pw_cls, {
            "violations": [],
            "passes": [{}] * 10,
            "incomplete": [],
            "inapplicable": [],
        })

        result = run_axe(["https://example.com"], tmp_path)

        assert result["violations"] == 0
        report = (tmp_path / "report.md").read_text()
        assert "No violations detected" in report

    @patch("playwright.sync_api.sync_playwright")
    def test_run_axe_with_tags(self, mock_pw_cls, tmp_path):
        from qaagent.a11y import run_axe

        mock_page = _setup_playwright_mock(mock_pw_cls, {
            "violations": [],
            "passes": [],
            "incomplete": [],
            "inapplicable": [],
        })

        run_axe(["https://example.com"], tmp_path, tags=["wcag2a"])

        # With tags, evaluate should be called with a config arg
        call_args = mock_page.evaluate.call_args
        assert len(call_args.args) == 2  # (js_code, cfg)

    def test_axe_cdn_constant(self):
        assert "axe-core" in AXE_CDN
        assert AXE_CDN.startswith("https://")
