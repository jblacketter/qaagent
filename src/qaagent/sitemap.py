from __future__ import annotations

from typing import List


def fetch_sitemap_urls(base_url: str, limit: int = 50) -> List[str]:
    try:
        import httpx  # type: ignore
        import xml.etree.ElementTree as ET
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "Sitemap fetching requires httpx. Install API extras: pip install -e .[api]"
        ) from e

    url = base_url.rstrip("/") + "/sitemap.xml"
    r = httpx.get(url, timeout=15.0)
    r.raise_for_status()
    text = r.text
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:  # noqa: BLE001
        raise RuntimeError("Invalid sitemap.xml format") from e

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = []
    for loc in root.findall(".//sm:loc", ns):
        if loc.text:
            locs.append(loc.text.strip())
            if len(locs) >= limit:
                break
    return locs

