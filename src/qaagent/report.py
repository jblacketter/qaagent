from __future__ import annotations

import datetime as _dt
import platform
import json
import csv
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass
class Case:
    name: str
    classname: str = ""
    time: float = 0.0
    status: str = "passed"  # passed|failed|error|skipped
    message: str = ""


@dataclass
class Suite:
    name: str
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    time: float = 0.0
    file: Optional[Path] = None
    cases: List[Case] = field(default_factory=list)


@dataclass
class Aggregate:
    suites: List[Suite]
    total_tests: int
    total_failures: int
    total_errors: int
    total_skipped: int
    total_time: float


def _float(attr: Optional[str]) -> float:
    try:
        return float(attr or 0)
    except Exception:
        return 0.0


def _int(attr: Optional[str]) -> int:
    try:
        return int(attr or 0)
    except Exception:
        return 0


def parse_junit(path: Path) -> List[Suite]:
    if not path.exists():
        return []
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return []
    root = tree.getroot()

    suites: List[Suite] = []
    if root.tag == "testsuite":
        suites.append(_parse_testsuite(root, path))
    elif root.tag == "testsuites":
        for ts in root.findall("testsuite"):
            suites.append(_parse_testsuite(ts, path))
    else:
        # unknown root
        return []
    return suites


def _parse_testsuite(elem: ET.Element, path: Path) -> Suite:
    suite = Suite(
        name=elem.attrib.get("name", path.stem),
        tests=_int(elem.attrib.get("tests")),
        failures=_int(elem.attrib.get("failures")),
        errors=_int(elem.attrib.get("errors")),
        skipped=_int(elem.attrib.get("skipped")),
        time=_float(elem.attrib.get("time")),
        file=path,
    )
    # Some JUnit variants omit top-level counts; compute from cases
    computed_tests = 0
    computed_failures = 0
    computed_errors = 0
    computed_skipped = 0

    for tc in elem.findall("testcase"):
        name = tc.attrib.get("name", "")
        classname = tc.attrib.get("classname", "")
        time = _float(tc.attrib.get("time"))
        status = "passed"
        message = ""

        failure = tc.find("failure")
        error = tc.find("error")
        skipped = tc.find("skipped")

        if failure is not None:
            status = "failed"
            message = (failure.attrib.get("message") or failure.text or "").strip()
            computed_failures += 1
        elif error is not None:
            status = "error"
            message = (error.attrib.get("message") or error.text or "").strip()
            computed_errors += 1
        elif skipped is not None:
            status = "skipped"
            message = (skipped.attrib.get("message") or skipped.text or "").strip()
            computed_skipped += 1

        computed_tests += 1
        suite.cases.append(Case(name=name, classname=classname, time=time, status=status, message=message))

    if suite.tests == 0 and computed_tests > 0:
        suite.tests = computed_tests
        suite.failures = computed_failures
        suite.errors = computed_errors
        suite.skipped = computed_skipped
        suite.time = sum(c.time for c in suite.cases)

    return suite


def aggregate_suites(suites: Iterable[Suite]) -> Aggregate:
    suites = list(suites)
    return Aggregate(
        suites=suites,
        total_tests=sum(s.tests for s in suites),
        total_failures=sum(s.failures for s in suites),
        total_errors=sum(s.errors for s in suites),
        total_skipped=sum(s.skipped for s in suites),
        total_time=sum(s.time for s in suites),
    )


def find_default_junit_files() -> List[Path]:
    candidates = [
        Path("reports/pytest/junit.xml"),
        Path("reports/schemathesis/junit.xml"),
        Path("reports/ui/junit.xml"),
    ]
    return [p for p in candidates if p.exists()]


