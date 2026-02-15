"""RAG CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from ._helpers import console
from qaagent.config import load_active_profile
from qaagent.rag import default_index_path, index_repository, load_index, search_index


rag_app = typer.Typer(help="Local RAG indexing and retrieval commands")


def _default_root(path_arg: str) -> Path:
    try:
        entry, _ = load_active_profile()
        return entry.resolved_path()
    except Exception:
        return Path(path_arg).expanduser().resolve()


@rag_app.command("index")
def rag_index(
    path: str = typer.Option(".", "--path", help="Project root to index"),
    out: Optional[str] = typer.Option(None, "--out", help="Output index path"),
    chunk_chars: int = typer.Option(1400, "--chunk-chars", min=300, help="Chunk size in characters"),
    max_file_bytes: int = typer.Option(500000, "--max-file-bytes", min=1024, help="Skip files larger than this"),
    json_out: bool = typer.Option(False, "--json-out", help="Emit JSON output"),
):
    """Build a local retrieval index."""
    root = _default_root(path)
    out_path = Path(out).expanduser().resolve() if out else None
    summary = index_repository(
        root,
        output_path=out_path,
        chunk_chars=chunk_chars,
        max_file_bytes=max_file_bytes,
    )

    if json_out:
        typer.echo(json.dumps(summary))
        return

    table = Table(title="RAG Index")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Root", str(summary["root"]))
    table.add_row("Documents", str(summary["documents"]))
    table.add_row("Chunks", str(summary["chunks"]))
    table.add_row("Index", str(summary["index_path"]))
    console.print(table)


@rag_app.command("query")
def rag_query(
    query: str = typer.Argument(..., help="Free-text query"),
    path: str = typer.Option(".", "--path", help="Project root when --index is omitted"),
    index: Optional[str] = typer.Option(None, "--index", help="Path to index.json"),
    top_k: int = typer.Option(5, "--top-k", min=1, max=50, help="Max results"),
    json_out: bool = typer.Option(False, "--json-out", help="Emit JSON output"),
):
    """Query the local retrieval index."""
    if index:
        index_path = Path(index).expanduser().resolve()
    else:
        root = _default_root(path)
        index_path = default_index_path(root)

    if not index_path.exists():
        console.print(f"[red]RAG index not found:[/red] {index_path}")
        console.print("[yellow]Run `qaagent rag index` first.[/yellow]")
        raise typer.Exit(code=2)

    data = load_index(index_path)
    results = search_index(data, query, top_k=top_k)

    payload = {
        "query": query,
        "index": index_path.as_posix(),
        "count": len(results),
        "results": [item.to_dict() for item in results],
    }
    if json_out:
        typer.echo(json.dumps(payload))
        return

    table = Table(title=f"RAG Query Results ({len(results)})")
    table.add_column("Score", style="magenta")
    table.add_column("Path", style="cyan")
    table.add_column("Lines", style="green")
    table.add_column("Preview", style="white")
    for item in results:
        preview = item.text.replace("\n", " ")
        if len(preview) > 100:
            preview = preview[:97] + "..."
        table.add_row(
            f"{item.score:.2f}",
            item.path,
            f"{item.start_line}-{item.end_line}",
            preview,
        )
    console.print(table)
