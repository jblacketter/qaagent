"""Unit tests for notification helpers."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from qaagent.notifications import (
    build_ci_summary,
    render_ci_summary,
    send_email_smtp,
    send_slack_webhook,
)


def _meta(failures: int = 0, errors: int = 0):
    return {
        "output": "reports/findings.md",
        "format": "markdown",
        "summary": {"tests": 10, "failures": failures, "errors": errors, "skipped": 1, "time": 4.2},
        "extras": {
            "api_coverage": {"pct": 80, "uncovered": [{"path": "/x"}]},
            "a11y": {"violations": 2},
            "lighthouse": {"scores": {"performance": 0.91}},
        },
    }


def test_build_ci_summary_failed_status():
    summary = build_ci_summary(_meta(failures=1))
    assert summary["status"] == "failed"
    assert summary["api_coverage_pct"] == 80
    assert summary["a11y_violations"] == 2


def test_build_ci_summary_passed_status():
    summary = build_ci_summary(_meta(failures=0, errors=0))
    assert summary["status"] == "passed"


def test_render_ci_summary():
    text = render_ci_summary(build_ci_summary(_meta()))
    assert "Status: PASSED" in text
    assert "API Coverage: 80%" in text
    assert "Report: reports/findings.md" in text


@patch("qaagent.notifications.urlopen")
def test_send_slack_webhook(mock_urlopen):
    response = MagicMock()
    response.status = 200
    mock_urlopen.return_value.__enter__.return_value = response

    send_slack_webhook("https://example.com/webhook", "hello")

    assert mock_urlopen.called


@patch("qaagent.notifications.smtplib.SMTP")
def test_send_email_smtp(mock_smtp):
    send_email_smtp(
        smtp_host="smtp.example.com",
        smtp_port=587,
        username="user",
        password="pass",
        sender="from@example.com",
        recipients=["to@example.com"],
        subject="Subject",
        body="Body",
    )

    smtp_obj = mock_smtp.return_value.__enter__.return_value
    smtp_obj.starttls.assert_called_once()
    smtp_obj.login.assert_called_once_with("user", "pass")
    smtp_obj.send_message.assert_called_once()
