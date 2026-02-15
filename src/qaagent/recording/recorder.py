"""Playwright-based flow recording with bounded capture."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

from .models import RecordedAction, RecordedFlow
from .selectors import choose_best_selector

RECORDER_INIT_SCRIPT = r"""
(() => {
  if (window.__qaagentRecorder) return;

  const state = {
    running: false,
    events: [],
    handlers: {},
  };

  const textOf = (node) => {
    if (!node) return '';
    const value = (node.innerText || node.textContent || '').trim();
    return value.slice(0, 120);
  };

  const cssPath = (el) => {
    if (!el || !el.tagName) return '';
    if (el.id) return `#${el.id}`;
    const parts = [];
    let node = el;
    while (node && node.nodeType === Node.ELEMENT_NODE && parts.length < 6) {
      let part = node.tagName.toLowerCase();
      if (node.className && typeof node.className === 'string') {
        const cls = node.className.trim().split(/\s+/).filter(Boolean).slice(0, 2);
        if (cls.length) {
          part += '.' + cls.join('.');
        }
      }
      if (node.parentElement) {
        const siblings = Array.from(node.parentElement.children).filter(ch => ch.tagName === node.tagName);
        if (siblings.length > 1) {
          const idx = siblings.indexOf(node) + 1;
          part += `:nth-of-type(${idx})`;
        }
      }
      parts.unshift(part);
      node = node.parentElement;
    }
    return parts.join(' > ');
  };

  const targetSnapshot = (target) => {
    if (!target || !target.getAttribute) return {};
    return {
      tag: (target.tagName || '').toLowerCase(),
      role: target.getAttribute('role') || null,
      id: target.getAttribute('id') || null,
      name: target.getAttribute('name') || null,
      type: target.getAttribute('type') || null,
      text: textOf(target),
      aria_label: target.getAttribute('aria-label') || null,
      testid:
        target.getAttribute('data-testid') ||
        target.getAttribute('data-test-id') ||
        target.getAttribute('data-test') ||
        target.getAttribute('data-qa') ||
        target.getAttribute('data-cy') ||
        null,
      css_path: cssPath(target),
    };
  };

  const pushEvent = (eventType, target, value) => {
    state.events.push({
      type: eventType,
      timestamp: Date.now(),
      url: window.location.href,
      value: value ?? null,
      target: targetSnapshot(target),
    });
  };

  const onClick = (ev) => pushEvent('click', ev.target, null);
  const onInput = (ev) => pushEvent('input', ev.target, ev.target && 'value' in ev.target ? ev.target.value : null);
  const onChange = (ev) => pushEvent('change', ev.target, ev.target && 'value' in ev.target ? ev.target.value : null);
  const onSubmit = (ev) => pushEvent('submit', ev.target, null);

  state.handlers = { onClick, onInput, onChange, onSubmit };

  window.__qaagentRecorder = {
    start: () => {
      if (state.running) return;
      state.running = true;
      document.addEventListener('click', state.handlers.onClick, true);
      document.addEventListener('input', state.handlers.onInput, true);
      document.addEventListener('change', state.handlers.onChange, true);
      document.addEventListener('submit', state.handlers.onSubmit, true);
    },
    stop: () => {
      if (!state.running) return;
      state.running = false;
      document.removeEventListener('click', state.handlers.onClick, true);
      document.removeEventListener('input', state.handlers.onInput, true);
      document.removeEventListener('change', state.handlers.onChange, true);
      document.removeEventListener('submit', state.handlers.onSubmit, true);
    },
    drain: () => {
      const out = state.events.slice();
      state.events = [];
      return out;
    },
  };
})();
"""

_SENSITIVE_FIELD_RE = re.compile(r"(password|secret|token|api[_-]?key|auth)", flags=re.IGNORECASE)
_TOKENISH_RE = re.compile(r"^[A-Za-z0-9_\-]{24,}$")
_REDACTED = "***REDACTED***"


def _canonical_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"}:
        return raw_url
    path = parsed.path or "/"
    while "//" in path:
        path = path.replace("//", "/")
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    normalized = parsed._replace(path=path, fragment="")
    return urlunparse(normalized)


def _is_sensitive_target(target: Dict[str, Any]) -> bool:
    for key in ("name", "id", "text", "aria_label", "testid"):
        value = target.get(key)
        if isinstance(value, str) and _SENSITIVE_FIELD_RE.search(value):
            return True
    ttype = target.get("type")
    if isinstance(ttype, str) and _SENSITIVE_FIELD_RE.search(ttype):
        return True
    return False


def _redact_value(target: Dict[str, Any], value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if _is_sensitive_target(target):
        return _REDACTED
    if isinstance(value, str) and _TOKENISH_RE.match(value.strip()):
        return _REDACTED
    return value


def _normalize_raw_event(index: int, raw: Dict[str, Any]) -> RecordedAction:
    event_type = str(raw.get("type") or "").lower()
    timestamp = float(raw.get("timestamp") or int(time.time() * 1000))
    target = raw.get("target") if isinstance(raw.get("target"), dict) else {}
    url = raw.get("url")
    if isinstance(url, str):
        url = _canonical_url(url)

    selector = choose_best_selector(target)
    text = target.get("text") if isinstance(target.get("text"), str) and target.get("text") else None

    action = "unknown"
    value: Optional[str] = None

    if event_type == "navigation":
        action = "navigate"
        selector = None
    elif event_type == "click":
        action = "click"
    elif event_type in {"input", "change"}:
        action = "fill"
        raw_value = raw.get("value")
        if raw_value is not None:
            value = _redact_value(target, str(raw_value))
    elif event_type == "submit":
        action = "submit"
    else:
        action = event_type or "unknown"

    return RecordedAction(
        index=index,
        action=action,
        timestamp=timestamp / 1000.0,
        selector=selector,
        value=value,
        url=url,
        text=text,
        metadata={"target": target, "event_type": event_type},
    )


def _coalesce(actions: List[RecordedAction], incoming: RecordedAction) -> None:
    """Coalesce rapid duplicate fill actions on the same selector."""
    if not actions:
        actions.append(incoming)
        return

    prev = actions[-1]
    if (
        incoming.action == "fill"
        and prev.action == "fill"
        and incoming.selector
        and incoming.selector == prev.selector
        and abs(incoming.timestamp - prev.timestamp) <= 1.0
    ):
        prev.value = incoming.value
        prev.timestamp = incoming.timestamp
        return

    if incoming.action == "navigate" and prev.action == "navigate" and incoming.url == prev.url:
        return

    actions.append(incoming)


def save_recording(flow: RecordedFlow, output_dir: Path) -> Path:
    """Persist recorded flow to output directory as JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "recording.json"
    path.write_text(json.dumps(flow.to_dict(), indent=2), encoding="utf-8")
    return path


