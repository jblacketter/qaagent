from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

try:
    from mcp.server.fastmcp import FastMCP
except Exception as e:  # noqa: BLE001
    raise RuntimeError(
        "The 'mcp' package is required for the MCP server. Install with: pip install -e .[mcp]"
    ) from e

from .tools import ensure_dir, run_command
from .report import generate_report
from .config import load_config
from .openapi_utils import find_openapi_candidates, load_openapi, enumerate_operations
from .a11y import run_axe
from .llm import llm_available, generate_api_tests_from_spec, summarize_findings_text


mcp = FastMCP("qaagent")


class SchemathesisArgs(BaseModel):
    openapi: str | None = None
    base_url: str | None = None
    outdir: str = "reports/schemathesis"
    auth_header: str | None = None
    auth_token_env: str | None = None
    auth_prefix: str = "Bearer "
    timeout: float | None = None
    tag: list[str] | None = None
    operation_id: list[str] | None = None
    endpoint_pattern: str | None = None


class PytestArgs(BaseModel):
    path: str = "tests"
    junit: bool = True
    outdir: str = "reports/pytest"


@mcp.tool()
def schemathesis_run(args: SchemathesisArgs):
    out = Path(args.outdir)
    ensure_dir(out)
    # Load config defaults if missing
    cfg = load_config()
    openapi = args.openapi or (cfg.api.openapi if cfg and cfg.api.openapi else None)
    base_url = args.base_url or (cfg.api.base_url if cfg and cfg.api.base_url else None)

    if not openapi:
        cands = find_openapi_candidates()
        if cands:
            openapi = cands[0].as_posix()

    if not openapi or not base_url:
        return {"error": "openapi and base_url are required (via args, config, or detection)"}

    cmd = [
        "schemathesis",
        "run",
        openapi,
        "--base-url",
        base_url,
        "--checks=all",
        "--hypothesis-deadline=500",
        "--junit-xml",
        str(out / "junit.xml"),
    ]
    if args.timeout is not None:
        cmd += ["--request-timeout", str(args.timeout)]

    # Auth header
    token = None
    token_env = args.auth_token_env or (cfg.api.auth.token_env if cfg else None)
    if token_env:
        import os

        token = os.environ.get(token_env)
    if token:
        header_name = args.auth_header or (cfg.api.auth.header_name if cfg else "Authorization")
        prefix = args.auth_prefix or (cfg.api.auth.prefix if cfg else "Bearer ")
        header = f"{header_name}: {prefix}{token}" if prefix else f"{header_name}: {token}"
        cmd += ["--header", header]

    # Filters
    if args.tag:
        for t in args.tag:
            cmd += ["--tag", t]
    if args.operation_id:
        for oid in args.operation_id:
            cmd += ["--operation-id", oid]
    if args.endpoint_pattern:
        cmd += ["--endpoint", args.endpoint_pattern]
    res = run_command(cmd)
    meta = {"returncode": res.returncode, "stdout": res.stdout, "stderr": res.stderr}
    # Compute basic coverage
    try:
        from .report import parse_junit
        from .openapi_utils import covered_operations_from_junit_case_names

        suites = parse_junit(out / "junit.xml")
        case_names = [c.name for s in suites for c in s.cases]
        covered = set(covered_operations_from_junit_case_names(case_names))
        spec = load_openapi(openapi)
        ops = enumerate_operations(spec)
        total_ops = len(ops)
        covered_count = sum(1 for op in ops if (op.method, op.path) in covered)
        meta["coverage"] = {
            "covered": covered_count,
            "total": total_ops,
            "pct": (covered_count * 100.0 / total_ops) if total_ops else 0.0,
        }
    except Exception:
        pass
    return meta


@mcp.tool()
def pytest_run(args: PytestArgs):
    out = Path(args.outdir)
    ensure_dir(out)
    cmd = ["pytest", args.path, "-q"]
    if args.junit:
        cmd += ["--junitxml", str(out / "junit.xml")]
    res = run_command(cmd)
    return {"returncode": res.returncode, "stdout": res.stdout, "stderr": res.stderr}


