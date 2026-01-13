"""Utility to build synthetic git history for collector tests."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd or ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def ensure_git_repo() -> None:
    git_dir = ROOT / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)
    run(["git", "init", "."])
    run(["git", "config", "user.name", "Synthetic QA Agent"])
    run(["git", "config", "user.email", "qaagent@example.com"])


def initial_commit(days_ago: int = 120) -> None:
    run(["git", "add", "-A"])
    ts = datetime.utcnow() - timedelta(days=days_ago)
    env = {
        "GIT_AUTHOR_DATE": ts.isoformat(),
        "GIT_COMMITTER_DATE": ts.isoformat(),
    }
    subprocess.run(
        ["git", "commit", "-m", "Initial synthetic repo"],
        cwd=ROOT,
        check=True,
        env={**env, **{k: v for k, v in os.environ.items() if k not in env}},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def make_churn_commits(count: int = 14, window_days: int = 90) -> None:
    session_path = ROOT / "src" / "auth" / "session.py"
    base_time = datetime.utcnow()
    for idx in range(count):
        commit_time = base_time - timedelta(days=window_days - (idx * window_days // count))
        with session_path.open("a", encoding="utf-8") as fp:
            fp.write(f"\n# churn marker {idx}\n")
        run(["git", "add", str(session_path.relative_to(ROOT))])
        env = {
            "GIT_AUTHOR_DATE": commit_time.isoformat(),
            "GIT_COMMITTER_DATE": commit_time.isoformat(),
        }
        subprocess.run(
            ["git", "commit", "-m", f"churn commit {idx}"],
            cwd=ROOT,
            check=True,
            env={**env, **{k: v for k, v in os.environ.items() if k not in env}},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Setup synthetic git history")
    parser.add_argument("--churn-commits", type=int, default=14)
    parser.add_argument("--window-days", type=int, default=90)
    args = parser.parse_args()

    ensure_git_repo()
    initial_commit()
    make_churn_commits(count=args.churn_commits, window_days=args.window_days)


if __name__ == "__main__":
    main()
