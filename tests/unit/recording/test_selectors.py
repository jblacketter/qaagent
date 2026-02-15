"""Tests for selector candidate ranking."""
from __future__ import annotations

from qaagent.recording.selectors import build_selector_candidates, choose_best_selector


def test_prefers_data_testid_first():
    target = {
        "testid": "login-submit",
        "id": "submit-button",
        "name": "submit",
        "css_path": "form > button:nth-of-type(1)",
    }
    selector = choose_best_selector(target)
    assert selector == '[data-testid="login-submit"]'


def test_falls_back_to_aria_then_id_name():
    target = {
        "role": "button",
        "aria_label": "Continue",
        "id": "continue-btn",
        "name": "continue",
    }
    candidates = build_selector_candidates(target)
    assert candidates[0].strategy == "role+aria-label"
    assert choose_best_selector(target) == '[role="button"][aria-label="Continue"]'


def test_returns_none_when_no_target_data():
    assert choose_best_selector({}) is None
    assert choose_best_selector(None) is None

