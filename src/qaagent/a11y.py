from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


AXE_CDN = "https://cdn.jsdelivr.net/npm/axe-core@4.7.0/axe.min.js"


@dataclass
class A11yResult:
    url: str
    violations: List[Dict]
    passes: int
    incomplete: int
    inapplicable: int


def run_axe(
    urls: List[str],
    outdir: Path,
    tags: Optional[List[str]] = None,
    axe_source_url: Optional[str] = AXE_CDN,
    browser: str = "chromium",
) -> Dict[str, object]:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "Playwright is required for a11y checks. Install UI extras: pip install -e .[ui]"
        ) from e

    outdir.mkdir(parents=True, exist_ok=True)
    results: List[A11yResult] = []

    with sync_playwright() as pw:
        browser_type = getattr(pw, browser)
        b = browser_type.launch(headless=True)
        try:
            for url in urls:
                page = b.new_page()
                page.goto(url, wait_until="networkidle")
                if axe_source_url:
                    page.add_script_tag(url=axe_source_url)
                # axe config
                if tags:
                    cfg = {
                        "runOnly": {
                            "type": "tag",
                            "values": tags,
                        }
                    }
                    res = page.evaluate("async (cfg) => await axe.run(document, cfg)", cfg)
                else:
                res = page.evaluate("async () => await axe.run(document)")

                # Ensure result tracks the tested URL for downstream reporting
                try:
                    current_url = page.url
                    if isinstance(res, dict):
                        res.setdefault("testUrl", current_url)
                except Exception:
                    pass

                violations = res.get("violations", [])
                passes = len(res.get("passes", []))
                incomplete = len(res.get("incomplete", []))
                inapplicable = len(res.get("inapplicable", []))
                results.append(A11yResult(url, violations, passes, incomplete, inapplicable))
                # Save per-URL JSON
                safe = (
                    url.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_")
                )
                (outdir / f"a11y_{safe}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        finally:
            b.close()

    # Aggregate and write markdown
    total_violations = sum(len(r.violations) for r in results)
    lines: List[str] = ["# Accessibility Findings", ""]
    lines.append(f"- URLs checked: {len(results)}")
    lines.append(f"- Violations groups: {total_violations}")
    lines.append("")
    for r in results:
        lines.append(f"## {r.url}")
        if r.violations:
            for v in r.violations[:100]:
                lines.append(
                    f"- [{v.get('impact','')}] {v.get('id')} - {v.get('help','')} (nodes: {len(v.get('nodes',[]))})"
                )
                if v.get("helpUrl"):
                    lines.append(f"  - {v['helpUrl']}")
        else:
            lines.append("- No violations detected")
        lines.append("")
    md_path = outdir / "report.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "output_markdown": md_path.as_posix(),
        "violations": total_violations,
        "urls": [r.url for r in results],
    }
