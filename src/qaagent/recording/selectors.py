"""Selector ranking and extraction for recorded interactions."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from .models import SelectorCandidate

_UNSAFE_CHARS = re.compile(r'["\\]')


def _escape(value: str) -> str:
    return _UNSAFE_CHARS.sub(lambda m: f"\\{m.group(0)}", value)


def build_selector_candidates(target: Dict[str, object] | None) -> List[SelectorCandidate]:
    """Build ordered selector candidates from a target snapshot."""
    if not target:
        return []

    candidates: List[SelectorCandidate] = []

    for testid_key in ("testid", "data_testid", "data_test_id", "data_test", "data_qa", "data_cy"):
        raw = target.get(testid_key)
        if isinstance(raw, str) and raw.strip():
            val = raw.strip()
            candidates.append(
                SelectorCandidate("data-testid", f'[data-testid="{_escape(val)}"]', 100, {"raw": val})
            )
            break

    role = target.get("role")
    aria_label = target.get("aria_label")
    if isinstance(role, str) and role.strip() and isinstance(aria_label, str) and aria_label.strip():
        candidates.append(
            SelectorCandidate(
                "role+aria-label",
                f'[role="{_escape(role.strip())}"][aria-label="{_escape(aria_label.strip())}"]',
                90,
            )
        )

    if isinstance(aria_label, str) and aria_label.strip():
        candidates.append(
            SelectorCandidate(
                "aria-label",
                f'[aria-label="{_escape(aria_label.strip())}"]',
                85,
            )
        )

    raw_id = target.get("id")
    if isinstance(raw_id, str) and raw_id.strip():
        value = raw_id.strip()
        if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*$", value):
            candidates.append(SelectorCandidate("id", f"#{value}", 80))
        else:
            candidates.append(SelectorCandidate("id", f'[id="{_escape(value)}"]', 80))

    raw_name = target.get("name")
    if isinstance(raw_name, str) and raw_name.strip():
        candidates.append(
            SelectorCandidate("name", f'[name="{_escape(raw_name.strip())}"]', 70)
        )

    css_path = target.get("css_path")
    if isinstance(css_path, str) and css_path.strip():
        candidates.append(SelectorCandidate("css-path", css_path.strip(), 10))

    return sorted(candidates, key=lambda item: item.score, reverse=True)


def choose_best_selector(target: Dict[str, object] | None) -> Optional[str]:
    """Select the highest-ranked selector value from target attributes."""
    candidates = build_selector_candidates(target)
    if not candidates:
        return None
    return candidates[0].value

