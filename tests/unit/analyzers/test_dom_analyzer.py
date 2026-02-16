"""Unit tests for DOM analyzer helpers."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from qaagent.analyzers.dom_analyzer import build_dom_analysis, run_dom_analysis


def _sample_page_payload():
    return {
        "url": "https://app.example.com/dashboard",
        "title": "Dashboard",
        "element_inventory": {
            "total": 120,
            "interactive": 10,
            "by_tag": {"button": 8, "a": 12, "input": 5},
        },
        "selector_signals": {
            "with_testid": 2,
            "with_aria": 3,
            "with_role": 2,
            "with_id_or_name": 5,
            "stable_total": 6,
            "missing_stable": 4,
        },
        "forms": [
            {
                "index": 0,
                "method": "post",
                "field_count": 2,
                "fields": [
                    {"index": 0, "tag": "input", "name": "email", "has_label": True},
                    {"index": 1, "tag": "input", "name": "password", "has_label": False},
                ],
                "submit_controls": [{"tag": "button", "text": "Sign in"}],
            }
        ],
        "nav_links": [
            {"href": "/profile", "text": "Profile"},
            {"href": "https://external.example.org/docs", "text": "External Docs"},
        ],
    }


class TestBuildDomAnalysis:
    def test_builds_summary_and_recommendations(self):
        analysis = build_dom_analysis(
            [_sample_page_payload()],
            target_url="https://app.example.com/dashboard",
            browser="chromium",
            headless=True,
            timeout_seconds=30.0,
            wait_until="networkidle",
        )

        assert analysis["summary"]["pages_analyzed"] == 1
        assert analysis["summary"]["interactive_elements"] == 10
        assert analysis["summary"]["forms_total"] == 1
        assert analysis["summary"]["unlabeled_fields_total"] == 1

        selector = analysis["summary"]["selector_strategy"]
        assert selector["stable_selector_coverage_pct"] == 60.0
        assert selector["testid_coverage_pct"] == 20.0
        assert selector["aria_coverage_pct"] == 30.0

        recs = analysis["recommendations"]
        assert any("data-testid" in item for item in recs)
        assert any("labeling" in item.lower() for item in recs)

    def test_excludes_external_links_by_default(self):
        analysis = build_dom_analysis(
            [_sample_page_payload()],
            target_url="https://app.example.com/dashboard",
            browser="chromium",
            headless=True,
            timeout_seconds=30.0,
            wait_until="networkidle",
            include_external_links=False,
        )
        links = analysis["pages"][0]["nav_links"]
        assert len(links) == 1
        assert links[0]["internal"] is True

        analysis_with_external = build_dom_analysis(
            [_sample_page_payload()],
            target_url="https://app.example.com/dashboard",
            browser="chromium",
            headless=True,
            timeout_seconds=30.0,
            wait_until="networkidle",
            include_external_links=True,
        )
        links_with_external = analysis_with_external["pages"][0]["nav_links"]
        assert len(links_with_external) == 2
        assert any(link["internal"] is False for link in links_with_external)


class TestRunDomAnalysis:
    @patch("playwright.sync_api.sync_playwright")
    def test_runs_playwright_and_writes_output(self, mock_sync_playwright, tmp_path):
        out_path = tmp_path / "dom-analysis.json"

        mock_page = MagicMock()
        mock_page.evaluate.return_value = _sample_page_payload()

        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page

        mock_browser_instance = MagicMock()
        mock_browser_instance.new_context.return_value = mock_context

        mock_browser_type = MagicMock()
        mock_browser_type.launch.return_value = mock_browser_instance

        pw_obj = SimpleNamespace(
            chromium=mock_browser_type,
            firefox=MagicMock(),
            webkit=MagicMock(),
        )
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = pw_obj
        mock_cm.__exit__.return_value = False
        mock_sync_playwright.return_value = mock_cm

        result = run_dom_analysis(
            url="https://app.example.com/dashboard",
            out_path=out_path,
            headers={"Authorization": "Bearer token"},
        )

        assert result["summary"]["pages_analyzed"] == 1
        assert out_path.exists()
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert payload["summary"]["elements_total"] == 120

        context_kwargs = mock_browser_instance.new_context.call_args.kwargs
        assert context_kwargs["extra_http_headers"]["Authorization"] == "Bearer token"

    def test_rejects_invalid_wait_until(self, tmp_path):
        with pytest.raises(ValueError, match="Unsupported wait strategy"):
            run_dom_analysis(
                url="https://app.example.com/dashboard",
                out_path=tmp_path / "dom-analysis.json",
                wait_until="invalid",
            )
