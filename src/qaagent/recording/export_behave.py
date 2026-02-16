"""Behave exporter for recorded flows."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

from .models import RecordedFlow

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_]+")


def _safe_name(value: str) -> str:
    cleaned = _SAFE_NAME_RE.sub("_", value.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "recorded_flow"


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def render_feature(flow: RecordedFlow) -> str:
    """Render a Gherkin feature from a recorded flow."""
    scenario_name = _safe_name(flow.name).replace("_", " ")
    lines = [
        "Feature: Recorded user flow",
        "",
        f"  Scenario: {scenario_name}",
        f'    Given I open "{_quote(flow.start_url)}"',
    ]

    for action in flow.actions:
        if action.action == "navigate" and action.url:
            lines.append(f'    Then I should be on "{_quote(action.url)}"')
        elif action.action == "click" and action.selector:
            lines.append(f'    When I click "{_quote(action.selector)}"')
        elif action.action == "fill" and action.selector:
            lines.append(f'    When I fill "{_quote(action.selector)}" with "{_quote(action.value or "")}"')
        elif action.action == "submit":
            if action.selector:
                lines.append(f'    When I submit "{_quote(action.selector)}"')
            else:
                lines.append("    When I submit the current form")

    return "\n".join(lines) + "\n"


def render_step_stubs() -> str:
    """Render reusable Behave step stubs for recorded features."""
    return (
        "from behave import given, when, then\n\n"
        "\n"
        '@given(\'I open "{url}"\')\n'
        "def step_open(context, url):\n"
        "    # TODO: implement browser navigation\n"
        "    pass\n\n"
        '@when(\'I click "{selector}"\')\n'
        "def step_click(context, selector):\n"
        "    # TODO: implement click\n"
        "    pass\n\n"
        '@when(\'I fill "{selector}" with "{value}"\')\n'
        "def step_fill(context, selector, value):\n"
        "    # TODO: implement fill\n"
        "    pass\n\n"
        '@when(\'I submit "{selector}"\')\n'
        "def step_submit(context, selector):\n"
        "    # TODO: implement submit with selector\n"
        "    pass\n\n"
        "@when('I submit the current form')\n"
        "def step_submit_current_form(context):\n"
        "    # TODO: implement generic submit\n"
        "    pass\n\n"
        '@then(\'I should be on "{url}"\')\n'
        "def step_assert_url(context, url):\n"
        "    # TODO: implement URL assertion\n"
        "    pass\n"
    )


def export_behave_assets(flow: RecordedFlow, feature_file: Path, steps_file: Path) -> Tuple[Path, Path]:
    """Write feature file and steps stub for a recorded flow."""
    feature_file.parent.mkdir(parents=True, exist_ok=True)
    steps_file.parent.mkdir(parents=True, exist_ok=True)

    feature_file.write_text(render_feature(flow), encoding="utf-8")
    if not steps_file.exists():
        steps_file.write_text(render_step_stubs(), encoding="utf-8")
    return feature_file, steps_file
