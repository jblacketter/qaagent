# RUNBOOK — qaagent MVP

**Last Updated:** 2025-10-24
**Audience:** Engineers and users running qaagent locally
**Status:** Living document (expand during Sprint 1+)

---

## Purpose

This runbook provides step-by-step instructions for installing, configuring, and operating qaagent for local quality analysis of Python projects.

---

## Prerequisites

### System Requirements

**Operating Systems:**
- macOS 10.15+ (tested on M1/M2)
- Linux (Ubuntu 20.04+, Debian 11+)
- Windows 10+ (via WSL2 recommended)

**Required Software:**
- Python 3.11 or 3.12 (3.10 may work but untested)
- Git 2.39+ (for churn analysis)
- 500MB free disk space minimum

### Optional Tools

For full feature support, install these analysis tools:

| Tool | Purpose | Installation | Priority |
|------|---------|--------------|----------|
| flake8 | Style linting | `pip install flake8==6.1.0` | High |
| pylint | Code quality | `pip install pylint==3.2.0` | High |
| bandit | Security scanning | `pip install bandit==1.7.9` | High |
| pip-audit | Dependency CVEs | `pip install pip-audit==2.7.3` | High |
| safety | Fallback for pip-audit | `pip install safety` | Medium |
| coverage | Test coverage | `pip install coverage` | Medium |

**Note:** qaagent gracefully degrades if tools are missing. You'll see warnings but analysis will continue with available tools.

---

## Installation

### 1. Clone and Setup Virtual Environment

```bash
# Clone repository (or download release)
git clone https://github.com/yourusername/qaagent.git
cd qaagent

# Create Python virtual environment
python3.11 -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate

# Activate (Windows WSL)
source .venv/bin/activate

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1
```

### 2. Install qaagent

```bash
# Install core package
pip install -e .

# Or install with all optional dependencies
pip install -e ".[dev,ui,api]"

# Verify installation
qaagent --version
```

### 3. Install Analysis Tools

**Quick install (all tools):**
```bash
pip install -r requirements-dev.txt
```

**Individual tool installation:**
```bash
# Essential security & quality tools
pip install flake8==6.1.0 pylint==3.2.0 bandit==1.7.9 pip-audit==2.7.3
```

### 4. Verify Setup

```bash
# Check which tools are available
qaagent doctor

# Expected output:
# ✓ Python 3.11.5
# ✓ git 2.42.0
# ✓ flake8 6.1.0
# ✓ pylint 3.2.0
# ✓ bandit 1.7.9
# ✓ pip-audit 2.7.3
# ✗ safety (optional)
```

---

## Configuration

### Project Configuration

Create `qaagent.toml` in your target project (optional):

```toml
[tool.qaagent]
# Enable/disable collectors
collectors = ["flake8", "pylint", "bandit", "pip-audit", "coverage", "git-churn"]

# Tool-specific settings
[tool.qaagent.flake8]
max_line_length = 100
ignore = ["E203", "W503"]

[tool.qaagent.git-churn]
window = "90d"  # Analyze last 90 days

[tool.qaagent.coverage]
required_coverage = 0.80  # 80% coverage target
```

### Global Configuration

Edit `~/.qaagent/config/risk_config.yaml` to customize risk weights:

```yaml
scoring:
  weights:
    security: 3.0
    coverage: 2.0
    churn: 2.0
```

(See RISK_SCORING.md for details)

---

## Basic Usage

### Running Your First Analysis

```bash
# Navigate to your Python project
cd /path/to/your/project

# Run analysis
qaagent analyze

# Analysis will:
# 1. Detect project type and structure
# 2. Run enabled collectors (flake8, pylint, bandit, etc.)
# 3. Compute coverage and churn metrics
# 4. Store results in ~/.qaagent/runs/<timestamp>/
# 5. Display summary
```

**Example Output:**
```
🔍 Analyzing project: myproject
📂 Target: /Users/jack/projects/myproject
⏱️  Started: 2025-10-24 19:30:12

Running collectors...
  ✓ flake8      (128 findings, 4.2s)
  ✓ pylint      (67 findings, 12.1s)
  ✓ bandit      (5 findings, 2.3s)
  ✓ pip-audit   (2 vulnerabilities, 6.8s)
  ✓ coverage    (64% line coverage, 1.1s)
  ✓ git-churn   (187 files analyzed, 0.9s)

📊 Analysis complete!
Run ID: 20251024_193012Z
Evidence: ~/.qaagent/runs/20251024_193012Z/

Summary:
  Total findings: 202
  Security issues: 7
  Coverage: 64% (target: 80%)
  High-churn files: 12

Next steps:
  qaagent report --format html
  qaagent dashboard
```

### Viewing Results

```bash
# Generate HTML report
qaagent report --format html --out report.html
open report.html

# Launch interactive dashboard
qaagent dashboard

# Open in browser at http://localhost:8765
```

---

## Common Workflows

### Workflow 1: Pre-Commit Check

Run analysis before committing:

```bash
# Quick analysis (skip slow collectors)
qaagent analyze --quick

# Only run security checks
qaagent analyze --tools bandit,pip-audit

# Fail CI if P0 risks found
qaagent analyze --fail-on P0
```

### Workflow 2: CI/CD Integration

```yaml
# .github/workflows/qa.yml
- name: Run QA Analysis
  run: |
    pip install qaagent
    qaagent analyze --format json --out qa-report.json
    qaagent report --format html --out qa-report.html

- name: Upload Reports
  uses: actions/upload-artifact@v3
  with:
    name: qa-reports
    path: qa-report.*
```

### Workflow 3: Compare Runs

