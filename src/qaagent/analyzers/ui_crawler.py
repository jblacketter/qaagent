"""Live UI crawling helpers for runtime route discovery."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

_WAIT_UNTIL_VALUES = {"load", "domcontentloaded", "networkidle", "commit"}


@dataclass(frozen=True)
class CrawlPage:
    """Normalized page discovered during crawl traversal."""

    url: str
    path: str
    title: str
    depth: int
    internal: bool


def _normalize_path(path: str) -> str:
    value = (path or "").strip() or "/"
    if not value.startswith("/"):
        value = "/" + value
    while "//" in value:
        value = value.replace("//", "/")
    if len(value) > 1 and value.endswith("/"):
        value = value[:-1]
    return value


def _canonical_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    path = _normalize_path(parsed.path or "/")
    clean = parsed._replace(query="", fragment="", path=path)
    return urlunparse(clean)


def _is_http_url(raw_url: str) -> bool:
    scheme = urlparse(raw_url).scheme.lower()
    return scheme in {"http", "https"}


def _is_internal(raw_url: str, origin_host: str) -> bool:
    return urlparse(raw_url).netloc.lower() == origin_host.lower()


def crawl_ui_routes(
    *,
    start_url: str,
    max_depth: int = 2,
    max_pages: int = 50,
    same_origin: bool = True,
    timeout_seconds: float = 20.0,
    wait_until: str = "networkidle",
    browser: str = "chromium",
    headless: bool = True,
    max_links_per_page: int = 200,
    headers: Optional[Dict[str, str]] = None,
    storage_state_path: Optional[Path | str] = None,
) -> List[CrawlPage]:
    """Crawl links from a starting URL and return normalized page records."""
    if not _is_http_url(start_url):
        raise ValueError("start_url must be an http/https URL.")
    if max_depth < 0:
        raise ValueError("max_depth must be >= 0")
    if max_pages < 1:
        raise ValueError("max_pages must be >= 1")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be > 0")
    if wait_until not in _WAIT_UNTIL_VALUES:
        raise ValueError(
            f"Unsupported wait strategy '{wait_until}'. Use one of: {', '.join(sorted(_WAIT_UNTIL_VALUES))}"
        )
    if max_links_per_page < 1:
        raise ValueError("max_links_per_page must be >= 1")

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Playwright is required for UI crawling. Install UI extras: pip install -e .[ui]"
        ) from exc

    canonical_start = _canonical_url(start_url)
    start_host = urlparse(canonical_start).netloc
    visited: Set[str] = set()
    queued: Set[str] = {canonical_start}
    queue: deque[Tuple[str, int]] = deque([(canonical_start, 0)])
    pages: List[CrawlPage] = []

    resolved_state: Optional[Path] = None
    if storage_state_path is not None:
        resolved_state = Path(storage_state_path).expanduser()
        if not resolved_state.is_absolute():
            resolved_state = (Path.cwd() / resolved_state).resolve()
        if not resolved_state.exists():
            raise FileNotFoundError(f"Storage state file not found: {resolved_state}")

    with sync_playwright() as pw:
        browser_type = getattr(pw, browser, None)
        if browser_type is None:
            raise ValueError("Unsupported browser. Use one of: chromium, firefox, webkit")

        browser_instance = browser_type.launch(headless=headless)
        context = None
        try:
            context_kwargs: Dict[str, Any] = {}
            if headers:
                context_kwargs["extra_http_headers"] = headers
            if resolved_state is not None:
                context_kwargs["storage_state"] = resolved_state.as_posix()

            context = browser_instance.new_context(**context_kwargs)

            while queue and len(pages) < max_pages:
                candidate_url, depth = queue.popleft()
                if candidate_url in visited:
                    continue
                visited.add(candidate_url)

                page = context.new_page()
                try:
                    page.goto(candidate_url, wait_until=wait_until, timeout=int(timeout_seconds * 1000))
                    current_url = _canonical_url(page.url or candidate_url)
                    title = (page.title() or "").strip()
                    internal = _is_internal(current_url, start_host)
                    pages.append(
                        CrawlPage(
                            url=current_url,
                            path=_normalize_path(urlparse(current_url).path),
                            title=title,
                            depth=depth,
                            internal=internal,
                        )
                    )

                    if depth >= max_depth:
                        continue

                    hrefs = page.eval_on_selector_all(
                        "a[href]",
                        "els => els.map(el => el.getAttribute('href')).filter(Boolean)",
                    )
                    candidates: List[str] = []
                    if isinstance(hrefs, list):
                        for raw in hrefs:
                            if not isinstance(raw, str):
                                continue
                            href = raw.strip()
                            if not href:
                                continue
                            if href.startswith(("javascript:", "mailto:", "tel:")):
                                continue
                            absolute = _canonical_url(urljoin(current_url, href))
                            if not _is_http_url(absolute):
                                continue
                            if same_origin and not _is_internal(absolute, start_host):
                                continue
                            candidates.append(absolute)

                    for next_url in sorted(set(candidates))[:max_links_per_page]:
                        if next_url in visited or next_url in queued:
                            continue
                        queue.append((next_url, depth + 1))
                        queued.add(next_url)
                finally:
                    page.close()
        finally:
            if context is not None:
                context.close()
            browser_instance.close()

    return pages

