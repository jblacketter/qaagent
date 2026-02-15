"""Notification helpers for CI summaries (Slack + SMTP email)."""
from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, Iterable
from urllib.request import Request, urlopen


def build_ci_summary(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Build a compact CI-friendly summary payload from report metadata."""
    summary = dict(meta.get("summary", {}) or {})
    extras = dict(meta.get("extras", {}) or {})

    failures = int(summary.get("failures", 0) or 0)
    errors = int(summary.get("errors", 0) or 0)
    payload: Dict[str, Any] = {
        "output": meta.get("output"),
        "format": meta.get("format"),
        "tests": int(summary.get("tests", 0) or 0),
        "failures": failures,
        "errors": errors,
        "skipped": int(summary.get("skipped", 0) or 0),
        "duration_sec": float(summary.get("time", 0.0) or 0.0),
        "status": "failed" if (failures > 0 or errors > 0) else "passed",
    }

    if extras.get("api_coverage"):
        api_cov = extras["api_coverage"]
        payload["api_coverage_pct"] = api_cov.get("pct")
        payload["api_uncovered"] = len(api_cov.get("uncovered", []) or [])

    if extras.get("a11y"):
        payload["a11y_violations"] = extras["a11y"].get("violations")

    if extras.get("lighthouse"):
        scores = extras["lighthouse"].get("scores", {}) or {}
        payload["lighthouse_performance"] = scores.get("performance")

    return payload


def render_ci_summary(summary: Dict[str, Any]) -> str:
    """Render a human-readable CI summary string."""
    lines = [
        f"Status: {summary.get('status', 'unknown').upper()}",
        (
            "Tests: {tests} | Failures: {failures} | Errors: {errors} | "
            "Skipped: {skipped} | Time: {duration_sec:.2f}s"
        ).format(
            tests=summary.get("tests", 0),
            failures=summary.get("failures", 0),
            errors=summary.get("errors", 0),
            skipped=summary.get("skipped", 0),
            duration_sec=float(summary.get("duration_sec", 0.0) or 0.0),
        ),
    ]
    if summary.get("api_coverage_pct") is not None:
        lines.append(
            f"API Coverage: {summary.get('api_coverage_pct')}% (uncovered={summary.get('api_uncovered', 0)})",
        )
    if summary.get("a11y_violations") is not None:
        lines.append(f"A11y Violations: {summary.get('a11y_violations')}")
    if summary.get("lighthouse_performance") is not None:
        lines.append(f"Lighthouse Performance: {summary.get('lighthouse_performance')}")
    if summary.get("output"):
        lines.append(f"Report: {summary.get('output')}")
    return "\n".join(lines)


def send_slack_webhook(webhook_url: str, body: str, title: str = "QAAgent CI Summary", timeout: int = 10) -> None:
    """Post a plain-text summary to a Slack incoming webhook."""
    payload = {"text": f"*{title}*\n{body}"}
    req = Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=timeout) as response:  # noqa: S310 - explicit webhook target from user/config
        status = getattr(response, "status", 200)
        if status >= 400:
            raise RuntimeError(f"Slack webhook returned status {status}")


def send_email_smtp(
    *,
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    sender: str,
    recipients: Iterable[str],
    subject: str,
    body: str,
    use_tls: bool = True,
) -> None:
    """Send a plain-text email summary via SMTP."""
    recipient_list = [addr for addr in recipients if addr]
    if not recipient_list:
        raise ValueError("No recipients specified")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipient_list)
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(msg)
