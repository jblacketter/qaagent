"""Tests for recording session normalization and persistence."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from qaagent.recording.recorder import record_flow, save_recording


class _FakeFrame:
    def __init__(self, url: str = ""):
        self.url = url


class _FakePage:
    def __init__(self, drained_batches):
        self._drained_batches = list(drained_batches)
        self._listeners = {}
        self.main_frame = _FakeFrame()

    def on(self, event: str, callback):
        self._listeners[event] = callback

    def add_init_script(self, script: str):
        return None

    def goto(self, url: str, wait_until: str, timeout: int):
        self.main_frame.url = url
        callback = self._listeners.get("framenavigated")
        if callback:
            callback(self.main_frame)

    def evaluate(self, script: str):
        if "drain" in script:
            if self._drained_batches:
                return self._drained_batches.pop(0)
            return []
        return None

    def close(self):
        return None


class _FakeContext:
    def __init__(self, page):
        self._page = page

    def new_page(self):
        return self._page

    def close(self):
        return None


def _setup_playwright_mock(mock_sync_playwright, drained_batches):
    page = _FakePage(drained_batches)
    context = _FakeContext(page)

    browser_instance = MagicMock()
    browser_instance.new_context.return_value = context

    browser_type = MagicMock()
    browser_type.launch.return_value = browser_instance

    pw_obj = SimpleNamespace(
        chromium=browser_type,
        firefox=MagicMock(),
        webkit=MagicMock(),
    )
    cm = MagicMock()
    cm.__enter__.return_value = pw_obj
    cm.__exit__.return_value = False
    mock_sync_playwright.return_value = cm
    return page


@patch("playwright.sync_api.sync_playwright")
def test_record_flow_captures_and_coalesces_fill_events(mock_sync_playwright):
    drained = [
        [
            {
                "type": "input",
                "timestamp": 1_000,
                "url": "https://app.example.com/login",
                "value": "q",
                "target": {"name": "email", "css_path": 'input[name="email"]', "text": "", "type": "text"},
            },
            {
                "type": "input",
                "timestamp": 1_200,
                "url": "https://app.example.com/login",
                "value": "qa@example.com",
                "target": {"name": "email", "css_path": 'input[name="email"]', "text": "", "type": "text"},
            },
            {
                "type": "click",
                "timestamp": 2_000,
                "url": "https://app.example.com/login",
                "value": None,
                "target": {"testid": "submit-login", "text": "Sign in"},
            },
        ],
        [],
    ]
    _setup_playwright_mock(mock_sync_playwright, drained)

    flow = record_flow(
        name="login",
        start_url="https://app.example.com/login",
        timeout_seconds=0.4,
        max_actions=10,
        poll_interval=0.05,
    )

    # One navigation + one coalesced fill + one click.
    assert len(flow.actions) == 3
    assert flow.actions[0].action == "navigate"
    assert flow.actions[1].action == "fill"
    assert flow.actions[1].value == "qa@example.com"
    assert flow.actions[2].selector == '[data-testid="submit-login"]'


@patch("playwright.sync_api.sync_playwright")
def test_record_flow_redacts_sensitive_values(mock_sync_playwright):
    drained = [
        [
            {
                "type": "input",
                "timestamp": 1_000,
                "url": "https://app.example.com/login",
                "value": "super-secret",
                "target": {"name": "password", "css_path": 'input[name="password"]', "type": "password"},
            }
        ],
        [],
    ]
    _setup_playwright_mock(mock_sync_playwright, drained)

    flow = record_flow(
        name="login",
        start_url="https://app.example.com/login",
        timeout_seconds=0.3,
        max_actions=10,
        poll_interval=0.05,
    )
    assert any(action.value == "***REDACTED***" for action in flow.actions if action.action == "fill")


def test_save_recording_writes_json(tmp_path: Path):
    # Build a minimal flow object to exercise save path expectations.
    from qaagent.recording.models import RecordedFlow

    rec = RecordedFlow(name="demo", start_url="https://app.example.com", actions=[], created_at="2026-02-15T00:00:00Z")
    out = save_recording(rec, tmp_path)
    assert out.exists()
    assert out.name == "recording.json"
