"""Playwright exporter for recorded flows."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .models import RecordedFlow

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_]+")


def _safe_name(value: str) -> str:
    cleaned = _SAFE_NAME_RE.sub("_", value.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "recorded_flow"


def render_playwright_spec(flow: RecordedFlow) -> str:
    """Render a TypeScript Playwright spec for a recorded flow."""
    lines = [
        "import { test, expect } from '@playwright/test';",
        "",
        f"test('{_safe_name(flow.name)}', async ({{ page }}) => {{",
        f"  await page.goto({json.dumps(flow.start_url)});",
        f"  await expect(page).toHaveURL({json.dumps(flow.start_url)});",
    ]

    for action in flow.actions:
        if action.action == "navigate" and action.url:
            lines.append(f"  await page.goto({json.dumps(action.url)});")
            lines.append(f"  await expect(page).toHaveURL({json.dumps(action.url)});")
        elif action.action == "click" and action.selector:
            lines.append(f"  await page.click({json.dumps(action.selector)});")
        elif action.action == "fill" and action.selector:
            lines.append(f"  await page.fill({json.dumps(action.selector)}, {json.dumps(action.value or '')});")
        elif action.action == "submit" and action.selector:
            lines.append(f"  await page.press({json.dumps(action.selector)}, 'Enter');")
        elif action.action == "submit":
            lines.append("  // Submit action captured without selector context.")

    lines.append("});")
    return "\n".join(lines) + "\n"


def export_playwright_spec(flow: RecordedFlow, out_file: Path) -> Path:
    """Write rendered Playwright spec to output path."""
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(render_playwright_spec(flow), encoding="utf-8")
    return out_file