def collect_artifacts() -> Dict[str, List[str]]:
    roots = [Path("reports"), Path("test-results"), Path("playwright-report"), Path("artifacts")]
    files: Dict[str, List[str]] = {
        "junit": [],
        "html_reports": [],
        "videos": [],
        "traces": [],
        "screenshots": [],
        "json": [],
        "csv": [],
        "coverage_xml": [],
        "coverage_html": [],
    }
    patterns = {
        "junit": ["**/junit.xml"],
        "html_reports": ["**/report.html", "**/index.html"],
        "videos": ["**/*.webm", "**/*.mp4"],
        "traces": ["**/trace.zip", "**/*.zip"],
        "screenshots": ["**/*.png"],
        "json": ["**/report.json", "**/lighthouse*.json", "**/a11y_*.json"],
        "csv": ["**/*.csv"],
        "coverage_xml": ["**/coverage.xml"],
        "coverage_html": ["**/htmlcov/index.html", "**/coverage_html/index.html"],
    }
    for root in roots:
        if not root.exists():
            continue
        for key, globs in patterns.items():
            for pat in globs:
                for p in root.glob(pat):
                    if p.is_file():
                        files[key].append(p.as_posix())
    # De-duplicate and sort
    for k, lst in files.items():
        seen = sorted(set(lst))
        files[k] = seen
    return files


def render_markdown(
    agg: Aggregate,
    artifacts: Dict[str, List[str]],
    extras: Dict[str, object] | None = None,
    title: str = "QA Findings",
) -> str:
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = [
        f"# {title}",
        "",
        f"Generated: {now}",
        f"Environment: Python {platform.python_version()} | {platform.system()} {platform.release()}",
        "",
        "## Summary",
        "",
        f"- Total tests: {agg.total_tests}",
        f"- Failures: {agg.total_failures}",
        f"- Errors: {agg.total_errors}",
        f"- Skipped: {agg.total_skipped}",
        f"- Time: {agg.total_time:.2f}s",
        "",
    ]

    parts = header

    # Artifacts
    parts += ["## Artifacts", ""]
    for key in ["junit", "html_reports", "videos", "traces", "screenshots"]:
        lst = artifacts.get(key, [])
        if not lst:
            continue
        parts.append(f"- {key}:")
        for p in lst:
            parts.append(f"  - [{p}]({p})")
    parts.append("")

    # A11y summary
    if extras and isinstance(extras.get("a11y"), dict):
        a11y = extras["a11y"]  # type: ignore
        parts += ["", "## Accessibility (axe)"]
        parts.append(f"- URLs: {a11y.get('urls_count', 0)}")
        parts.append(f"- Violation groups: {a11y.get('violations', 0)}")
        impacts = a11y.get("impacts", {}) or {}
        if impacts:
            parts.append("- By impact:")
            for k, v in impacts.items():
                parts.append(f"  - {k}: {v}")

    # API Coverage summary
    if extras and isinstance(extras.get("api_coverage"), dict):
        cov = extras["api_coverage"]  # type: ignore
        parts += ["", "## API Coverage (Schemathesis)"]
        parts.append(f"- Spec: {cov.get('spec')}")
        parts.append(f"- Covered operations: {cov.get('covered')}/{cov.get('total')} ({cov.get('pct')}%)")
        priority_samples = cov.get("priority_uncovered_samples") or []
        if priority_samples:
            parts.append("- Top uncovered (priority):")
            for item in priority_samples[:10]:
                parts.append(f"  - {item['priority']}: {item['method']} {item['path']}")
        samples = cov.get("uncovered_samples") or []
        if samples:
            parts.append("- Uncovered samples:")
            for m, p in samples[:10]:
                parts.append(f"  - {m} {p}")

    # Code coverage summary
    if extras and isinstance(extras.get("code_coverage"), dict):
        cov = extras["code_coverage"]  # type: ignore
        parts += ["", "## Code Coverage (pytest-cov)"]
        if cov.get("line") is not None:
            parts.append(f"- Line: {cov['line']}%")
        if cov.get("branch") is not None:
            parts.append(f"- Branch: {cov['branch']}%")
        if cov.get("source"):
            parts.append(f"- Source: {cov['source']}")

    # Lighthouse summary
    if extras and isinstance(extras.get("lighthouse"), dict):
        lh = extras["lighthouse"]  # type: ignore
        parts += ["", "## Lighthouse"]
        scores = lh.get("scores", {}) or {}
        if scores:
            parts.append("- Category scores:")
            for k in ["performance", "accessibility", "best-practices", "seo", "pwa"]:
                if k in scores:
                    parts.append(f"  - {k}: {scores[k]}")
        metrics = lh.get("metrics", {}) or {}
        if metrics:
            parts.append("- Key metrics:")
            for k in ["FCP", "LCP", "TBT", "CLS"]:
                if k in metrics:
                    parts.append(f"  - {k}: {metrics[k]}")

    # Perf summary
    if extras and isinstance(extras.get("perf"), dict):
        pf = extras["perf"]  # type: ignore
        parts += ["", "## Performance (Locust)"]
        for k in ["requests", "failures", "failure_ratio", "rps", "avg_response_time", "p95_response_time"]:
            if k in pf:
                parts.append(f"- {k}: {pf[k]}")

    # Suites and notable cases
    parts.append("## Suites")
    for s in agg.suites:
        parts.append("")
        src = f" ({s.file.as_posix()})" if s.file else ""
        parts.append(f"### {s.name}{src}")
        parts.append(
            f"- tests: {s.tests} | failures: {s.failures} | errors: {s.errors} | skipped: {s.skipped} | time: {s.time:.2f}s"
        )
        # Only list failed/error cases to keep concise
        failed = [c for c in s.cases if c.status in {"failed", "error"}]
        skipped = [c for c in s.cases if c.status == "skipped"]
        if failed:
            parts.append("- Notable cases:")
            for c in failed[:50]:  # cap to avoid massive output
                cls = f"{c.classname}." if c.classname else ""
                parts.append(f"  - {c.status.upper()}: {cls}{c.name} ({c.time:.2f}s)")
                if c.message:
                    msg = c.message.strip().splitlines()[0][:300]
                    parts.append(f"    - {msg}")
        if skipped and s.failures == 0 and s.errors == 0:
            parts.append(f"- Skipped cases: {len(skipped)}")

    parts.append("")
    return "\n".join(parts)


