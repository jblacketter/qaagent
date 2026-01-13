# LLM-Powered Fixes - Implementation Guide

## Overview

Integrate local LLM (running on Windows GPU machine) to generate context-aware code fixes for security and quality issues found by QA Agent.

**Status:** 📋 Planned - Implement when on Windows machine

## Architecture

```
┌─────────────────┐         HTTP/API         ┌──────────────────┐
│   Mac Mini      │ ◄─────────────────────► │ Windows Machine  │
│   (qaagent)     │   http://WIN_IP:11434   │   (Ollama GPU)   │
│   Development   │                          │   LLM Server     │
└─────────────────┘                          └──────────────────┘
```

## Prerequisites

**Windows Machine:**
- ✅ Ollama installed (already done)
- GPU available for acceleration
- Network accessible from Mac

**Mac Mini:**
- QA Agent installed
- Network access to Windows machine

## Implementation Plan

### Phase 1: Ollama Server Setup (Windows Machine)

#### 1.1 Configure Ollama for Network Access

Create PowerShell script: `C:\ollama\start-server.ps1`

```powershell
# Configure Ollama to listen on all interfaces (not just localhost)
$env:OLLAMA_HOST = "0.0.0.0:11434"

# Optional: Set number of GPU layers to use
$env:OLLAMA_NUM_GPU = "999"  # Use all available GPU layers

# Start Ollama server
Write-Host "Starting Ollama server on 0.0.0.0:11434"
Write-Host "GPU acceleration enabled"
ollama serve
```

**Run as Windows Service (Optional but recommended):**

```powershell
# Install NSSM (Non-Sucking Service Manager)
# Download from: https://nssm.cc/download

# Install as service
nssm install OllamaServer "C:\Users\YOU\AppData\Local\Programs\Ollama\ollama.exe" "serve"
nssm set OllamaServer AppEnvironmentExtra OLLAMA_HOST=0.0.0.0:11434
nssm start OllamaServer

# Verify
nssm status OllamaServer
```

#### 1.2 Pull Code-Focused Models

```powershell
# Best models for code fixes (in order of recommendation)

# 1. DeepSeek Coder - Best for code understanding and fixes
ollama pull deepseek-coder:6.7b      # 4GB RAM, fast
ollama pull deepseek-coder:33b       # 20GB RAM, very accurate

# 2. CodeLlama - Good alternative
ollama pull codellama:13b            # 8GB RAM
ollama pull codellama:34b            # 20GB RAM

# 3. Llama 3 - General purpose, good at code
ollama pull llama3:8b                # 5GB RAM

# Test a model
ollama run deepseek-coder:6.7b "Write a Python function to reverse a string"
```

#### 1.3 Find Windows Machine IP

```powershell
# Get IPv4 address
ipconfig | findstr IPv4

# Example output: 192.168.1.100
```

#### 1.4 Test Connectivity from Mac

```bash
# From Mac, test connection
curl http://192.168.1.100:11434/api/tags

# Should return JSON with available models
```

### Phase 2: QA Agent LLM Integration (Mac)

#### 2.1 Create LLM Client Module

**File:** `src/qaagent/llm_client.py`

