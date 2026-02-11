"""Tests for sitemap.py — fetch_sitemap_urls."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


VALID_SITEMAP = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/</loc></url>
  <url><loc>https://example.com/about</loc></url>
  <url><loc>https://example.com/contact</loc></url>
</urlset>
"""


class TestFetchSitemapUrls:
    def _call(self, base_url="https://example.com", **kwargs):
        """Helper that patches httpx inside the function scope."""
        from qaagent.sitemap import fetch_sitemap_urls
        return fetch_sitemap_urls(base_url, **kwargs)

    @patch("httpx.get")
    def test_parses_urls(self, mock_get):
        response = MagicMock()
        response.text = VALID_SITEMAP
        response.raise_for_status = MagicMock()
        mock_get.return_value = response

        urls = self._call("https://example.com")

        assert urls == [
            "https://example.com/",
            "https://example.com/about",
            "https://example.com/contact",
        ]
        mock_get.assert_called_once_with(
            "https://example.com/sitemap.xml", timeout=15.0
        )

    @patch("httpx.get")
    def test_respects_limit(self, mock_get):
        response = MagicMock()
        response.text = VALID_SITEMAP
        response.raise_for_status = MagicMock()
        mock_get.return_value = response

        urls = self._call("https://example.com", limit=2)

        assert len(urls) == 2

    @patch("httpx.get")
    def test_strips_trailing_slash(self, mock_get):
        response = MagicMock()
        response.text = VALID_SITEMAP
        response.raise_for_status = MagicMock()
        mock_get.return_value = response

        self._call("https://example.com/")

        mock_get.assert_called_once_with(
            "https://example.com/sitemap.xml", timeout=15.0
        )

    @patch("httpx.get")
    def test_invalid_xml_raises(self, mock_get):
        response = MagicMock()
        response.text = "not xml at all <>"
        response.raise_for_status = MagicMock()
        mock_get.return_value = response

        with pytest.raises(RuntimeError, match="Invalid sitemap"):
            self._call("https://example.com")

    @patch("httpx.get")
    def test_http_error_raises(self, mock_get):
        import httpx

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=mock_request, response=mock_response
        )

        with pytest.raises(Exception):
            self._call("https://example.com")
