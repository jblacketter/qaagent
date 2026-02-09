"""QA Agent CLI entry point.

This is a thin wrapper that imports the assembled Typer app from commands/
and exposes the main() function referenced by pyproject.toml entry points.
"""
from qaagent.commands import app


def main():
    app()


if __name__ == "__main__":
    main()
