"""Report and dashboard commands for the qaagent CLI."""
from __future__ import annotations

import json
import os
import webbrowser
import zipfile
from pathlib import Path
from typing import List, Optional

import typer
from rich import print

from ._helpers import console
from qaagent.config import load_active_profile, load_config_compat
from qaagent.evidence.models import ToolStatus
from qaagent.openapi_utils import find_openapi_candidates
from qaagent.notifications import (
    build_ci_summary,
    render_ci_summary,
    send_email_smtp,
    send_slack_webhook,
)
from qaagent.report import generate_report
from qaagent.llm import summarize_findings_text, llm_available
from qaagent.tools import ensure_dir


def report(
    out: str = typer.Option("reports/findings.md", help="Output file path (.md or .html)"),
    sources: Optional[List[str]] = typer.Option(None, help="Optional JUnit XML files to include; defaults searched"),
    title: str = typer.Option("QA Findings", help="Report title"),
    fmt: str = typer.Option("markdown", help="Report format: markdown|html"),
    json_out: bool = typer.Option(False, help="Print JSON result metadata"),
):
    """Generate a consolidated QA Findings report (Markdown)."""
    # Convenience: if html requested but extension is .md, flip it
    if fmt.lower() == "html" and out.lower().endswith(".md"):
        out = out[:-3] + ".html"
    result = generate_report(output=out, sources=sources, title=title, fmt=fmt)
    if json_out:
        print(json.dumps(result))
    else:
        print(f"[green]Report written:[/green] {result['output']}")
        print("Summary:")
        print(result["summary"])


def dashboard(
    out: Optional[str] = typer.Option(None, help="Output path for dashboard HTML"),
    target: Optional[str] = typer.Argument(None, help="Target name (uses active target if not specified)"),
):
    """Generate interactive visual dashboard with risk analysis and test recommendations."""
    from qaagent.dashboard import generate_dashboard_from_workspace

    # Get target name
    if target is None:
        try:
            active_entry, _ = load_active_profile()
            target = active_entry.name
        except Exception:
            console.print("[red]No active target. Specify target name or use `qaagent use <target>`[/red]")
            raise typer.Exit(code=2)

    try:
        # Determine output path
        output_path = None
        if out:
            output_path = Path(out)
            if not output_path.is_absolute():
                output_path = Path.cwd() / output_path

        console.print(f"[cyan]Generating dashboard for '{target}'...[/cyan]")
        console.print("[cyan]  \u2192 Discovering routes...[/cyan]")
        console.print("[cyan]  \u2192 Assessing risks...[/cyan]")
        console.print("[cyan]  \u2192 Building recommendations...[/cyan]")

        dashboard_path = generate_dashboard_from_workspace(target, output_path)

        console.print(f"[green]\u2713 Dashboard generated \u2192 {dashboard_path}[/green]")
        console.print()
        console.print("[yellow]Open in browser:[/yellow]")
        console.print(f"  open {dashboard_path}")
        console.print()
        console.print("[yellow]Or use:[/yellow]")
        console.print(f"  qaagent open-report --path {dashboard_path}")

    except Exception as e:
        console.print(f"[red]Error generating dashboard: {e}[/red]")
        raise typer.Exit(code=1)


def summarize(
    findings: str = typer.Option("reports/findings.md", help="Findings file to base the summary on (regenerated if exists)"),
    fmt: str = typer.Option("markdown", help="Report format for re-generation (md or html)"),
    out: str = typer.Option("reports/summary.md", help="Executive summary output"),
):
    """Produce an executive summary using artifacts and (optionally) the local LLM."""
    meta = generate_report(output=findings, fmt=fmt)
    summary = summarize_findings_text(meta)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(summary, encoding="utf-8")
    print(f"[green]Summary written:[/green] {out} (LLM={'yes' if llm_available() else 'no'})")


