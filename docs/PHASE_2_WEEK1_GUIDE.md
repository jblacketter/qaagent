# Phase 2 Week 1 Guide

This guide explains the new intelligent-analysis capabilities introduced during Phase 2 Week 1.

## Commands

```bash
# Discover routes from OpenAPI / source code (OpenAPI MVP)
qaagent analyze routes --openapi examples/petstore-api/openapi.yaml --out routes.json

# Assess security / performance / reliability risks
qaagent analyze risks --routes routes.json --markdown risks.md

# Generate an actionable test strategy
qaagent analyze strategy --routes routes.json --risks risks.json --out strategy.yaml --markdown strategy.md
```

## Generated Artifacts

| File | Description |
|------|-------------|
| `routes.json` | Normalized route metadata (method, path, auth, tags, params) |
| `risks.json` / `risks.md` | Rule-based risk assessment including CWE / OWASP mappings |
| `strategy.yaml` / `strategy.md` | Test pyramid guidance, priorities, sample scenarios |

## Automation

A helper script is included for quick smoke testing:

```bash
scripts/validate_week1.sh
```

The script will:
1. Discover routes from the petstore example
2. Assess risks
3. Generate a strategy summary

Artifacts will be written to `.tmp/analyze-validation/` for inspection.

## MCP Tools

Three new MCP tools expose the Week 1 pipeline:
- `discover_routes` – returns normalized routes
- `assess_risks` – returns risk findings
- `analyze_application` – full pipeline (routes + risks + strategy)

These can be orchestrated by external agents for autonomous analysis workflows.

## Next Steps

- Extend route discovery to static code analysis (FastAPI, Flask, Django)
- Add runtime crawling for UI discovery
- Feed enriched metadata into Week 2 test generation
