"""Miscellaneous commands for the qaagent CLI."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich import print
from rich.table import Table

from ._helpers import console, module_available, print_fix_result, target_manager
from qaagent.config import load_active_profile, load_config_compat, write_default_config, write_env_example
from qaagent.doctor import HealthStatus, checks_to_json, run_health_checks
from qaagent.llm import generate_api_tests_from_spec, llm_available
from qaagent.openapi_utils import find_openapi_candidates, load_openapi, enumerate_operations
from qaagent.rag import default_index_path, load_index, search_index
from qaagent.tools import ensure_dir, which
from qaagent import __version__


def doctor(json_out: bool = typer.Option(False, help="Emit machine-readable JSON output")):
    """Run health checks to validate local QA Agent prerequisites."""
    checks = run_health_checks()
    exit_code = 0 if all(check.status is not HealthStatus.ERROR for check in checks) else 1

    if json_out:
        payload = {
            "checks": checks_to_json(checks),
            "platform": {
                "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "system": os.uname().sysname if hasattr(os, "uname") else os.name,
            },
        }
        typer.echo(json.dumps(payload, indent=2))
        raise typer.Exit(code=exit_code)

    table = Table(title="QA Agent Health Check", show_lines=False)
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="white", no_wrap=True)
    table.add_column("Details", style="white")
    table.add_column("Suggestion", style="magenta")

    def format_status(status: HealthStatus) -> str:
        if status is HealthStatus.OK:
            return "[green]OK[/green]"
        if status is HealthStatus.WARNING:
            return "[yellow]WARN[/yellow]"
        return "[red]ERROR[/red]"

    for check in checks:
        table.add_row(
            check.name,
            format_status(check.status),
            check.message,
            check.suggestion or "-",
        )
    console.print(table)

    errors = [c for c in checks if c.status is HealthStatus.ERROR]
    warnings = [c for c in checks if c.status is HealthStatus.WARNING and c not in errors]

    console.rule("Summary")
    if errors:
        print(f"[red][FAIL] {len(errors)} failing checks[/red]")
    elif warnings:
        print(f"[yellow]WARN {len(warnings)} warnings[/yellow]")
    else:
        print("[green][OK] All checks passed[/green]")
    raise typer.Exit(code=exit_code)


def fix_issues(
    tool: str = typer.Option("autopep8", help="Formatting tool to use (autopep8, black, isort, or all)"),
    target: Optional[str] = typer.Argument(None, help="Target name (uses active target if not specified)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be fixed without making changes"),
):
    """Auto-fix common code quality issues (formatting, imports, etc.)."""
    from qaagent.autofix import AutoFixer

    # Get target path
    if target is None:
        try:
            active_entry, _ = load_active_profile()
            target_name = active_entry.name
            target_path = active_entry.resolved_path()
        except Exception:
            console.print("[red]No active target. Specify target name or use `qaagent use <target>`[/red]")
            raise typer.Exit(code=2)
    else:
        manager = target_manager()
        entry = manager.get(target)
        if not entry:
            console.print(f"[red]Target '{target}' not found[/red]")
            raise typer.Exit(code=1)
        target_name = entry.name
        target_path = entry.resolved_path()

    console.print(f"[cyan]Fixing issues in '{target_name}' at {target_path}[/cyan]")

    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/yellow]")

    fixer = AutoFixer(target_path)

    if tool == "all":
        console.print("[cyan]Running autopep8...[/cyan]")
        result = fixer.fix_formatting("autopep8")
        print_fix_result(result)

        console.print("[cyan]Running isort...[/cyan]")
        result = fixer.fix_imports()
        print_fix_result(result)

    elif tool in ("autopep8", "black"):
        console.print(f"[cyan]Running {tool}...[/cyan]")
        result = fixer.fix_formatting(tool)
        print_fix_result(result)

    elif tool == "isort":
        console.print("[cyan]Running isort...[/cyan]")
        result = fixer.fix_imports()
        print_fix_result(result)

    else:
        console.print(f"[red]Unknown tool: {tool}[/red]")
        console.print("[yellow]Available tools: autopep8, black, isort, all[/yellow]")
        raise typer.Exit(code=1)

    console.print()
    console.print("[green][OK] Fixes applied successfully![/green]")
    console.print("[yellow]Tip:[/yellow] Re-run analysis to verify fixes:")
    console.print(f"  qaagent analyze routes {target_name}")


def web_ui(
    host: str = typer.Option("127.0.0.1", help="Host to bind to"),
    port: int = typer.Option(8080, help="Port to bind to"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser automatically"),
):
    """Start the web UI server - graphical interface for QA Agent."""
    try:
        from qaagent.web_ui import start_web_ui

        if host == "0.0.0.0":
            console.print()
            console.print("[bold yellow]WARNING: Binding to 0.0.0.0 — the server will be accessible to all devices on your local network.[/bold yellow]")
            console.print("[yellow]Make sure you have set an admin password (the app will prompt on first visit).[/yellow]")
            console.print("[yellow]For internet-facing deployments, use a reverse proxy with HTTPS.[/yellow]")
            console.print()

        console.print(f"[cyan]Starting QA Agent Web UI...[/cyan]")
        console.print(f"[green]-> Server: http://{host}:{port}[/green]")
        console.print()
        console.print("[yellow]Web UI Features:[/yellow]")
        console.print("  - Configure targets (local repos or GitHub URLs)")
        console.print("  - Discover routes from Next.js projects")
        console.print("  - Generate OpenAPI specifications")
        console.print("  - View interactive dashboards")
        console.print("  - Browse workspace files")
        console.print()
        console.print("[dim]Press Ctrl+C to stop the server[/dim]")
        console.print()

        if open_browser:
            import webbrowser
            import threading
            import time

            def open_browser_delayed():
                time.sleep(1.5)
                webbrowser.open(f"http://{host}:{port}")

            threading.Thread(target=open_browser_delayed, daemon=True).start()

        start_web_ui(host=host, port=port)

    except KeyboardInterrupt:
        console.print()
        console.print("[yellow][OK] Web UI server stopped[/yellow]")
    except ImportError as e:
        console.print(f"[red]Web UI dependencies not available: {e}[/red]")
        console.print("[yellow]Install UI extras: pip install -e .[ui][/yellow]")
        raise typer.Exit(code=2)
    except Exception as e:
        console.print(f"[red]Failed to start web UI: {e}[/red]")
        raise typer.Exit(code=1)


def version():
    """Show version info."""
    data = {"qaagent": __version__, "python": os.sys.version.split()[0]}
    print(json.dumps(data))


def init():
    """Create a starter .qaagent.toml and .env.example if missing."""
    cfg_path = write_default_config()
    env_example = write_env_example()
    print(f"[green]Wrote[/green] {cfg_path}")
    print(f"[green]Wrote[/green] {env_example}")


def api_detect(
    path: str = typer.Option(".", help="Root to search for OpenAPI files"),
    base_url: Optional[str] = typer.Option(None, help="If provided, probe common spec endpoints"),
    probe: bool = typer.Option(False, help="Probe base URL for spec endpoints"),
):
    """Find OpenAPI files and optionally probe a base URL for a spec endpoint."""
    from qaagent.openapi_utils import probe_spec_from_base_url

    root = Path(path)
    files = find_openapi_candidates(root)
    table = Table(title="OpenAPI Detection")
    table.add_column("Source", style="cyan")
    table.add_column("Value")
    if files:
        for f in files:
            table.add_row("file", f.as_posix())
    else:
        table.add_row("file", "(none found)")

    found_url = None
    if base_url and probe:
        found_url = probe_spec_from_base_url(base_url)
        table.add_row("probe", found_url or "(not found)")

    console.print(table)

    target = (found_url or (files[0].as_posix() if files else None))
    if target:
        try:
            spec = load_openapi(target)
            ops = enumerate_operations(spec)
            print(f"[bold]Operations detected:[/bold] {len(ops)} from {target}")
        except Exception as e:  # noqa: BLE001
            print(f"[yellow]Could not parse spec from {target}: {e}[/yellow]")


def gen_tests(
    kind: str = typer.Option("api", help="Type of tests to generate: api|ui (api supported)"),
    openapi: Optional[str] = typer.Option(None, help="Path/URL to OpenAPI; auto-detect if omitted"),
    base_url: Optional[str] = typer.Option(None, help="Base URL for generated tests"),
    outdir: str = typer.Option("tests/api", help="Directory to write tests"),
    max_tests: int = typer.Option(12, help="Max tests to generate"),
    use_rag: bool = typer.Option(False, "--use-rag", help="Enable retrieval context from local RAG index"),
    rag_top_k: int = typer.Option(5, "--rag-top-k", min=1, max=20, help="Number of retrieval snippets to include"),
    rag_index: Optional[str] = typer.Option(None, "--rag-index", help="Path to RAG index.json"),
    dry_run: bool = typer.Option(False, help="Print output instead of writing files"),
):
    """Generate test stubs. For now, supports API-only from OpenAPI. Falls back if no LLM."""
    if kind != "api":
        print("[red]Only kind=api is supported currently[/red]")
        raise typer.Exit(code=2)
    cfg = load_config_compat()
    if not openapi and cfg and cfg.api.openapi:
        openapi = cfg.api.openapi
    if not base_url and cfg and cfg.api.base_url:
        base_url = cfg.api.base_url
    if not openapi:
        cands = find_openapi_candidates(Path.cwd())
        if cands:
            openapi = cands[0].as_posix()
    if not openapi:
        print("[red]OpenAPI not provided or detected[/red]")
        raise typer.Exit(code=2)
    if not base_url:
        base_url = os.environ.get("BASE_URL", "http://localhost:8000")

    spec = load_openapi(openapi)
    retrieval_context: Optional[List[str]] = None
    if use_rag:
        rag_root = Path.cwd()
        try:
            entry, _ = load_active_profile()
            rag_root = entry.resolved_path()
        except Exception:
            pass

        index_path = Path(rag_index).expanduser().resolve() if rag_index else default_index_path(rag_root)
        if not index_path.exists():
            print(f"[red]RAG index not found:[/red] {index_path}")
            print("[yellow]Run `qaagent rag index` first or provide --rag-index[/yellow]")
            raise typer.Exit(code=2)

        index_data = load_index(index_path)
        ops = enumerate_operations(spec)[:max_tests]
        op_lines = [f"{op.method} {op.path}" for op in ops]
        query = "API test generation context:\n" + "\n".join(op_lines)
        results = search_index(index_data, query, top_k=rag_top_k)
        retrieval_context = [
            f"{item.path}:{item.start_line}-{item.end_line}\n{item.text}"
            for item in results
        ]
        print(f"[cyan]Using {len(retrieval_context)} RAG snippet(s) from {index_path}[/cyan]")

    code = generate_api_tests_from_spec(
        spec,
        base_url=base_url,
        max_tests=max_tests,
        retrieval_context=retrieval_context,
    )
    if dry_run:
        console.rule("Generated tests (preview)")
        print(code)
        return
    dest = Path(outdir)
    ensure_dir(dest)
    path = dest / "test_generated_api.py"
    path.write_text(code, encoding="utf-8")
    print(f"[green]Wrote[/green] {path} (LLM={'yes' if llm_available() else 'no'})")


def api_server(
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
    runs_dir: Optional[Path] = typer.Option(None, "--runs-dir", help="Runs directory for the API"),
):
    """Start the QA Agent API server."""
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - import guard
        typer.echo("[red]uvicorn not installed. Install with `pip install uvicorn`.")
        raise typer.Exit(code=1) from exc

    if runs_dir:
        os.environ["QAAGENT_RUNS_DIR"] = str(runs_dir)

    typer.echo(f"Starting API server at http://{host}:{port}")
    uvicorn.run("qaagent.api.app:app", host=host, port=port)


def mcp_stdio():
    """Run the MCP server over stdio."""
    try:
        from qaagent.mcp_server import run_stdio
    except Exception as e:  # noqa: BLE001
        print("[red]MCP server is unavailable. Ensure 'mcp' extra is installed.[/red]")
        print(str(e))
        raise typer.Exit(code=2)

    run_stdio()


def register(app: typer.Typer) -> None:
    """Register all misc commands on the main app."""
    app.command("doctor")(doctor)
    app.command("fix")(fix_issues)
    app.command("web-ui")(web_ui)
    app.command()(version)
    app.command()(init)
    app.command("api-detect")(api_detect)
    app.command("gen-tests")(gen_tests)
    app.command("api")(api_server)
    app.command("mcp-stdio")(mcp_stdio)