class ReportArgs(BaseModel):
    out: str = "reports/findings.md"
    sources: list[str] | None = None
    title: str = "QA Findings"
    fmt: str = "markdown"


@mcp.tool()
def generate_report_tool(args: ReportArgs):
    """Generate a consolidated QA Findings report and return summary metadata."""
    meta = generate_report(output=args.out, sources=args.sources, title=args.title, fmt=args.fmt)
    return meta


class DetectOpenAPIArgs(BaseModel):
    path: str = "."
    base_url: str | None = None
    probe: bool = False


@mcp.tool()
def detect_openapi(args: DetectOpenAPIArgs):
    """Find OpenAPI files and optionally probe a base URL. Returns candidates and counts."""
    cands = [p.as_posix() for p in find_openapi_candidates(args.path)]
    result = {"files": cands, "probe_url": None, "operations": None}
    target = None
    if cands:
        target = cands[0]
    if args.base_url and args.probe:
        from .openapi_utils import probe_spec_from_base_url

        url = probe_spec_from_base_url(args.base_url)
        if url:
            result["probe_url"] = url
            target = url
    if target:
        try:
            spec = load_openapi(target)
            ops = enumerate_operations(spec)
            result["operations"] = len(ops)
        except Exception:
            pass
    return result


class A11yArgs(BaseModel):
    url: list[str]
    outdir: str = "reports/a11y"
    tag: list[str] | None = None
    browser: str = "chromium"
    axe_url: str | None = "https://cdn.jsdelivr.net/npm/axe-core@4.7.0/axe.min.js"


@mcp.tool()
def a11y_run(args: A11yArgs):
    meta = run_axe(urls=args.url, outdir=Path(args.outdir), tags=args.tag, axe_source_url=args.axe_url, browser=args.browser)
    return meta


class LighthouseArgs(BaseModel):
    url: str
    outdir: str = "reports/lighthouse"
    categories: str = "performance,accessibility,best-practices,seo"
    device: str = "desktop"
    disable_storage_reset: bool = False


@mcp.tool()
def lighthouse_audit(args: LighthouseArgs):
    # Reuse CLI logic by constructing the command
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    html = out / "report.html"
    if shutil.which("lighthouse"):
        base_cmd = ["lighthouse"]
    elif shutil.which("npx"):
        base_cmd = ["npx", "-y", "lighthouse"]
    else:
        return {"error": "lighthouse or npx not found"}
    cmd = base_cmd + [
        args.url,
        "--quiet",
        f"--only-categories={args.categories}",
        f"--preset={'desktop' if args.device=='desktop' else 'mobile'}",
        "--output=json",
        "--output=html",
        f"--output-path={html}",
        f"--save-assets",
    ]
    if args.disable_storage_reset:
        cmd.append("--disable-storage-reset")
    res = run_command(cmd)
    return {"returncode": res.returncode, "stdout": res.stdout, "stderr": res.stderr, "html": html.as_posix()}


class GenTestsArgs(BaseModel):
    kind: str = "api"
    openapi: str | None = None
    base_url: str | None = None
    max_tests: int = 12


@mcp.tool()
def generate_tests(args: GenTestsArgs):
    if args.kind != "api":
        return {"error": "Only kind=api is supported"}
    target = args.openapi
    if not target:
        cands = find_openapi_candidates()
        if cands:
            target = cands[0].as_posix()
    if not target:
        return {"error": "OpenAPI not provided or detected"}
    spec = load_openapi(target)
    code = generate_api_tests_from_spec(spec, base_url=args.base_url or "http://localhost:8000", max_tests=args.max_tests)
    return {"kind": "api", "code": code, "llm": llm_available()}


class SummarizeArgs(BaseModel):
    findings: str = "reports/findings.md"
    fmt: str = "markdown"


@mcp.tool()
def summarize_findings(args: SummarizeArgs):
    meta = generate_report(output=args.findings, fmt=args.fmt)
    text = summarize_findings_text(meta)
    return {"summary": text, "llm": llm_available()}


def run_stdio():
    asyncio.run(mcp.run_stdio())


def main():
    run_stdio()