```python
"""Client for connecting to local or remote LLM servers (Ollama, LM Studio, etc.)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict
import requests

LOGGER = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM connection."""
    provider: str = "ollama"  # ollama, openai, anthropic
    base_url: str = "http://localhost:11434"  # Ollama default
    model: str = "deepseek-coder:6.7b"
    timeout: int = 120
    temperature: float = 0.2  # Lower = more deterministic
    max_tokens: int = 2000


class LLMClient:
    """Client for generating code fixes using LLM."""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()

    def generate_fix(
        self,
        code_snippet: str,
        issue_description: str,
        file_path: str,
        context: Optional[Dict] = None,
    ) -> Dict[str, str]:
        """
        Generate a fix for a code issue using LLM.

        Args:
            code_snippet: The problematic code
            issue_description: Description of the issue (from bandit/flake8/etc)
            file_path: Path to the file with the issue
            context: Additional context (severity, CWE, etc.)

        Returns:
            Dict with 'fixed_code', 'explanation', and 'confidence'
        """
        prompt = self._build_fix_prompt(
            code_snippet, issue_description, file_path, context
        )

        try:
            response = self._call_llm(prompt)
            return self._parse_fix_response(response)
        except Exception as e:
            LOGGER.error(f"LLM fix generation failed: {e}")
            return {
                "fixed_code": None,
                "explanation": f"Error: {e}",
                "confidence": 0.0,
            }

    def _build_fix_prompt(
        self,
        code: str,
        issue: str,
        file_path: str,
        context: Optional[Dict],
    ) -> str:
        """Build the prompt for the LLM."""
        severity = context.get("severity", "unknown") if context else "unknown"
        cwe = context.get("cwe", "N/A") if context else "N/A"

        return f"""You are a security and code quality expert. Fix the following issue:

**File:** {file_path}
**Issue:** {issue}
**Severity:** {severity}
**CWE:** {cwe}

**Current Code:**
```python
{code}
```

**Instructions:**
1. Provide the FIXED code (complete, ready to use)
2. Explain WHAT you changed and WHY
3. Rate your confidence (0-100)

**Response Format (JSON):**
```json
{{
  "fixed_code": "complete fixed code here",
  "explanation": "explanation of changes",
  "confidence": 85
}}
```

Respond ONLY with valid JSON.
"""

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM API."""
        if self.config.provider == "ollama":
            return self._call_ollama(prompt)
        elif self.config.provider == "openai":
            return self._call_openai(prompt)
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API."""
        url = f"{self.config.base_url}/api/generate"
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        LOGGER.info(f"Calling Ollama at {url} with model {self.config.model}")

        response = requests.post(
            url,
            json=payload,
            timeout=self.config.timeout,
        )
        response.raise_for_status()

        result = response.json()
        return result.get("response", "")

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI-compatible API."""
        # Implementation for OpenAI API
        raise NotImplementedError("OpenAI provider not yet implemented")

    def _parse_fix_response(self, response: str) -> Dict[str, str]:
        """Parse LLM response into structured format."""
        # Try to extract JSON from response
        try:
            # Find JSON block in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                return {
                    "fixed_code": data.get("fixed_code"),
                    "explanation": data.get("explanation", ""),
                    "confidence": float(data.get("confidence", 0)),
                }
        except Exception as e:
            LOGGER.warning(f"Failed to parse JSON response: {e}")

        # Fallback: return raw response
        return {
            "fixed_code": None,
            "explanation": response,
            "confidence": 0.0,
        }

    def is_available(self) -> bool:
        """Check if LLM server is available."""
        try:
            if self.config.provider == "ollama":
                url = f"{self.config.base_url}/api/tags"
                response = requests.get(url, timeout=5)
                return response.status_code == 200
        except Exception:
            return False
        return False
```

#### 2.2 Create LLM Fix Generator

**File:** `src/qaagent/llm_fixer.py`

```python
"""LLM-powered code fix generator."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional

from qaagent.evidence import FindingRecord
from qaagent.llm_client import LLMClient, LLMConfig

LOGGER = logging.getLogger(__name__)


@dataclass
class FixSuggestion:
    """A suggested fix from the LLM."""
    file_path: str
    original_code: str
    fixed_code: str
    explanation: str
    confidence: float
    finding_id: str


class LLMFixGenerator:
    """Generate fixes for code issues using LLM."""

    def __init__(self, project_path: Path, llm_client: Optional[LLMClient] = None):
        self.project_path = Path(project_path)
        self.llm_client = llm_client or LLMClient()

    def generate_fixes(
        self,
        findings: List[FindingRecord],
        min_severity: str = "high",
        max_fixes: int = 10,
    ) -> List[FixSuggestion]:
        """
        Generate fixes for findings using LLM.

        Args:
            findings: List of findings from evidence
            min_severity: Only fix issues at or above this severity
            max_fixes: Maximum number of fixes to generate

        Returns:
            List of fix suggestions
        """
        # Filter findings by severity
        severity_order = ["critical", "high", "medium", "low"]
        min_index = severity_order.index(min_severity)
        filtered = [
            f for f in findings
            if severity_order.index(f.severity) <= min_index
        ]

        # Sort by severity (critical first)
        filtered.sort(
            key=lambda f: (
                severity_order.index(f.severity),
                -f.confidence if f.confidence else 0,
            )
        )

        # Generate fixes
        fixes = []
        for finding in filtered[:max_fixes]:
            try:
                fix = self._generate_fix_for_finding(finding)
                if fix:
                    fixes.append(fix)
            except Exception as e:
                LOGGER.error(f"Failed to generate fix for {finding.evidence_id}: {e}")

        return fixes

    def _generate_fix_for_finding(
        self,
        finding: FindingRecord,
    ) -> Optional[FixSuggestion]:
        """Generate a fix for a single finding."""
        # Read the code snippet from file
        file_path = self.project_path / finding.file
        if not file_path.exists():
            LOGGER.warning(f"File not found: {file_path}")
            return None

        code_snippet = self._extract_code_context(file_path, finding.line)

        # Generate fix using LLM
        result = self.llm_client.generate_fix(
            code_snippet=code_snippet,
            issue_description=f"{finding.code}: {finding.message}",
            file_path=str(finding.file),
            context={
                "severity": finding.severity,
                "tool": finding.tool,
                "confidence": finding.confidence,
                "cwe": finding.metadata.get("cwe") if finding.metadata else None,
            },
        )

        if not result.get("fixed_code"):
            return None

        return FixSuggestion(
            file_path=str(finding.file),
            original_code=code_snippet,
            fixed_code=result["fixed_code"],
            explanation=result["explanation"],
            confidence=result["confidence"],
            finding_id=finding.evidence_id,
        )

    def _extract_code_context(
        self,
        file_path: Path,
        line_number: Optional[int],
        context_lines: int = 10,
    ) -> str:
        """Extract code context around the issue."""
        try:
            lines = file_path.read_text().splitlines()
            if line_number is None:
                # Return whole file if no line number (up to 50 lines)
                return "\n".join(lines[:50])

            start = max(0, line_number - context_lines)
            end = min(len(lines), line_number + context_lines)
            return "\n".join(lines[start:end])
        except Exception as e:
            LOGGER.error(f"Failed to read file {file_path}: {e}")
            return ""
```

