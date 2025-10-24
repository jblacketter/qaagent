# QA Agent Examples

This directory contains runnable sample projects that demonstrate how to use QA Agent end to end. Each example is self‑contained and ships with configuration so you can go from cloning the repository to running tests in a few minutes.

## Available Examples

- [`petstore-api`](petstore-api/): FastAPI implementation of the classic Petstore service. Includes an OpenAPI specification, ready-to-run server, and preconfigured `.qaagent.toml`.

## Getting Started

1. Create and activate a virtual environment in the repository root if you have not already.
2. Install QA Agent with the tooling required for the example:
   ```bash
   pip install -e ".[api,report]"
   pip install fastapi uvicorn
   ```
3. Follow the example-specific README for setup and usage.

## Contributing Examples

When adding a new example:

1. Place it in a dedicated subdirectory.
2. Include a README with prerequisites and a quick start section.
3. Provide any supporting assets (configs, fixtures, screenshots) within the subdirectory.
4. Keep dependencies isolated—document additional pip installs or provide a local `requirements.txt`.
