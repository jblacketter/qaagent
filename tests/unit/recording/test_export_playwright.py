"""Tests for Playwright recording export."""
from __future__ import annotations

from qaagent.recording.export_playwright import render_playwright_spec
from qaagent.recording.models import RecordedAction, RecordedFlow


def test_render_playwright_spec_includes_navigation_and_actions():
    flow = RecordedFlow(
        name="Checkout Flow",
        start_url="https://app.example.com",
        actions=[
            RecordedAction(index=0, action="navigate", timestamp=1.0, url="https://app.example.com/cart"),
            RecordedAction(index=1, action="fill", timestamp=2.0, selector='[name="email"]', value="qa@example.com"),
            RecordedAction(index=2, action="click", timestamp=3.0, selector='[data-testid="checkout"]'),
        ],
    )

    rendered = render_playwright_spec(flow)
    assert "test('Checkout_Flow'" in rendered
    assert "await page.goto(\"https://app.example.com/cart\")" in rendered
    assert "await expect(page).toHaveURL(\"https://app.example.com/cart\")" in rendered
    assert "await page.fill(\"[name=\\\"email\\\"]\", \"qa@example.com\")" in rendered
    assert "await page.click(\"[data-testid=\\\"checkout\\\"]\")" in rendered

