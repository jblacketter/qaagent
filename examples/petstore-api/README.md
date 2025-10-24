# Petstore API Example

This example bundles a minimal FastAPI implementation of the classic Petstore service together with an OpenAPI specification and QA Agent configuration. It is the fastest way to try QA Agent end to end.

## Prerequisites

- Python 3.11+
- Virtual environment activated in the project root
- QA Agent installed with API tooling:
  ```bash
  pip install -e ".[api,report]"
  pip install -r requirements.txt
  ```

## Quick Start (5 minutes)

1. **Start the API server** in a new terminal:
   ```bash
   uvicorn server:app --app-dir examples/petstore-api --reload --port 8765
   ```

2. **Explore the OpenAPI spec** (optional):
   ```bash
   open examples/petstore-api/openapi.yaml
   ```

3. **Run the QA Agent workflow** from the project root:
   ```bash
   # Generate analysis metadata
   qaagent analyze examples/petstore-api

   # Execute Schemathesis against the running server
   qaagent schemathesis-run \
     --openapi examples/petstore-api/openapi.yaml \
     --base-url http://localhost:8765 \
     --outdir examples/petstore-api/tests/results

   # Generate a findings report
   qaagent report \
     --sources examples/petstore-api/tests/results/junit.xml \
     --out examples/petstore-api/tests/findings.md
   ```

4. **Inspect the output**:
   - `examples/petstore-api/tests/results/` contains Schemathesis artifacts
   - `examples/petstore-api/tests/findings.md` summarizes issues

## Intelligent Analysis (Phase 2 Preview)

Generate automated insights about the API:

```bash
# Discover routes
qaagent analyze routes --openapi examples/petstore-api/openapi.yaml --out examples/petstore-api/analysis/routes.json

# Assess risks and produce a Markdown summary
qaagent analyze risks \
  --routes examples/petstore-api/analysis/routes.json \
  --markdown examples/petstore-api/analysis/risks.md

# Create a testing strategy
qaagent analyze strategy \
  --routes examples/petstore-api/analysis/routes.json \
  --risks examples/petstore-api/analysis/risks.json \
  --out examples/petstore-api/analysis/strategy.yaml
```

Artifacts will be saved under `examples/petstore-api/analysis/` for easy review.

## Configuration

- `.qaagent.toml` is preconfigured to point at the local OpenAPI file and server.
- `.env.example` demonstrates the environment variables used by the configuration loader.

## Shutdown

When finished, stop the FastAPI server with `Ctrl+C`.
