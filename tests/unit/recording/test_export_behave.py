"""Tests for Behave recording export."""
from __future__ import annotations

from qaagent.recording.export_behave import render_feature, render_step_stubs
from qaagent.recording.models import RecordedAction, RecordedFlow


def test_render_feature_contains_recorded_steps():
    flow = RecordedFlow(
        name="Login Flow",
        start_url="https://app.example.com/login",
        actions=[
            RecordedAction(index=0, action="fill", timestamp=1.0, selector='[name="email"]', value="qa@example.com"),
            RecordedAction(index=1, action="submit", timestamp=2.0, selector='form[data-testid="login-form"]'),
            RecordedAction(index=2, action="navigate", timestamp=3.0, url="https://app.example.com/dashboard"),
        ],
    )

    feature = render_feature(flow)
    assert 'Given I open "https://app.example.com/login"' in feature
    assert 'When I fill "[name=\\"email\\"]" with "qa@example.com"' in feature
    assert 'When I submit "form[data-testid=\\"login-form\\"]"' in feature
    assert 'Then I should be on "https://app.example.com/dashboard"' in feature


def test_render_step_stubs_contains_core_steps():
    steps = render_step_stubs()
    assert 'I open "{url}"' in steps
    assert 'I click "{selector}"' in steps
    assert 'I should be on "{url}"' in steps