def generate_report(
    output: Path | str = Path("reports/findings.md"),
    sources: Optional[List[Path | str]] = None,
    title: str = "QA Findings",
    fmt: str = "markdown",
) -> Dict[str, object]:
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    junit_files: List[Path] = []
    if sources:
        for s in sources:
            p = Path(s)
            if p.exists():
                junit_files.append(p)
    else:
        junit_files = find_default_junit_files()

    suites: List[Suite] = []
    for f in junit_files:
        suites.extend(parse_junit(f))

    agg = aggregate_suites(suites)
    artifacts = collect_artifacts()
    extras = analyze_extras(artifacts)
    fmt_norm = (fmt or "markdown").lower()
    if fmt_norm in {"markdown", "md"}:
        content = render_markdown(agg, artifacts, extras, title=title)
    elif fmt_norm == "html":
        content = render_html(agg, artifacts, extras, title=title)
    else:
        raise ValueError(f"Unsupported format: {fmt}. Use 'markdown' or 'html'.")

    out_path.write_text(content, encoding="utf-8")
    return {
        "output": out_path.as_posix(),
        "junit_files": [p.as_posix() for p in junit_files],
        "summary": {
            "tests": agg.total_tests,
            "failures": agg.total_failures,
            "errors": agg.total_errors,
            "skipped": agg.total_skipped,
            "time": agg.total_time,
        },
        "artifacts": artifacts,
        "extras": extras,
        "format": fmt_norm,
    }


