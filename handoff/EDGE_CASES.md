# Collector Edge Cases & Test Notes

## flake8
- Missing tool: capture `FileNotFoundError`, mark `executed=false`, add diagnostic.
- Non-zero exit with findings still emits JSON; parse anyway.
- Large output: stream to temp file, avoid loading entire stdout in memory.

## pylint
- Some messages lack column numbers → default to `null`.
- When pylint fails to load modules (import-error), treat as warning and capture in diagnostics.

## bandit
- Ensure `--ini` not required; run recursive by default.
- Handle both B101 (assert) and B105 (hard-coded password) findings; map severity string to numeric weight later.

## pip-audit
- Multiple requirements files: run once per file, aggregate.
- Unsupported manifests (poetry.lock) → log diagnostic advising manual audit.
- No internet (offline) → handle exit code 2 with message `"No matching vulnerabilities"` vs actual failure.

## coverage ingestion
- Respect both `coverage.xml` and `lcov.info`; prefer XML when both present.
- Missing files: set `found=false`, degrade confidence.
- XML without `<sources>`: fallback to relative paths.

## git churn
- Non-git directory: skip gracefully.
- Shallow clone without history < window: still count available commits.
- Binary files: ignore from stats.
- Merge base missing (no origin/main): fallback to `git rev-parse HEAD^` and log diagnostic.

## General
- All collectors should emit structured log events `collector.start`/`collector.finish`.
- Evidence IDs must remain deterministic within a run (ordering by file path + message hash).