```bash
# Analyze current state
qaagent analyze

# After changes, analyze again
qaagent analyze

# Compare (future feature)
qaagent diff <run_id_1> <run_id_2>
```

---

## Troubleshooting

### Issue: "Tool not found" Warnings

**Symptom:**
```
⚠️  flake8 not found, skipping style analysis
```

**Solution:**
```bash
pip install flake8==6.1.0
qaagent doctor  # Verify installation
```

### Issue: "No git repository found"

**Symptom:**
```
⚠️  git-churn collector skipped: not a git repository
```

**Solution:**
- Ensure you're running qaagent inside a git repository
- Initialize git: `git init`
- Or disable git-churn: `qaagent analyze --skip git-churn`

### Issue: "Permission denied writing to ~/.qaagent/"

**Symptom:**
```
ERROR: Cannot write to /Users/jack/.qaagent/runs/
```

**Solution:**
```bash
# Fix permissions
chmod 755 ~/.qaagent
mkdir -p ~/.qaagent/runs
chmod 755 ~/.qaagent/runs

# Or specify different output location
qaagent analyze --output-dir ./local-runs
```

### Issue: Coverage File Not Found

**Symptom:**
```
⚠️  coverage.xml not found, skipping coverage analysis
```

**Solution:**
```bash
# Generate coverage first
pytest --cov=src --cov-report=xml

# Then run qaagent
qaagent analyze
```

### Issue: Analysis Too Slow

**Symptom:** Analysis takes >5 minutes

**Solutions:**
```bash
# Skip slow collectors
qaagent analyze --skip pylint

# Analyze only changed files (future feature)
qaagent analyze --changed-only

# Limit git churn window
qaagent analyze --churn-window 30d
```

---

## Advanced Usage

### Custom Risk Configuration

Create `~/.qaagent/config/risk_config.yaml`:

```yaml
scoring:
  weights:
    security: 5.0  # Prioritize security
    coverage: 1.0  # De-prioritize coverage

prioritization:
  bands:
    - { name: "P0", min_score: 90 }  # Stricter P0 threshold
    - { name: "P1", min_score: 70 }
    - { name: "P2", min_score: 50 }
    - { name: "P3", min_score: 0 }
```

### Custom CUJ Mapping

Create `cuj.yaml` in project root:

```yaml
version: 1
product: myproject
journeys:
  - id: user_auth
    name: "User authentication flow"
    components: ["src/auth/*"]
    apis:
      - {method: POST, endpoint: "/api/login"}
    acceptance:
      - "Valid credentials return 200"
      - "Invalid credentials return 401"

coverage_targets:
  user_auth: 90  # 90% coverage required
```

### Filtering Analysis Scope

```bash
# Analyze only specific paths
qaagent analyze --paths "src/auth/" "src/api/"

# Exclude paths
qaagent analyze --exclude "tests/" "docs/"

# Analyze only Python files matching pattern
qaagent analyze --include "*.py"
```

---

## Data Management

### Evidence Store Location

All analysis results stored in:
```
~/.qaagent/runs/<timestamp>/
  manifest.json
  evidence/
    findings.jsonl
    coverage.jsonl
    churn.jsonl
    quality.jsonl
  artifacts/
    flake8.log
    pylint.json
    bandit.json
```

### Cleanup Old Runs

```bash
# List all runs
qaagent runs list

# Delete runs older than 30 days
qaagent runs clean --older-than 30d

# Delete specific run
qaagent runs delete 20251024_193012Z
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QAAGENT_HOME` | `~/.qaagent` | Base directory for configs and runs |
| `QAAGENT_RUNS_DIR` | `~/.qaagent/runs` | Override runs directory (used by CLI/API) |
| `QAAGENT_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `QAAGENT_TIMEOUT` | `120` | Default tool timeout in seconds |
| `QAAGENT_PARALLEL` | `false` | Run collectors in parallel (experimental) |

---

## Analysis Pipeline

### Run Collectors
```bash
qaagent analyze collectors /path/to/project
# Outputs run ID like 20251025_080902Z stored in ~/.qaagent/runs/<run_id>
```

### Aggregate Risks
```bash
# Use latest run (omit run-id) or specify explicitly
qaagent analyze risks 20251025_080902Z --config handoff/risk_config.yaml --top 15

# Optional JSON export
qaagent analyze risks --json-out risks.json
```

### Generate Recommendations
```bash
qaagent analyze recommendations 20251025_080902Z \
  --risk-config handoff/risk_config.yaml \
  --cuj-config handoff/cuj.yaml \
  --top 10
```

### Start API Server
```bash
# Runs on http://127.0.0.1:8000 by default
qaagent api --runs-dir ~/.qaagent/runs

# Query examples
curl http://127.0.0.1:8000/api/runs | jq
curl http://127.0.0.1:8000/api/runs/<run_id>/risks | jq
curl http://127.0.0.1:8000/api/runs/<run_id>/recommendations | jq
```

## Getting Help

```bash
# General help
qaagent --help

# Command-specific help
qaagent analyze --help

# Check system compatibility
qaagent doctor

# View version and build info
qaagent --version

# Enable verbose logging
qaagent --verbose analyze
```

**Report Issues:**
- GitHub: https://github.com/yourusername/qaagent/issues
- Docs: https://qaagent.dev/docs

---

## Next Steps

After successful first run:

1. ✅ Review findings and risks via CLI/UI
2. ✅ Tune risk weights (`handoff/risk_config.yaml`) and CUJ targets (`handoff/cuj.yaml`)
3. ✅ Integrate collectors & API queries into CI
4. ✅ Schedule recurring analysis + dashboard refresh
5. ✅ Prepare for Sprint 3 (dashboard/API integration)