def render_html(
    agg: Aggregate,
    artifacts: Dict[str, List[str]],
    extras: Dict[str, object] | None = None,
    title: str = "QA Findings",
) -> str:
    try:
        from jinja2 import Template  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "HTML rendering requires Jinja2. Install with: pip install -e .[report]"
        ) from e

    template = Template(
        r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
    :root { --bg: #0b1020; --panel: #121a2b; --text: #e6eefc; --muted:#98a3b8; --accent:#6ea8fe; --bad:#ff6b6b; --warn:#ffd166; --ok:#4cd97b; }
    body { background: var(--bg); color: var(--text); font: 14px/1.5 system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 0; }
    header { padding: 16px 24px; background: linear-gradient(90deg, #0f1b36, #0b1020); border-bottom: 1px solid #1b2742; }
    h1 { margin: 0; font-size: 20px; }
    .wrap { padding: 24px; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
    .card { background: var(--panel); padding: 12px; border-radius: 8px; border: 1px solid #1b2742; }
    .card h3 { margin: 0 0 6px 0; font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; }
    .card .val { font-size: 20px; font-weight: 600; }
    .val.fail { color: var(--bad); }
    .val.warn { color: var(--warn); }
    .val.ok { color: var(--ok); }
    section { margin-top: 24px; }
    h2 { font-size: 16px; margin: 0 0 12px 0; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 8px; border-bottom: 1px solid #1b2742; vertical-align: top; }
    th { text-align: left; color: var(--muted); font-weight: 600; }
    .suite { background: var(--panel); border: 1px solid #1b2742; border-radius: 8px; margin-bottom: 16px; }
    .suite h3 { margin: 0; padding: 10px 12px; border-bottom: 1px solid #1b2742; font-size: 14px; background: #0f1628; }
    .artifact a { color: var(--accent); text-decoration: none; }
    .status { padding: 2px 6px; border-radius: 999px; font-size: 12px; }
    .status.failed, .status.error { background: rgba(255,107,107,.15); color: var(--bad); }
    .status.skipped { background: rgba(255,209,102,.15); color: var(--warn); }
    .status.passed { background: rgba(76,217,123,.15); color: var(--ok); }
    .muted { color: var(--muted); }
    .meta { color: var(--muted); font-size: 12px; }
  </style>
  <meta name="color-scheme" content="dark light">
  <meta name="robots" content="noindex">
  <meta name="generator" content="qaagent">
  <meta name="created" content="{{ now }}">
  <meta name="totals" content="tests={{ agg.total_tests }},failures={{ agg.total_failures }},errors={{ agg.total_errors }},skipped={{ agg.total_skipped }},time={{ '%.2f' % agg.total_time }}">
</head>
<body>
  <header>
    <h1>{{ title }}</h1>
    <div class="meta">Generated {{ now }}</div>
  </header>
  <div class="wrap">
    <section class="cards">
      <div class="card"><h3>Total Tests</h3><div class="val">{{ agg.total_tests }}</div></div>
      <div class="card"><h3>Failures</h3><div class="val fail">{{ agg.total_failures }}</div></div>
      <div class="card"><h3>Errors</h3><div class="val fail">{{ agg.total_errors }}</div></div>
      <div class="card"><h3>Skipped</h3><div class="val warn">{{ agg.total_skipped }}</div></div>
      <div class="card"><h3>Total Time (s)</h3><div class="val">{{ '%.2f' % agg.total_time }}</div></div>
      {% if extras and extras.get('a11y') %}
      <div class="card"><h3>A11y Violations</h3><div class="val fail">{{ extras['a11y']['violations'] }}</div></div>
      {% endif %}
      {% if extras and extras.get('api_coverage') %}
      <div class="card"><h3>API Coverage</h3><div class="val">{{ extras['api_coverage']['pct'] }}%</div></div>
      {% endif %}
      {% if extras and extras.get('code_coverage') and extras['code_coverage'].get('line') is not none %}
      <div class="card"><h3>Code Cov</h3><div class="val">{{ extras['code_coverage']['line'] }}%</div></div>
      {% endif %}
      {% if extras and extras.get('lighthouse') and extras['lighthouse'].get('scores') %}
      <div class="card"><h3>LH Perf</h3><div class="val">{{ extras['lighthouse']['scores'].get('performance','-') }}</div></div>
      <div class="card"><h3>LH A11y</h3><div class="val">{{ extras['lighthouse']['scores'].get('accessibility','-') }}</div></div>
      {% endif %}
      {% if extras and extras.get('perf') and extras['perf'].get('rps') %}
      <div class="card"><h3>RPS</h3><div class="val">{{ extras['perf']['rps'] }}</div></div>
      {% endif %}
    </section>

    <section>
      <h2>Artifacts</h2>
      <table>
        <thead><tr><th>Type</th><th>Files</th></tr></thead>
        <tbody>
        {% for key, lst in artifacts.items() if lst %}
          <tr class="artifact">
            <td class="muted">{{ key }}</td>
            <td>
              {% for p in lst %}
                <div><a href="{{ p }}" target="_blank" rel="noopener">{{ p }}</a></div>
              {% endfor %}
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </section>

    <section>
      {% if extras and extras.get('a11y') %}
      <h2>Accessibility (axe)</h2>
      <div class="suite">
        <h3>Summary</h3>
        <table>
          <tbody>
            <tr><td class="muted">URLs</td><td>{{ extras['a11y']['urls_count'] }}</td></tr>
            <tr><td class="muted">Violation groups</td><td class="val fail">{{ extras['a11y']['violations'] }}</td></tr>
            {% if extras['a11y'].get('impacts') %}
            <tr><td class="muted">By impact</td><td>
              {% for k, v in extras['a11y']['impacts'].items() %}
                <div>{{ k }}: {{ v }}</div>
              {% endfor %}
            </td></tr>
            {% endif %}
          </tbody>
        </table>
      </div>
      {% endif %}

      {% if extras and extras.get('api_coverage') %}
      <h2>API Coverage (Schemathesis)</h2>
      <div class="suite">
        <table><tbody>
          <tr><td class="muted">Spec</td><td>{{ extras['api_coverage']['spec'] }}</td></tr>
          <tr><td class="muted">Covered</td><td>{{ extras['api_coverage']['covered'] }}/{{ extras['api_coverage']['total'] }} ({{ extras['api_coverage']['pct'] }}%)</td></tr>
          {% if extras['api_coverage'].get('priority_uncovered_samples') %}
          <tr><td class="muted">Top uncovered (priority)</td><td>
            {% for item in extras['api_coverage']['priority_uncovered_samples'][:10] %}
              <div>{{ item['priority'] }}: {{ item['method'] }} {{ item['path'] }}</div>
            {% endfor %}
          </td></tr>
          {% endif %}
          {% if extras['api_coverage'].get('uncovered_samples') %}
          <tr><td class="muted">Uncovered samples</td><td>
            {% for item in extras['api_coverage']['uncovered_samples'][:10] %}
              <div>{{ item[0] }} {{ item[1] }}</div>
            {% endfor %}
          </td></tr>
          {% endif %}
        </tbody></table>
      </div>
      {% endif %}

      {% if extras and extras.get('code_coverage') %}
      <h2>Code Coverage (pytest-cov)</h2>
      <div class="suite">
        <table><tbody>
          {% if extras['code_coverage'].get('line') is not none %}
          <tr><td class="muted">Line</td><td>{{ extras['code_coverage']['line'] }}%</td></tr>
          {% endif %}
          {% if extras['code_coverage'].get('branch') is not none %}
          <tr><td class="muted">Branch</td><td>{{ extras['code_coverage']['branch'] }}%</td></tr>
          {% endif %}
          {% if extras['code_coverage'].get('source') %}
          <tr><td class="muted">Source</td><td>{{ extras['code_coverage']['source'] }}</td></tr>
          {% endif %}
        </tbody></table>
      </div>
      {% endif %}

      {% if extras and extras.get('lighthouse') %}
      <h2>Lighthouse</h2>
      <div class="suite">
        <h3>Scores</h3>
        <table>
          <tbody>
            {% for k in ['performance','accessibility','best-practices','seo','pwa'] %}
              {% if extras['lighthouse'].get('scores') and k in extras['lighthouse']['scores'] %}
              <tr><td class="muted">{{ k }}</td><td>{{ extras['lighthouse']['scores'][k] }}</td></tr>
              {% endif %}
            {% endfor %}
          </tbody>
        </table>
        {% if extras['lighthouse'].get('metrics') %}
        <h3>Metrics</h3>
        <table><tbody>
          {% for k in ['FCP','LCP','TBT','CLS'] %}
            {% if k in extras['lighthouse']['metrics'] %}
            <tr><td class="muted">{{ k }}</td><td>{{ extras['lighthouse']['metrics'][k] }}</td></tr>
            {% endif %}
          {% endfor %}
        </tbody></table>
        {% endif %}
      </div>
      {% endif %}

      {% if extras and extras.get('perf') %}
      <h2>Performance (Locust)</h2>
      <div class="suite">
        <table>
          <tbody>
            {% for k in ['requests','failures','failure_ratio','rps','avg_response_time','p95_response_time'] %}
              {% if k in extras['perf'] %}
              <tr><td class="muted">{{ k }}</td><td>{{ extras['perf'][k] }}</td></tr>
              {% endif %}
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% endif %}
    </section>

    <section>
      <h2>Suites</h2>
      {% for s in agg.suites %}
      <div class="suite">
        <h3>{{ s.name }}{% if s.file %} ({{ s.file }}){% endif %}</h3>
        <table>
          <thead>
            <tr><th>Stats</th><th>Notable cases</th></tr>
          </thead>
          <tbody>
            <tr>
              <td class="muted">tests: {{ s.tests }} | failures: {{ s.failures }} | errors: {{ s.errors }} | skipped: {{ s.skipped }} | time: {{ '%.2f' % s.time }}</td>
              <td>
                {% set failed = s.cases | selectattr('status', 'in', ['failed','error']) | list %}
                {% if failed %}
                  {% for c in failed[:50] %}
                    <div><span class="status {{ c.status }}">{{ c.status }}</span>
                      {% if c.classname %}<span class="muted">{{ c.classname }}.</span>{% endif %}{{ c.name }}
                      {% if c.message %}<div class="muted">{{ c.message.split('\n')[0][:300] }}</div>{% endif %}
                    </div>
                  {% endfor %}
                {% else %}
                  <span class="muted">No failed/error cases</span>
                {% endif %}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      {% endfor %}
    </section>
  </div>
</body>
</html>
        """
    )

    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return template.render(title=title, agg=agg, artifacts=artifacts, extras=extras or {}, now=now)


def analyze_extras(artifacts: Dict[str, List[str]]) -> Dict[str, object]:
    extras: Dict[str, object] = {}
    # A11y JSON files (axe results)
    a11y_files = [p for p in artifacts.get("json", []) if Path(p).name.startswith("a11y_")]
    a11y_summary = summarize_a11y(a11y_files)
    if a11y_summary:
        extras["a11y"] = a11y_summary

    # Lighthouse JSON
    lh_files = [p for p in artifacts.get("json", []) if "lighthouse" in Path(p).name]
    lh_summary = summarize_lighthouse(lh_files)
    if lh_summary:
        extras["lighthouse"] = lh_summary

    # Locust CSV
    csv_files = artifacts.get("csv", [])
    perf_summary = summarize_perf(csv_files)
    if perf_summary:
        extras["perf"] = perf_summary

    # API coverage from spec + junit
    api_cov = summarize_api_coverage(artifacts)
    if api_cov:
        extras["api_coverage"] = api_cov

    # Code coverage (pytest-cov)
    cov = summarize_code_coverage(artifacts.get("coverage_xml", []))
    if cov:
        extras["code_coverage"] = cov
    return extras


def _safe_json_load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def summarize_a11y(files: List[str]) -> Dict[str, object] | None:
    if not files:
        return None
    total_violations = 0
    impacts: Dict[str, int] = {}
    urls: List[str] = []
    for f in files:
        data = _safe_json_load(Path(f))
        if not data:
            continue
        url = data.get("url") or data.get("testUrl") or None
        if url:
            urls.append(str(url))
        violations = data.get("violations", []) or []
        total_violations += len(violations)
        for v in violations:
            imp = (v.get("impact") or "unknown").lower()
            impacts[imp] = impacts.get(imp, 0) + 1
    return {
        "urls_count": len(sorted(set(urls))),
        "violations": total_violations,
        "impacts": dict(sorted(impacts.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def summarize_lighthouse(files: List[str]) -> Dict[str, object] | None:
    if not files:
        return None
    # Use the most recent (by mtime) if present
    paths = [Path(f) for f in files if Path(f).exists()]
    if not paths:
        return None
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    data = _safe_json_load(paths[0])
    if not data:
        return None
    cats = data.get("categories", {}) or {}
    scores = {}
    for k in ["performance", "accessibility", "best-practices", "seo", "pwa"]:
        c = cats.get(k)
        if isinstance(c, dict) and c.get("score") is not None:
            try:
                scores[k] = int(round(float(c["score"]) * 100))
            except Exception:
                pass
    audits = data.get("audits", {}) or {}
    metrics = {}
    def _fmt_ms(val: float) -> str:
        return f"{val:.0f} ms"
    def _fmt_sec(val: float) -> str:
        return f"{val:.2f} s"
    if "first-contentful-paint" in audits and audits["first-contentful-paint"].get("numericValue") is not None:
        val = float(audits["first-contentful-paint"]["numericValue"])
        metrics["FCP"] = _fmt_ms(val)
    if "largest-contentful-paint" in audits and audits["largest-contentful-paint"].get("numericValue") is not None:
        val = float(audits["largest-contentful-paint"]["numericValue"])
        metrics["LCP"] = _fmt_ms(val)
    if "total-blocking-time" in audits and audits["total-blocking-time"].get("numericValue") is not None:
        val = float(audits["total-blocking-time"]["numericValue"])
        metrics["TBT"] = _fmt_ms(val)
    if "cumulative-layout-shift" in audits and audits["cumulative-layout-shift"].get("numericValue") is not None:
        val = float(audits["cumulative-layout-shift"]["numericValue"])
        metrics["CLS"] = f"{val:.3f}"
    return {"scores": scores, "metrics": metrics, "source": paths[0].as_posix()}


def summarize_perf(csv_files: List[str]) -> Dict[str, object] | None:
    if not csv_files:
        return None
    # Find a stats CSV (prefer *_stats.csv)
    candidates = [Path(f) for f in csv_files if f.endswith("stats.csv")]
    if not candidates:
        return None
    path = sorted(candidates)[0]
    try:
        with path.open("r", newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            headers = next(reader, [])
            headers_lower = [h.strip().lower() for h in headers]
            rows = list(reader)
    except Exception:
        return None
    # Try to find an aggregated row
    agg_row = None
    name_idx = None
    for i, h in enumerate(headers_lower):
        if h in {"name", "label"}:
            name_idx = i
            break
    if name_idx is not None:
        for row in rows:
            name = row[name_idx].strip().lower()
            if name in {"aggregated", "total", "all"}:
                agg_row = row
                break
    if agg_row is None and rows:
        agg_row = rows[-1]

    # Map helper
    def get_num(field_names: List[str], default: float = 0.0) -> float:
        for fn in field_names:
            for i, h in enumerate(headers_lower):
                if h == fn:
                    try:
                        return float(agg_row[i])
                    except Exception:
                        return default
        return default

    if agg_row is None:
        return None
    requests = int(get_num(["requests", "request count"]))
    failures = int(get_num(["failures", "failure count"]))
    failure_ratio = (failures / requests) if requests else 0.0
    rps = get_num(["requests/s", "rps"]) or get_num(["total req/s", "total rps"])
    avg_rt = get_num(["average response time", "avg response time", "avg response time (ms)"])
    p95 = get_num(["95%", "p95", "95th percentile", "p(95)"])
    return {
        "requests": requests,
        "failures": failures,
        "failure_ratio": round(failure_ratio, 4),
        "rps": round(rps, 2) if rps else None,
        "avg_response_time": round(avg_rt, 2) if avg_rt else None,
        "p95_response_time": round(p95, 2) if p95 else None,
        "source": path.as_posix(),
    }


def summarize_code_coverage(files: List[str]) -> Dict[str, object] | None:
    if not files:
        return None
    # Use first coverage.xml
    path = Path(files[0])
    if not path.exists():
        return None
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return None
    root = tree.getroot()
    # Cobertura format
    line_rate = root.attrib.get("line-rate") or root.attrib.get("lineRate")
    branch_rate = root.attrib.get("branch-rate") or root.attrib.get("branchRate")
    def pct(val: Optional[str]) -> Optional[float]:
        try:
            f = float(val)
            return round(f * 100.0, 1)
        except Exception:
            return None
    return {
        "line": pct(line_rate),
        "branch": pct(branch_rate),
        "source": path.as_posix(),
    }


def summarize_api_coverage(artifacts: Dict[str, List[str]]) -> Dict[str, object] | None:
    try:
        from .analyzers.route_coverage import build_route_coverage
        from .openapi_utils import find_openapi_candidates
    except Exception:
        return None

    junit_files = [Path(p) for p in artifacts.get("junit", []) if Path(p).exists()]
    if not junit_files:
        return None

    # Pick a spec file if available
    spec_path: str | None = None
    cands = find_openapi_candidates(Path.cwd())
    if cands:
        spec_path = cands[0].as_posix()
    if not spec_path:
        return None

    try:
        summary = build_route_coverage(
            openapi_path=spec_path,
            junit_files=junit_files,
        )
    except Exception:
        return None

    if not summary:
        return None

    return {
        "spec": summary.get("spec"),
        "covered": summary.get("covered", 0),
        "total": summary.get("total", 0),
        "pct": summary.get("pct", 0.0),
        "uncovered_samples": summary.get("uncovered_samples", []),
        "priority_uncovered_samples": summary.get("priority_uncovered_samples", []),
        "uncovered": summary.get("uncovered", []),
    }