def record_flow(
    *,
    name: str,
    start_url: str,
    timeout_seconds: float = 30.0,
    max_actions: int = 100,
    browser: str = "chromium",
    headless: bool = True,
    headers: Optional[Dict[str, str]] = None,
    storage_state_path: Optional[Path | str] = None,
    poll_interval: float = 0.25,
) -> RecordedFlow:
    """Record a browser flow by draining injected DOM event queues."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be > 0")
    if max_actions < 1:
        raise ValueError("max_actions must be >= 1")
    if poll_interval <= 0:
        raise ValueError("poll_interval must be > 0")

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Playwright is required for recording. Install UI extras: pip install -e .[ui]"
        ) from exc

    resolved_state: Optional[Path] = None
    if storage_state_path is not None:
        resolved_state = Path(storage_state_path).expanduser()
        if not resolved_state.is_absolute():
            resolved_state = (Path.cwd() / resolved_state).resolve()
        if not resolved_state.exists():
            raise FileNotFoundError(f"Storage state file not found: {resolved_state}")

    actions: List[RecordedAction] = []
    nav_events: List[Dict[str, Any]] = []

    with sync_playwright() as pw:
        browser_type = getattr(pw, browser, None)
        if browser_type is None:
            raise ValueError("Unsupported browser. Use one of: chromium, firefox, webkit")

        browser_instance = browser_type.launch(headless=headless)
        context = None
        page = None
        try:
            context_kwargs: Dict[str, Any] = {}
            if headers:
                context_kwargs["extra_http_headers"] = headers
            if resolved_state is not None:
                context_kwargs["storage_state"] = resolved_state.as_posix()
            context = browser_instance.new_context(**context_kwargs)
            page = context.new_page()

            def on_navigated(frame):
                if frame != page.main_frame:
                    return
                nav_events.append(
                    {
                        "type": "navigation",
                        "timestamp": int(time.time() * 1000),
                        "url": _canonical_url(frame.url),
                        "target": {},
                    }
                )

            page.on("framenavigated", on_navigated)
            page.add_init_script(RECORDER_INIT_SCRIPT)
            page.goto(start_url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000))
            page.evaluate("window.__qaagentRecorder && window.__qaagentRecorder.start && window.__qaagentRecorder.start()")

            start = time.monotonic()
            while len(actions) < max_actions and (time.monotonic() - start) < timeout_seconds:
                if nav_events:
                    pending_nav = nav_events[:]
                    nav_events.clear()
                    for raw in pending_nav:
                        normalized = _normalize_raw_event(len(actions), raw)
                        _coalesce(actions, normalized)
                        if len(actions) >= max_actions:
                            break
                if len(actions) >= max_actions:
                    break

                drained = page.evaluate(
                    "window.__qaagentRecorder && window.__qaagentRecorder.drain ? window.__qaagentRecorder.drain() : []"
                )
                if isinstance(drained, list):
                    for raw in drained:
                        if not isinstance(raw, dict):
                            continue
                        normalized = _normalize_raw_event(len(actions), raw)
                        _coalesce(actions, normalized)
                        if len(actions) >= max_actions:
                            break
                time.sleep(poll_interval)

            # Ensure listeners are removed before exit.
            page.evaluate("window.__qaagentRecorder && window.__qaagentRecorder.stop && window.__qaagentRecorder.stop()")
        finally:
            if page is not None:
                page.close()
            if context is not None:
                context.close()
            browser_instance.close()

    # Reindex after coalescing to keep sequential action indices.
    for idx, action in enumerate(actions):
        action.index = idx

    return RecordedFlow(
        name=name,
        start_url=_canonical_url(start_url),
        actions=actions,
        created_at=datetime.now(timezone.utc).isoformat(),
        metadata={
            "browser": browser,
            "headless": headless,
            "timeout_seconds": timeout_seconds,
            "max_actions": max_actions,
        },
    )

