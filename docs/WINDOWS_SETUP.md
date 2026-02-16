# Windows Setup Guide (RTX 4070) for QAAgent + Ollama

This guide helps you run QAAgent on Windows and prepare for local LLMs with Ollama.

## Prerequisites
- Windows 11 (recommended)
- Python 3.11 (installed as `py -3.11`)
- Git
- Node.js LTS (20+)
- (Optional, for GPUs beyond Ollama) NVIDIA GPU drivers up to date

## Clone and Create a Virtual Env
```powershell
# In a terminal (PowerShell)
cd path\to\your\workspace
git clone <your-repo-url> qaagent
cd qaagent
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip wheel
```

## Install Dependencies

> **Note:** The `[llm]` extras include `litellm` which may attempt to install `uvloop`.
> `uvloop` does not support Windows. The project pins `uvloop` with a platform marker
> so it is excluded automatically on Windows. If you see uvloop-related errors, ensure
> you are installing from the latest `pyproject.toml`.

Install the subsets you need:
```powershell
# Base CLI + tests
pip install -e .

# API testing (Schemathesis + YAML)
pip install -e .[api]

# UI testing (Playwright)
pip install -e .[ui]
qaagent playwright-install  # installs browsers

# Performance (Locust)
pip install -e .[perf]

# Reports (HTML rendering)
pip install -e .[report]

# LLM features (Ollama + litellm)
pip install -e .[llm]

# Config convenience (.env auto-load)
pip install -e .[config]
```

## Optional: Node + Lighthouse
```powershell
# Node should be installed. Lighthouse is invoked via npx automatically by the CLI.
# Verify node
node --version
```

## Run a Quick Sanity Check
```powershell
pytest -q
qaagent analyze .
qaagent a11y-run --url https://example.com
qaagent lighthouse-audit --url https://example.com
qaagent perf-scaffold
$env:BASE_URL = "https://example.com"
qaagent perf-run --users 5 --spawn-rate 2 --run-time 15s
qaagent report --format html --out reports/findings.html
```
Open `reports\findings.html` in your browser.

## Configuration and Secrets
- `qaagent init` creates `.qaagent.toml` and `.env.example`.
- Copy `.env.example` to `.env` and set:
  - `API_TOKEN` if your API needs auth.
  - `BASE_URL` for UI/perf runners.
- `.qaagent.toml` can specify `api.openapi`, `api.base_url`, `api.auth`, and filters.

---

# Prepare for Ollama (Local LLM)

We’ll add Ollama integration next. Here’s how to install and verify it on Windows.

## Install Ollama
```powershell
# Option 1: Winget (recommended)
winget install Ollama.Ollama

# Option 2: Download installer from https://ollama.com/
```

Start Ollama service (if not already running) and pull a model:
```powershell
ollama --version
ollama pull qwen2.5:14b   # or llama3.1:8b for lighter usage
ollama run qwen2.5:14b "Say hello"
```

## GPU Notes
- Ollama uses your RTX 4070 automatically via CUDA if available.
- Keep NVIDIA drivers current.
- For Python extras using CUDA (e.g., PyTorch), prefer Python 3.11 and match CUDA toolkit versions when you add them.

## What We’ll Add Next (Ollama Integration)
- Extras: `[llm]` → `ollama` client (and optional `litellm` for cloud routing)
- `src/qaagent/llm.py`: LLM wrapper with model selection via env or config
- CLI Commands:
  - `qaagent gen-tests` → propose/generate test stubs from OpenAPI/UI hints
  - `qaagent summarize` → executive summary from artifacts
  - `qaagent plan-run` → LangGraph planner that sequences tools (API/UI/a11y/perf)
- MCP Tools for generation/summarization and plan-run, so MCP clients can drive the agent

## Model Recommendations
- Planning/tool-use: `qwen2.5:7b` or `llama3.1:8b`
- Higher quality generation: `qwen2.5:14b`
- Keep a switch to cloud for tough tasks as a fallback

## Troubleshooting
- If browsers fail on Windows, re-run: `qaagent playwright-install`
- If Lighthouse fails, verify Node and allow `npx` to fetch.
- If performance tests can’t reach a host, set `BASE_URL` correctly.
- Use `--json-out` flags for machine-readable logs in CI or scripts.

