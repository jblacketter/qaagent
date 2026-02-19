"""QA Agent CLI command assembly.

Creates the main Typer app and registers all subcommands from command modules.
"""
import typer

# Backward-compat re-exports from analyze helpers (used by mcp_server and other code)
from .analyze import (
    run_collectors,
    ensure_risks,
    ensure_recommendations,
    ensure_run_handle,
)

# Create main app
app = typer.Typer(help="QA Agent CLI: analyze, test, and expose tools via MCP")

# Import subapps
from .analyze_cmd import analyze_app
from .config_cmd import config_app
from .targets_cmd import targets_app, use_target
from .generate_cmd import generate_app
from .workspace_cmd import workspace_app
from .doc_cmd import doc_app
from .rules_cmd import rules_app
from .rag_cmd import rag_app
from .branch_cmd import branch_app

# Register subgroups
app.add_typer(analyze_app, name="analyze")
app.add_typer(config_app, name="config")
app.add_typer(targets_app, name="targets")
config_app.add_typer(targets_app, name="targets")
app.add_typer(generate_app, name="generate")
app.add_typer(workspace_app, name="workspace")
app.add_typer(doc_app, name="doc")
app.add_typer(rules_app, name="rules")
app.add_typer(rag_app, name="rag")
app.add_typer(branch_app, name="branch")

# Dual-registered commands (available both as top-level and within subgroups)
app.command("use")(use_target)

# Register top-level commands from modules
from . import run_cmd
from . import report_cmd
from . import misc_cmd
from . import record_cmd

run_cmd.register(app)
report_cmd.register(app)
misc_cmd.register(app)
record_cmd.register(app)

__all__ = [
    "app",
    "run_collectors",
    "ensure_risks",
    "ensure_recommendations",
    "ensure_run_handle",
]
