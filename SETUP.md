# Setup Guide

## Mac Setup (M1/M2/M3)

Your Mac Mini M1 is **perfect** for this project! Here's why and how to set it up:

### Why Mac M1 is Great for This Project

1. **MCP servers are lightweight** - No heavy compute needed
2. **Apple Silicon excels at Ollama** - If you want local LLM, M1 runs small models better than most x86 machines
3. **All QA tools work natively** - pytest, Playwright, Schemathesis run great on ARM
4. **Unified memory** - Your 8GB goes further than x86 systems

### Quick Setup on Mac

```bash
# 1. Ensure Python 3.11 is installed
brew install python@3.11

# 2. Clone and navigate to project
cd /path/to/qaagent

# 3. Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 4. Install base + MCP server (minimum to run)
pip install -e .[mcp]

# 5. Optional: Install additional features
pip install -e .[api,ui,config]

# 6. Verify installation & health
qaagent --help
qaagent doctor
qaagent-mcp  # Ctrl+C to exit once the banner appears
```

### Optional: Local LLM with Ollama

Only needed for test generation and summarization (project has fallbacks).

```bash
# Install Ollama
brew install ollama

# Start Ollama service (in a separate terminal)
ollama serve

# Pull a lightweight model (3B works great on M1)
ollama pull llama3.2:3b

# Install LLM extras in your project
pip install -e .[llm]

# Test it
qaagent gen-tests --kind api --openapi examples/api.yaml
```

### Playwright on Mac M1/M2/M3

```bash
# Install UI extras and browsers
pip install -e ".[ui]"
npx playwright install --with-deps
```

- **System Settings → Privacy & Security → Developer Tools**: ensure Terminal (or your shell) is allowed; otherwise WebKit may fail on macOS Sonoma.
- Install FFmpeg if you need video capture: `brew install ffmpeg`.
- Headless runs are significantly faster on Apple Silicon; use headed mode only for debugging.
- No Rosetta required—Playwright works natively on ARM.

### What You DON'T Need

- Windows machine with GPU
- Large models (3B is plenty for test generation)
- Expensive cloud API credits (unless you want to use them)

## Windows Setup

If you're on Windows:

```powershell
# 1. Ensure Python 3.11 is installed
py -3.11 --version

# 2. Create virtual environment
py -3.11 -m venv .venv
.\.venv\Scripts\activate

# 3. Install base + MCP
pip install -e .[mcp]

# 4. Optional extras
pip install -e .[api,ui,config]
```

## IDE Setup

### VSCode (Recommended)

1. Install Python extension
2. Select your `.venv` as the Python interpreter (Cmd+Shift+P → "Python: Select Interpreter")
3. Install MCP extension for testing MCP servers

### PyCharm

1. Open project
2. Settings → Project → Python Interpreter → Add Interpreter → Existing → Select `.venv/bin/python`
3. Mark `src` as "Sources Root"

## Verifying Your Setup

```bash
# Activate venv
source .venv/bin/activate  # Mac
# or
.\.venv\Scripts\activate   # Windows

# Run smoke tests
pytest tests/unit -v

# Optional: integration tests (requires extras)
pytest tests/integration -v

# Test CLI
qaagent --help
qaagent analyze .
qaagent doctor

# Test MCP server (minimal test)
qaagent-mcp
# Press Ctrl+C after seeing "MCP server running"
```

## Troubleshooting

### Mac M1/M2/M3 Specific

**Problem**: Some packages fail to install
```bash
# Solution: Use Rosetta Python if absolutely necessary (rare)
arch -x86_64 /usr/local/bin/python3.11 -m venv .venv-x86
```

**Problem**: Playwright browsers won't install
```bash
# Solution: Install browsers with npm
npx playwright install --with-deps
```
If WebKit continues to fail on macOS Sonoma, enable Terminal (or your IDE) under **System Settings → Privacy & Security → Developer Tools** and retry.

### General Issues

**Problem**: `command not found: qaagent`
```bash
# Solution: Ensure venv is activated and package installed
source .venv/bin/activate
pip install -e .
```

**Problem**: Import errors
```bash
# Solution: Reinstall in editable mode
pip install -e . --force-reinstall
```

## Next Steps

1. Read [README.md](README.md) for CLI usage examples
2. Try analyzing a sample repo: `qaagent analyze .`
3. Set up MCP client (Claude Desktop, etc.) to connect to `qaagent-mcp`
4. Check [CONTRIBUTING.md](CONTRIBUTING.md) if you want to extend the project

## Development Setup

If you're developing/contributing:

```bash
# Install all dev dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install

# Run all tests
pytest -v

# Format code
black src tests
ruff check src tests

# Type checking
mypy src
```
