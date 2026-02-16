"""Unit tests for UI route crawler."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from qaagent.analyzers.ui_crawler import crawl_ui_routes


@dataclass
class _FakePage:
    graph: dict[str, list[str]]
    titles: dict[str, str]
    current_url: str = ""

    @property
    def url(self) -> str:
        return self.current_url

    def goto(self, url: str, wait_until: str, timeout: int) -> None:
        self.current_url = url

    def title(self) -> str:
        return self.titles.get(self.current_url, "")

    def eval_on_selector_all(self, selector: str, script: str):
        return self.graph.get(self.current_url, [])

    def close(self) -> None:
        return None


class _FakeContext:
    def __init__(self, graph: dict[str, list[str]], titles: dict[str, str]):
        self.graph = graph
        self.titles = titles

    def new_page(self) -> _FakePage:
        return _FakePage(self.graph, self.titles)

    def close(self) -> None:
        return None


def _build_playwright_mock(mock_sync_playwright, graph: dict[str, list[str]], titles: dict[str, str]):
    context = _FakeContext(graph, titles)
    mock_browser_instance = MagicMock()
    mock_browser_instance.new_context.return_value = context

    mock_browser_type = MagicMock()
    mock_browser_type.launch.return_value = mock_browser_instance

    pw = SimpleNamespace(
        chromium=mock_browser_type,
        firefox=MagicMock(),
        webkit=MagicMock(),
    )
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = pw
    mock_cm.__exit__.return_value = False
    mock_sync_playwright.return_value = mock_cm
    return mock_browser_instance


class TestCrawlUiRoutes:
    @patch("playwright.sync_api.sync_playwright")
    def test_crawl_same_origin_normalizes_paths(self, mock_sync_playwright):
        graph = {
            "https://app.example.com/": [
                "/dashboard?tab=summary",
                "/settings/",
                "https://external.example.com/docs",
                "/dashboard/",
            ],
            "https://app.example.com/dashboard": ["/reports#weekly", "/settings"],
            "https://app.example.com/settings": [],
            "https://app.example.com/reports": [],
        }
        titles = {
            "https://app.example.com/": "Home",
            "https://app.example.com/dashboard": "Dashboard",
            "https://app.example.com/settings": "Settings",
            "https://app.example.com/reports": "Reports",
        }
        _build_playwright_mock(mock_sync_playwright, graph, titles)

        pages = crawl_ui_routes(
            start_url="https://app.example.com/",
            max_depth=2,
            max_pages=10,
            same_origin=True,
        )

        paths = [page.path for page in pages]
        assert paths == ["/", "/dashboard", "/settings", "/reports"]
        assert all(page.internal for page in pages)
        assert pages[-1].depth == 2

    @patch("playwright.sync_api.sync_playwright")
    def test_crawl_can_include_external_links(self, mock_sync_playwright):
        graph = {
            "https://app.example.com/": [
                "/dashboard",
                "https://external.example.com/docs",
            ],
            "https://app.example.com/dashboard": [],
            "https://external.example.com/docs": [],
        }
        titles = {
            "https://app.example.com/": "Home",
            "https://app.example.com/dashboard": "Dashboard",
            "https://external.example.com/docs": "Docs",
        }
        _build_playwright_mock(mock_sync_playwright, graph, titles)

        pages = crawl_ui_routes(
            start_url="https://app.example.com/",
            max_depth=1,
            same_origin=False,
        )

        assert any(page.internal is False for page in pages)
        assert any(page.url.startswith("https://external.example.com") for page in pages)

    @patch("playwright.sync_api.sync_playwright")
    def test_crawl_passes_headers_and_storage_state(self, mock_sync_playwright, tmp_path: Path):
        graph = {"https://app.example.com/": []}
        titles = {"https://app.example.com/": "Home"}
        browser_instance = _build_playwright_mock(mock_sync_playwright, graph, titles)

        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")

        crawl_ui_routes(
            start_url="https://app.example.com/",
            headers={"Authorization": "Bearer token"},
            storage_state_path=state_file,
        )

        kwargs = browser_instance.new_context.call_args.kwargs
        assert kwargs["extra_http_headers"]["Authorization"] == "Bearer token"
        assert kwargs["storage_state"] == state_file.as_posix()

    def test_crawl_validates_inputs(self, tmp_path: Path):
        with pytest.raises(ValueError, match="start_url must be an http/https URL"):
            crawl_ui_routes(start_url="file:///tmp/index.html")

        with pytest.raises(ValueError, match="Unsupported wait strategy"):
            crawl_ui_routes(start_url="https://app.example.com", wait_until="invalid")

        with pytest.raises(FileNotFoundError, match="Storage state file not found"):
            crawl_ui_routes(start_url="https://app.example.com", storage_state_path=tmp_path / "missing-state.json")