#### 2.3 Add CLI Command

**File:** `src/qaagent/cli.py` (add after the `fix` command)

```python
@app.command("fix-llm")
def fix_llm(
    target: Optional[str] = typer.Argument(None, help="Target name"),
    severity: str = typer.Option("high", help="Minimum severity to fix (critical, high, medium, low)"),
    max_fixes: int = typer.Option(10, help="Maximum number of fixes to generate"),
    apply: bool = typer.Option(False, "--apply", help="Apply fixes automatically (dangerous!)"),
    llm_url: Optional[str] = typer.Option(None, help="Override LLM server URL"),
    llm_model: Optional[str] = typer.Option(None, help="Override LLM model"),
):
    """Generate AI-powered fixes using local LLM (requires Ollama on GPU machine)."""
    from qaagent.llm_client import LLMClient, LLMConfig
    from qaagent.llm_fixer import LLMFixGenerator
    from qaagent.evidence.run_manager import RunManager
    from qaagent.evidence import EvidenceReader

    # Get target
    if target is None:
        try:
            active_entry, _ = load_active_profile()
            target_name = active_entry.name
            target_path = active_entry.resolved_path()
        except Exception:
            console.print("[red]No active target[/red]")
            raise typer.Exit(code=2)
    else:
        manager = _target_manager()
        entry = manager.get(target)
        if not entry:
            console.print(f"[red]Target not found: {target}[/red]")
            raise typer.Exit(code=1)
        target_name = entry.name
        target_path = entry.resolved_path()

    # Configure LLM client
    config = LLMConfig()
    if llm_url:
        config.base_url = llm_url
    if llm_model:
        config.model = llm_model

    client = LLMClient(config)

    # Check LLM availability
    console.print(f"[cyan]Checking LLM server at {config.base_url}...[/cyan]")
    if not client.is_available():
        console.print(f"[red]✗ LLM server not available at {config.base_url}[/red]")
        console.print()
        console.print("[yellow]Make sure Ollama is running on your Windows machine:[/yellow]")
        console.print("  1. Open PowerShell on Windows")
        console.print("  2. Run: $env:OLLAMA_HOST=\"0.0.0.0:11434\"; ollama serve")
        console.print("  3. Or run the Windows service if configured")
        raise typer.Exit(code=1)

    console.print(f"[green]✓ LLM server available[/green]")
    console.print(f"[cyan]Model: {config.model}[/cyan]")
    console.print()

    # Get latest run
    run_mgr = RunManager()
    latest_run = run_mgr.get_latest_run(target_name)
    if not latest_run:
        console.print(f"[red]No analysis runs found for '{target_name}'[/red]")
        console.print("[yellow]Run analysis first:[/yellow] qaagent analyze routes")
        raise typer.Exit(code=1)

    # Read findings
    reader = EvidenceReader(latest_run)
    findings = reader.read_findings()

    console.print(f"[cyan]Found {len(findings)} total findings[/cyan]")
    console.print(f"[cyan]Generating fixes for {severity}+ severity issues...[/cyan]")
    console.print()

    # Generate fixes
    generator = LLMFixGenerator(target_path, client)
    fixes = generator.generate_fixes(findings, min_severity=severity, max_fixes=max_fixes)

    if not fixes:
        console.print("[yellow]No fixes generated[/yellow]")
        return

    # Display fixes
    for i, fix in enumerate(fixes, 1):
        console.print(f"[bold cyan]Fix #{i}:[/bold cyan] {fix.file_path}")
        console.print(f"[dim]Confidence: {fix.confidence:.0f}%[/dim]")
        console.print()
        console.print("[yellow]Explanation:[/yellow]")
        console.print(fix.explanation)
        console.print()
        console.print("[red]Original:[/red]")
        console.print(fix.original_code[:200])
        console.print()
        console.print("[green]Fixed:[/green]")
        console.print(fix.fixed_code[:200])
        console.print()
        console.print("─" * 80)
        console.print()

    console.print(f"[green]✓ Generated {len(fixes)} fixes[/green]")

    if apply:
        console.print("[red]⚠️  Auto-apply not yet implemented for safety[/red]")
        console.print("[yellow]Review fixes manually and apply carefully[/yellow]")
```

