"""Live DOM analysis helpers for selector strategy and testability insights."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

_WAIT_UNTIL_VALUES = {"load", "domcontentloaded", "networkidle", "commit"}

_DOM_ANALYSIS_SCRIPT = r"""
() => {
  const nodes = Array.from(document.querySelectorAll('*'));
  const tagCounts = {};
  for (const node of nodes) {
    const tag = (node.tagName || '').toLowerCase();
    if (!tag) continue;
    tagCounts[tag] = (tagCounts[tag] || 0) + 1;
  }

  const interactiveSelector = [
    'a[href]',
    'button',
    'input',
    'select',
    'textarea',
    '[role="button"]',
    '[role="link"]',
    '[onclick]',
    '[tabindex]',
  ].join(',');
  const interactiveNodes = Array.from(new Set(document.querySelectorAll(interactiveSelector)));

  const readTestId = (el) =>
    el.getAttribute('data-testid')
      || el.getAttribute('data-test-id')
      || el.getAttribute('data-test')
      || el.getAttribute('data-qa')
      || el.getAttribute('data-cy')
      || null;

  const interactive = [];
  let withTestId = 0;
  let withAria = 0;
  let withRole = 0;
  let withIdOrName = 0;
  let stableTotal = 0;

  for (const el of interactiveNodes) {
    const testid = readTestId(el);
    const ariaLabel = el.getAttribute('aria-label') || null;
    const ariaLabelledBy = el.getAttribute('aria-labelledby') || null;
    const role = el.getAttribute('role') || null;
    const id = el.getAttribute('id') || null;
    const name = el.getAttribute('name') || null;
    const stable = Boolean(testid || ariaLabel || ariaLabelledBy || id || name);

    if (testid) withTestId += 1;
    if (ariaLabel || ariaLabelledBy) withAria += 1;
    if (role) withRole += 1;
    if (id || name) withIdOrName += 1;
    if (stable) stableTotal += 1;

    interactive.push({
      tag: (el.tagName || '').toLowerCase(),
      type: el.getAttribute('type') || null,
      text: (el.innerText || el.value || '').trim().slice(0, 120),
      testid,
      aria_label: ariaLabel,
      role,
      id,
      name,
    });
  }

  const explicitLabels = {};
  for (const label of Array.from(document.querySelectorAll('label[for]'))) {
    const key = label.getAttribute('for');
    if (!key) continue;
    if (!explicitLabels[key]) {
      explicitLabels[key] = (label.textContent || '').trim();
    }
  }

  const forms = Array.from(document.querySelectorAll('form')).map((form, index) => {
    const fields = Array.from(form.querySelectorAll('input,select,textarea')).map((field, fieldIndex) => {
      const fieldId = field.getAttribute('id');
      let labelText = '';
      if (fieldId && explicitLabels[fieldId]) {
        labelText = explicitLabels[fieldId];
      }
      if (!labelText) {
        const wrappingLabel = field.closest('label');
        if (wrappingLabel) {
          labelText = (wrappingLabel.textContent || '').trim();
        }
      }

      const ariaLabel = field.getAttribute('aria-label') || '';
      const ariaLabelledBy = field.getAttribute('aria-labelledby') || '';
      const hasLabel = Boolean(labelText || ariaLabel || ariaLabelledBy);

      return {
        index: fieldIndex,
        tag: (field.tagName || '').toLowerCase(),
        type: field.getAttribute('type') || null,
        id: fieldId || null,
        name: field.getAttribute('name') || null,
        required: field.hasAttribute('required'),
        label: labelText || null,
        aria_label: ariaLabel || null,
        placeholder: field.getAttribute('placeholder') || null,
        has_label: hasLabel,
      };
    });

    const submitControls = Array.from(
      form.querySelectorAll('button[type="submit"],input[type="submit"],button:not([type])')
    ).map((control) => ({
      tag: (control.tagName || '').toLowerCase(),
      text: (control.innerText || control.value || '').trim().slice(0, 80),
      id: control.getAttribute('id') || null,
      testid: readTestId(control),
    }));

    return {
      index,
      id: form.getAttribute('id') || null,
      name: form.getAttribute('name') || null,
      method: (form.getAttribute('method') || 'get').toLowerCase(),
      action: form.getAttribute('action') || null,
      field_count: fields.length,
      fields,
      submit_controls: submitControls,
    };
  });

  const navLinks = [];
  const seenHrefs = new Set();
  for (const link of Array.from(document.querySelectorAll('a[href]'))) {
    const href = link.getAttribute('href');
    if (!href || seenHrefs.has(href)) continue;
    seenHrefs.add(href);
    navLinks.push({
      href,
      text: (link.innerText || '').trim().slice(0, 100),
      testid: readTestId(link),
      aria_label: link.getAttribute('aria-label') || null,
    });
  }

  return {
    url: window.location.href,
    title: document.title || '',
    element_inventory: {
      total: nodes.length,
      interactive: interactiveNodes.length,
      by_tag: tagCounts,
    },
    selector_signals: {
      with_testid: withTestId,
      with_aria: withAria,
      with_role: withRole,
      with_id_or_name: withIdOrName,
      stable_total: stableTotal,
      missing_stable: Math.max(0, interactiveNodes.length - stableTotal),
    },
    forms,
    nav_links: navLinks,
    interactive_elements: interactive,
  };
}
"""


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:  # noqa: BLE001
        return 0


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator * 100.0) / denominator, 1)


def _dedupe(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for value in values:
        key = (value or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(value.strip())
    return ordered


def _normalize_tag_counts(payload: Any) -> Dict[str, int]:
    if not isinstance(payload, dict):
        return {}
    normalized: Dict[str, int] = {}
    for key, value in payload.items():
        tag = str(key).strip().lower()
        if not tag:
            continue
        normalized[tag] = _to_int(value)
    return dict(sorted(normalized.items(), key=lambda item: item[0]))


def _normalize_nav_links(
    *,
    page_url: str,
    links: Any,
    include_external_links: bool,
    max_links: int,
) -> List[Dict[str, Any]]:
    if not isinstance(links, list):
        return []

    parsed_page = urlparse(page_url)
    page_host = parsed_page.netloc.lower()
    normalized: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for item in links:
        if not isinstance(item, dict):
            continue
        href_raw = str(item.get("href") or "").strip()
        if not href_raw:
            continue
        if href_raw.startswith(("javascript:", "mailto:", "tel:")):
            continue

        href_abs = urljoin(page_url, href_raw)
        parsed = urlparse(href_abs)
        if parsed.scheme not in {"http", "https"}:
            continue

        key = href_abs.rstrip("/") or href_abs
        if key in seen:
            continue

        internal = parsed.netloc.lower() == page_host
        if not include_external_links and not internal:
            continue

        seen.add(key)
        normalized.append(
            {
                "href": href_abs,
                "text": str(item.get("text") or "").strip(),
                "testid": item.get("testid"),
                "aria_label": item.get("aria_label"),
                "internal": internal,
            }
        )
        if len(normalized) >= max_links:
            break
    return normalized


def _normalize_forms(payload: Any) -> tuple[List[Dict[str, Any]], int, int]:
    if not isinstance(payload, list):
        return [], 0, 0

    forms: List[Dict[str, Any]] = []
    total_fields = 0
    unlabeled_fields = 0

    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            continue

        fields_raw = item.get("fields")
        fields: List[Dict[str, Any]] = []
        if isinstance(fields_raw, list):
            for field_idx, field in enumerate(fields_raw):
                if not isinstance(field, dict):
                    continue
                has_label = bool(field.get("has_label"))
                field_item = {
                    "index": _to_int(field.get("index", field_idx)),
                    "tag": str(field.get("tag") or "").lower(),
                    "type": field.get("type"),
                    "id": field.get("id"),
                    "name": field.get("name"),
                    "required": bool(field.get("required")),
                    "label": field.get("label"),
                    "aria_label": field.get("aria_label"),
                    "placeholder": field.get("placeholder"),
                    "has_label": has_label,
                }
                if not has_label:
                    unlabeled_fields += 1
                total_fields += 1
                fields.append(field_item)

        submit_controls_raw = item.get("submit_controls")
        submit_controls: List[Dict[str, Any]] = []
        if isinstance(submit_controls_raw, list):
            for control in submit_controls_raw:
                if not isinstance(control, dict):
                    continue
                submit_controls.append(
                    {
                        "tag": str(control.get("tag") or "").lower(),
                        "text": str(control.get("text") or "").strip(),
                        "id": control.get("id"),
                        "testid": control.get("testid"),
                    }
                )

        forms.append(
            {
                "index": _to_int(item.get("index", idx)),
                "id": item.get("id"),
                "name": item.get("name"),
                "method": str(item.get("method") or "get").lower(),
                "action": item.get("action"),
                "field_count": _to_int(item.get("field_count", len(fields))),
                "fields": fields,
                "submit_controls": submit_controls,
            }
        )

    return forms, total_fields, unlabeled_fields


def _recommendations_for_page(page: Dict[str, Any]) -> List[str]:
    inventory = page.get("element_inventory") or {}
    selector = page.get("selector_coverage") or {}
    forms = page.get("forms") or []
    nav_links = page.get("nav_links") or []

    interactive = _to_int(inventory.get("interactive"))
    stable_coverage = float(selector.get("stable_selector_coverage_pct") or 0.0)
    testid_coverage = float(selector.get("testid_coverage_pct") or 0.0)
    aria_coverage = float(selector.get("aria_coverage_pct") or 0.0)

    recs: List[str] = []
    if interactive > 0 and stable_coverage < 70.0:
        recs.append(
            "Increase stable selector coverage (data-testid/ARIA/id-name) on interactive elements.",
        )
    if interactive > 0 and testid_coverage < 40.0:
        recs.append("Adopt data-testid attributes for critical interactive controls.")
    if interactive > 0 and aria_coverage < 60.0:
        recs.append("Improve ARIA labeling to strengthen accessibility-first selectors.")

    unlabeled_fields = 0
    for form in forms:
        for field in form.get("fields", []):
            if isinstance(field, dict) and not bool(field.get("has_label")):
                unlabeled_fields += 1
    if unlabeled_fields > 0:
        recs.append(
            f"Add visible labels or aria-label attributes for {unlabeled_fields} unlabeled form fields.",
        )

    internal_links = sum(1 for link in nav_links if isinstance(link, dict) and bool(link.get("internal")))
    if forms and internal_links == 0:
        recs.append("Add internal navigation coverage; forms were found but no internal links were discovered.")

    return _dedupe(recs)


def build_dom_analysis(
    pages: List[Dict[str, Any]],
    *,
    target_url: str,
    browser: str,
    headless: bool,
    timeout_seconds: float,
    wait_until: str,
    storage_state_used: bool = False,
    headers_used: bool = False,
    include_external_links: bool = False,
    max_links: int = 200,
) -> Dict[str, Any]:
    """Build normalized DOM analysis payload and recommendations."""
    normalized_pages: List[Dict[str, Any]] = []
    all_recommendations: List[str] = []

    total_elements = 0
    total_interactive = 0
    total_forms = 0
    total_fields = 0
    total_unlabeled_fields = 0
    total_nav_links = 0

    total_with_testid = 0
    total_with_aria = 0
    total_with_role = 0
    total_with_id_or_name = 0
    total_stable = 0
    total_missing_stable = 0

    for raw_page in pages:
        page_url = str(raw_page.get("url") or target_url)
        title = str(raw_page.get("title") or "")

        inventory_raw = raw_page.get("element_inventory") or {}
        selector_raw = raw_page.get("selector_signals") or {}

        element_total = _to_int(inventory_raw.get("total"))
        interactive_total = _to_int(inventory_raw.get("interactive"))
        by_tag = _normalize_tag_counts(inventory_raw.get("by_tag"))

        with_testid = _to_int(selector_raw.get("with_testid"))
        with_aria = _to_int(selector_raw.get("with_aria"))
        with_role = _to_int(selector_raw.get("with_role"))
        with_id_or_name = _to_int(selector_raw.get("with_id_or_name"))
        stable_total = _to_int(selector_raw.get("stable_total"))
        missing_stable = _to_int(selector_raw.get("missing_stable", max(0, interactive_total - stable_total)))

        forms, fields_count, unlabeled_fields = _normalize_forms(raw_page.get("forms"))
        nav_links = _normalize_nav_links(
            page_url=page_url,
            links=raw_page.get("nav_links"),
            include_external_links=include_external_links,
            max_links=max_links,
        )

        page_payload: Dict[str, Any] = {
            "url": page_url,
            "title": title,
            "element_inventory": {
                "total": element_total,
                "interactive": interactive_total,
                "by_tag": by_tag,
            },
            "selector_coverage": {
                "testid_elements": with_testid,
                "aria_elements": with_aria,
                "role_elements": with_role,
                "id_or_name_elements": with_id_or_name,
                "stable_selector_elements": stable_total,
                "missing_stable_selectors": missing_stable,
                "testid_coverage_pct": _pct(with_testid, interactive_total),
                "aria_coverage_pct": _pct(with_aria, interactive_total),
                "stable_selector_coverage_pct": _pct(stable_total, interactive_total),
            },
            "forms": forms,
            "nav_links": nav_links,
        }

        page_recommendations = _recommendations_for_page(page_payload)
        page_payload["recommendations"] = page_recommendations
        all_recommendations.extend(page_recommendations)
        normalized_pages.append(page_payload)

        total_elements += element_total
        total_interactive += interactive_total
        total_forms += len(forms)
        total_fields += fields_count
        total_unlabeled_fields += unlabeled_fields
        total_nav_links += len(nav_links)

        total_with_testid += with_testid
        total_with_aria += with_aria
        total_with_role += with_role
        total_with_id_or_name += with_id_or_name
        total_stable += stable_total
        total_missing_stable += missing_stable

    selector_strategy = {
        "testid_coverage_pct": _pct(total_with_testid, total_interactive),
        "aria_coverage_pct": _pct(total_with_aria, total_interactive),
        "stable_selector_coverage_pct": _pct(total_stable, total_interactive),
        "missing_stable_selectors": total_missing_stable,
    }

    summary = {
        "pages_analyzed": len(normalized_pages),
        "elements_total": total_elements,
        "interactive_elements": total_interactive,
        "forms_total": total_forms,
        "fields_total": total_fields,
        "unlabeled_fields_total": total_unlabeled_fields,
        "nav_links_total": total_nav_links,
        "selector_strategy": selector_strategy,
    }

    if total_interactive == 0:
        all_recommendations.append("No interactive elements detected; verify URL/auth state or app readiness.")
    if selector_strategy["stable_selector_coverage_pct"] < 70.0 and total_interactive > 0:
        all_recommendations.append(
            "Prioritize stable selectors (data-testid first, ARIA second, id/name fallback) before scaling UI tests.",
        )
    if total_unlabeled_fields > 0:
        all_recommendations.append(
            "Improve field labeling for both accessibility and resilient locator strategies.",
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": {
            "url": target_url,
            "browser": browser,
            "headless": headless,
            "timeout_seconds": timeout_seconds,
            "wait_until": wait_until,
            "storage_state_used": storage_state_used,
            "extra_headers_used": headers_used,
        },
        "summary": summary,
        "pages": normalized_pages,
        "recommendations": _dedupe(all_recommendations),
    }


def run_dom_analysis(
    *,
    url: str,
    out_path: Path,
    browser: str = "chromium",
    timeout_seconds: float = 30.0,
    wait_until: str = "networkidle",
    headless: bool = True,
    headers: Optional[Dict[str, str]] = None,
    storage_state_path: Optional[Path] = None,
    include_external_links: bool = False,
    max_links: int = 200,
) -> Dict[str, Any]:
    """Inspect a live page with Playwright and persist `dom-analysis.json` output."""
    if wait_until not in _WAIT_UNTIL_VALUES:
        raise ValueError(
            f"Unsupported wait strategy '{wait_until}'. Use one of: {', '.join(sorted(_WAIT_UNTIL_VALUES))}"
        )
    if timeout_seconds <= 0:
        raise ValueError("Timeout must be greater than zero.")
    if max_links < 1:
        raise ValueError("max_links must be >= 1.")

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Playwright is required for DOM analysis. Install UI extras: pip install -e .[ui]"
        ) from exc

    resolved_state: Optional[Path] = None
    if storage_state_path is not None:
        resolved_state = storage_state_path.expanduser()
        if not resolved_state.is_absolute():
            resolved_state = (Path.cwd() / resolved_state).resolve()
        if not resolved_state.exists():
            raise FileNotFoundError(f"Storage state file not found: {resolved_state}")

    raw_page: Dict[str, Any]
    with sync_playwright() as pw:
        browser_type = getattr(pw, browser, None)
        if browser_type is None:
            raise ValueError("Unsupported browser. Use one of: chromium, firefox, webkit")

        browser_instance = browser_type.launch(headless=headless)
        context = None
        try:
            context_kwargs: Dict[str, Any] = {}
            if headers:
                context_kwargs["extra_http_headers"] = headers
            if resolved_state is not None:
                context_kwargs["storage_state"] = resolved_state.as_posix()

            context = browser_instance.new_context(**context_kwargs)
            page = context.new_page()
            page.goto(url, wait_until=wait_until, timeout=int(timeout_seconds * 1000))
            payload = page.evaluate(_DOM_ANALYSIS_SCRIPT)
            raw_page = payload if isinstance(payload, dict) else {}
        finally:
            if context is not None:
                context.close()
            browser_instance.close()

    analysis = build_dom_analysis(
        [raw_page],
        target_url=url,
        browser=browser,
        headless=headless,
        timeout_seconds=timeout_seconds,
        wait_until=wait_until,
        storage_state_used=resolved_state is not None,
        headers_used=bool(headers),
        include_external_links=include_external_links,
        max_links=max_links,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    return analysis