def notify(
    findings: str = typer.Option("reports/findings.md", help="Findings output path (regenerated)"),
    fmt: str = typer.Option("markdown", help="Findings format: markdown|html"),
    output_format: str = typer.Option("text", help="Summary format: text|json"),
    slack_webhook: Optional[str] = typer.Option(
        None,
        "--slack-webhook",
        envvar="QAAGENT_SLACK_WEBHOOK",
        help="Slack incoming webhook URL",
    ),
    email_to: Optional[List[str]] = typer.Option(None, "--email-to", help="Email recipient (repeatable)"),
    smtp_host: Optional[str] = typer.Option(None, "--smtp-host", envvar="QAAGENT_SMTP_HOST", help="SMTP host"),
    smtp_port: int = typer.Option(587, "--smtp-port", envvar="QAAGENT_SMTP_PORT", help="SMTP port"),
    smtp_user: Optional[str] = typer.Option(None, "--smtp-user", envvar="QAAGENT_SMTP_USER", help="SMTP username"),
    smtp_password_env: str = typer.Option(
        "QAAGENT_SMTP_PASSWORD",
        "--smtp-password-env",
        help="Environment variable containing SMTP password",
    ),
    email_from: Optional[str] = typer.Option(None, "--email-from", envvar="QAAGENT_EMAIL_FROM", help="Sender email"),
    subject: str = typer.Option("QAAgent CI Summary", "--subject", help="Notification subject/title"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print summary without sending notifications"),
):
    """Generate a CI summary and optionally send Slack/email notifications."""
    meta = generate_report(output=findings, fmt=fmt)
    summary = build_ci_summary(meta)
    text = render_ci_summary(summary)

    if output_format.lower() == "json":
        print(json.dumps(summary, indent=2))
    else:
        print(text)

    if dry_run:
        print("[yellow]Dry run enabled; no notifications sent.[/yellow]")
        return

    sent = 0
    if slack_webhook:
        send_slack_webhook(slack_webhook, text, title=subject)
        print("[green]Sent Slack notification[/green]")
        sent += 1

    recipients = list(email_to or [])
    if recipients:
        smtp_password = os.environ.get(smtp_password_env)
        if not smtp_host or not smtp_user or not smtp_password or not email_from:
            print("[red]Email notification requires --smtp-host, --smtp-user, --email-from, and SMTP password env.[/red]")
            raise typer.Exit(code=2)
        send_email_smtp(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            username=smtp_user,
            password=smtp_password,
            sender=email_from,
            recipients=recipients,
            subject=subject,
            body=text,
        )
        print(f"[green]Sent email notification to {len(recipients)} recipient(s)[/green]")
        sent += 1

    if sent == 0:
        print("[yellow]No notification targets configured. Set --slack-webhook and/or --email-to.[/yellow]")


def open_report(path: str = typer.Option("reports/findings.html", help="Path to report HTML")):
    """Open the HTML report in the default browser."""
    p = Path(path)
    if not p.exists():
        print(f"[red]Report not found:[/red] {p}")
        raise typer.Exit(code=2)
    webbrowser.open(p.resolve().as_uri())
    print(f"Opened {p}")


def export_reports(
    reports_dir: str = typer.Option("reports", help="Reports directory"),
    out_zip: str = typer.Option("reports/export.zip", help="Output zip path"),
):
    """Zip all files under the reports directory for sharing."""
    r = Path(reports_dir)
    if not r.exists():
        print(f"[red]Directory not found:[/red] {r}")
        raise typer.Exit(code=2)
    out = Path(out_zip)
    ensure_dir(out.parent)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in r.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(r))
    print(f"[green]Exported[/green] {out}")


def _collect_tool_artifacts(
    handle,
    tool_name: str,
    report_dir: Path,
) -> None:
    """Copy tool report artifacts into the shared evidence run."""
    import shutil

    if handle is None or not report_dir.exists():
        return
    dest = handle.artifacts_dir / tool_name
    dest.mkdir(parents=True, exist_ok=True)
    for p in report_dir.iterdir():
        if p.is_file():
            shutil.copy2(p, dest / p.name)
        elif p.is_dir():
            shutil.copytree(p, dest / p.name, dirs_exist_ok=True)