#### 2.4 Configuration

**File:** `~/.qaagent/config.yaml` (add section)

```yaml
llm:
  provider: ollama
  base_url: http://192.168.1.100:11434  # Your Windows machine IP
  model: deepseek-coder:6.7b
  timeout: 120
  temperature: 0.2
```

### Phase 3: Testing Workflow

#### 3.1 Start Ollama on Windows

```powershell
# In PowerShell on Windows
$env:OLLAMA_HOST = "0.0.0.0:11434"
ollama serve

# Or if installed as service:
nssm start OllamaServer
```

#### 3.2 Test from Mac

```bash
# 1. Test connection
curl http://YOUR_WINDOWS_IP:11434/api/tags

# 2. Scan a project
qaagent use sonicgrid
qaagent analyze routes

# 3. Generate AI fixes
qaagent fix-llm --severity high --max-fixes 5

# 4. Review and manually apply fixes
```

## Model Recommendations

### For Code Fixes (Ranked)

1. **DeepSeek Coder 6.7B** (Recommended)
   - Size: ~4GB RAM
   - Best: Python, JavaScript, general code
   - Speed: Fast on GPU
   - Command: `ollama pull deepseek-coder:6.7b`

2. **CodeLlama 13B**
   - Size: ~8GB RAM
   - Best: Python, C++, system programming
   - Speed: Medium
   - Command: `ollama pull codellama:13b`

3. **DeepSeek Coder 33B** (High accuracy)
   - Size: ~20GB RAM
   - Best: Complex refactoring, architecture
   - Speed: Slower but very accurate
   - Command: `ollama pull deepseek-coder:33b`

## Network Configuration

### Firewall (Windows)

```powershell
# Allow Ollama through Windows Firewall
New-NetFirewallRule -DisplayName "Ollama Server" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow
```

### Finding Windows IP

```powershell
# PowerShell
(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -like "*Ethernet*" -or $_.InterfaceAlias -like "*Wi-Fi*"}).IPAddress

# Or simply:
ipconfig | findstr IPv4
```

## Security Considerations

1. **Network Security**
   - Ollama server is exposed on local network
   - Use firewall to restrict access to Mac IP only
   - Don't expose to internet

2. **Code Safety**
   - NEVER auto-apply LLM fixes without review
   - Always use `--dry-run` mode first
   - Test fixes in isolated environment

3. **API Key Management**
   - No API keys needed for Ollama
   - If using OpenAI: store keys in env vars

## Troubleshooting

### "Connection refused"
```bash
# Check if Ollama is running on Windows
curl http://WINDOWS_IP:11434/api/tags

# Check Windows firewall
# Check if Mac can ping Windows
ping WINDOWS_IP
```

### "Model not found"
```powershell
# On Windows, pull the model
ollama pull deepseek-coder:6.7b

# List available models
ollama list
```

### Slow Performance
```powershell
# Check GPU usage on Windows
nvidia-smi

# Ensure Ollama is using GPU
ollama run deepseek-coder:6.7b "test"
# Should show GPU layers loaded
```

## Future Enhancements

1. **Batch Fixes** - Fix multiple files in one pass
2. **Test Generation** - Generate tests for untested code
3. **Explanation Mode** - Explain *why* code is risky
4. **Interactive Mode** - Review and approve each fix
5. **PR Generation** - Create GitHub PRs with fixes
6. **Caching** - Cache LLM responses for repeated issues

## Files to Create

- [ ] `src/qaagent/llm_client.py`
- [ ] `src/qaagent/llm_fixer.py`
- [ ] `src/qaagent/cli.py` (add `fix-llm` command)
- [ ] `~/.qaagent/config.yaml` (add LLM section)
- [ ] `C:\ollama\start-server.ps1` (Windows)
- [ ] Windows Service setup (optional)

## Estimated Time

- Windows Ollama setup: 30 minutes
- Mac integration code: 2 hours
- Testing and refinement: 1 hour
- **Total: ~3.5 hours**

## Next Steps

When ready to implement:

1. **On Windows:**
   - Configure Ollama for network access
   - Pull recommended model
   - Test from Mac

2. **On Mac:**
   - Implement LLM client and fixer
   - Add CLI command
   - Test with SonicGrid

3. **Iterate:**
   - Try different models
   - Tune prompts
   - Improve accuracy