def plan_run(
    quick: bool = typer.Option(True, help="Quick run: a11y+LH+perf short; skip UI unless tests exist"),
    html_report: bool = typer.Option(True, help="Write HTML findings report"),
    generate: bool = typer.Option(False, "--generate", help="Generate test suites before running (discover -> assess -> generate -> run -> report)"),
):
    """Simple end-to-end plan: detect -> run tools -> generate report.

    With --generate: discover -> assess -> generate -> run -> report.
    """
    from .run_cmd import schemathesis_run, ui_run, a11y_run, lighthouse_audit, perf_run

    cfg = load_config_compat()
    openapi = (cfg.api.openapi if cfg and cfg.api.openapi else None) or (
        find_openapi_candidates(Path.cwd())[0].as_posix() if find_openapi_candidates(Path.cwd()) else None
    )
    base_url = (cfg.api.base_url if cfg and cfg.api.base_url else None) or os.environ.get("BASE_URL")

    # Create shared evidence run when --generate is set
    run_handle = None
    profile = None
    if generate:
        try:
            _, profile = load_active_profile()
        except Exception:
            console.print("[red]No active profile. Use `qaagent use <target>` first.[/red]")
            raise typer.Exit(code=2)

        try:
            from qaagent.evidence.run_manager import RunManager
            manager = RunManager()
            run_handle = manager.create_run(
                target_name=profile.project.name,
                target_path=Path.cwd(),
            )
        except Exception:
            pass  # Evidence is best-effort

    # Generate + orchestrated run (if --generate flag is set)
    if generate:
        print("[cyan]Generating test suites...[/cyan]")
        try:
            from .generate_cmd import generate_all
            generate_all(out=None, routes_file=None, risks_file=None, base_url=base_url)
        except (SystemExit, Exception) as exc:
            print(f"[yellow]Generation step encountered an issue: {exc}[/yellow]")

        # Run generated suites via orchestrator (sharing the run handle)
        print("[cyan]Running generated test suites...[/cyan]")
        try:
            from qaagent.runners.orchestrator import RunOrchestrator
            orchestrator = RunOrchestrator(
                config=profile, output_dir=Path("reports"), run_handle=run_handle,
            )
            orch_result = orchestrator.run_all()
            for suite_name, suite_result in orch_result.suites.items():
                status = "[green]PASS[/green]" if suite_result.success else "[red]FAIL[/red]"
                print(
                    f"  {suite_name}: {status} "
                    f"({suite_result.passed} passed, {suite_result.failed} failed, "
                    f"{suite_result.errors} errors) [{suite_result.duration:.1f}s]"
                )
            # Show diagnostic summary if there are failures
            if orch_result.diagnostic_summary and orch_result.diagnostic_summary.summary_text:
                print()
                print("[yellow]Failure Analysis:[/yellow]")
                print(f"  {orch_result.diagnostic_summary.summary_text}")
        except (SystemExit, Exception) as exc:
            print(f"[yellow]Orchestrated run encountered an issue: {exc}[/yellow]")

    # API
    if openapi and base_url:
        print("[cyan]Running Schemathesis...[/cyan]")
        try:
            schemathesis_run(openapi=openapi, base_url=base_url)
        except SystemExit:
            pass
        _collect_tool_artifacts(run_handle, "schemathesis", Path("reports/schemathesis"))
        if run_handle:
            run_handle.register_tool("schemathesis", ToolStatus(executed=True))
    else:
        print("[yellow]Skipping Schemathesis (spec or base_url missing)[/yellow]")

    # UI
    ui_dir = Path("tests/ui")
    if ui_dir.exists() and any(ui_dir.glob("test_*.py")):
        print("[cyan]Running UI tests...[/cyan]")
        try:
            ui_run(path=str(ui_dir), base_url=base_url)
        except SystemExit:
            pass
        _collect_tool_artifacts(run_handle, "ui", Path("reports/ui"))
        if run_handle:
            run_handle.register_tool("ui", ToolStatus(executed=True))
    else:
        print("[yellow]Skipping UI (no tests found)[/yellow]")

    # A11y + Lighthouse
    if base_url:
        try:
            a11y_run(url=[base_url])
        except SystemExit:
            pass
        _collect_tool_artifacts(run_handle, "a11y", Path("reports/a11y"))
        if run_handle:
            run_handle.register_tool("a11y", ToolStatus(executed=True))
        try:
            lighthouse_audit(url=base_url)
        except SystemExit:
            pass
        _collect_tool_artifacts(run_handle, "lighthouse", Path("reports/lighthouse"))
        if run_handle:
            run_handle.register_tool("lighthouse", ToolStatus(executed=True))
    else:
        print("[yellow]Skipping a11y / Lighthouse (no BASE_URL)[/yellow]")

    # Perf (short)
    if base_url:
        try:
            perf_run(users=5, spawn_rate=2.0, run_time="15s")
        except SystemExit:
            pass
        _collect_tool_artifacts(run_handle, "perf", Path("reports/perf"))
        if run_handle:
            run_handle.register_tool("perf", ToolStatus(executed=True))

    # Finalize shared evidence run
    if run_handle:
        run_handle.finalize()
        print(f"  Evidence: {run_handle.run_dir}")

    # Report
    fmt = "html" if html_report else "markdown"
    out = "reports/findings.html" if html_report else "reports/findings.md"
    result = generate_report(output=out, fmt=fmt)
    print(f"[green]Findings written:[/green] {result['output']}")


def register(app: typer.Typer) -> None:
    """Register all report commands on the main app."""
    app.command("report")(report)
    app.command("dashboard")(dashboard)
    app.command("summarize")(summarize)
    app.command("notify")(notify)
    app.command("open-report")(open_report)
    app.command("export-reports")(export_reports)
    app.command("plan-run")(plan_run)
