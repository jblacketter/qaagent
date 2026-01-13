# MCP and Agents: Complete Guide

**Date**: 2025-10-27
**Purpose**: Reference guide for understanding and extending MCP + Agent capabilities in qaagent

---

## Table of Contents

1. [What is MCP?](#what-is-mcp)
2. [Current MCP Implementation](#current-mcp-implementation)
3. [How MCP Enables Agents](#how-mcp-enables-agents)
4. [Agent Patterns in This Project](#agent-patterns-in-this-project)
5. [Creating Your Own Agents](#creating-your-own-agents)
6. [Examples and Patterns](#examples-and-patterns)
7. [Next Steps and Opportunities](#next-steps-and-opportunities)

---

## What is MCP?

**MCP (Model Context Protocol)** is a standard interface that lets AI agents access tools via JSON-RPC over stdio.

Think of it as an API that AI models understand natively.

### Key Concepts

```
┌─────────────────────────────────────────────────────────┐
│                   AI Agent (Claude)                     │
│  - Analyzes repositories                                │
│  - Generates test strategies                            │
│  - Reviews security findings                            │
└────────────────────┬────────────────────────────────────┘
                     │ MCP Protocol (JSON-RPC over stdio)
                     ▼
┌─────────────────────────────────────────────────────────┐
│              MCP Server (qaagent-mcp)                   │
│  - Exposes 11 QA tools                                  │
│  - Converts agent requests to qaagent commands          │
└────────────────────┬────────────────────────────────────┘
                     │ Internal Function Calls
                     ▼
┌─────────────────────────────────────────────────────────┐
│            QA Agent Core (Python Library)               │
│  - Route discovery, risk assessment                     │
│  - Schemathesis, pytest runners                         │
│  - Report generation                                    │
└─────────────────────────────────────────────────────────┘
```

---

## Current MCP Implementation

### Status: WELL-IMPLEMENTED

**Location**: `src/qaagent/mcp_server.py:1`

### 11 Tools Exposed

| Tool Name | Purpose | Key Features |
|-----------|---------|--------------|
| `discover_routes` | API route discovery | OpenAPI + source code analysis |
| `assess_risks` | Security/reliability assessment | Categorized risks with severity |
| `analyze_application` | End-to-end analysis | Routes + risks + test strategy |
| `schemathesis_run` | Property-based API testing | Auto-coverage metrics |
| `pytest_run` | Python test execution | JUnit XML output |
| `generate_report_tool` | QA findings consolidation | Markdown/HTML formats |
| `detect_openapi` | OpenAPI file discovery | Probing base URLs |
| `a11y_run` | Accessibility testing | axe-core integration |
| `lighthouse_audit` | Performance/quality audits | Desktop/mobile modes |
| `generate_tests` | LLM-based test generation | Fallback templates |
| `summarize_findings` | Executive summary generation | LLM optional |

### How to Use

```bash
# Start the MCP server
qaagent-mcp

# Or via CLI command
qaagent mcp-stdio
```

### Example: Claude Desktop Integration

**Config**: `~/Library/Application Support/Claude/claude_desktop_config.json`
```json
{
  "mcpServers": {
    "qaagent": {
      "command": "/path/to/qaagent/.venv/bin/qaagent-mcp"
    }
  }
}
```

**Usage in Claude**:
```
User: "Analyze the sonicgrid API for security risks"

Claude: [Uses discover_routes tool via MCP]
        [Uses assess_risks tool via MCP]
        [Returns comprehensive risk analysis]
```

### Implementation Quality

**Strengths**:
- ✅ Well-structured with 11 functional tools
- ✅ Full JSON-RPC 2.0 protocol compliance
- ✅ Proper dependency isolation (optional extra)
- ✅ Integration tests (`tests/integration/test_mcp_server.py:1`)
- ✅ Type-safe Pydantic models for all tool inputs
- ✅ Configuration inheritance from CLI
- ✅ Comprehensive docstrings

**Opportunities**:
- ❌ No streaming for long operations
- ❌ No MCP resources (expose reports/files directly)
- ❌ No MCP prompts (predefined workflows)
- ❌ No batch workflow tools

---

## How MCP Enables Agents

### The Connection

**MCP is the interface layer that lets AI agents USE your qaagent tools.**

### Example Flow

```python
# Agent thinks: "I need to discover routes in this FastAPI app"

# Agent calls MCP tool via JSON-RPC:
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "discover_routes",
    "arguments": {
      "target": "sonicgrid",
      "openapi": "/path/to/openapi.yaml"
    }
  }
}

# MCP server (src/qaagent/mcp_server.py:87) receives request
# Calls internal function: discover_routes_internal()
# Returns routes to agent

# Agent then chains another tool:
{
  "name": "assess_risks",
  "arguments": {
    "routes_json": "[routes from previous call]"
  }
}

# Agent now has risk assessment and can:
# - Generate test strategy
# - Create report
# - Recommend priorities
```

---

## Agent Patterns in This Project

### Dual-Agent Workflow

**Reference**: `docs/AGENT_WORKFLOW.md:1`

Your project uses a **dual-agent collaboration model**:

| Agent | Role | Tools |
|-------|------|-------|
| **Claude** | Analyzer & Reviewer | Claude Code (VSCode) |
| **Codex** | Implementer | Cursor IDE |
| **You** | Director & Validator | Terminal, Browser |

### The 5-Step Process

```
1. Analysis (Claude)
   ↓ Creates detailed analysis document

2. Review & Enhancement (Codex)
   ↓ Proposes implementation approach

3. Iteration (Both)
   ↓ Refine until consensus

4. Implementation (Codex)
   ↓ Writes code + tests

5. Review & Testing (Claude + You)
   ✓ Approve or request changes
```

### Autonomous Agent Vision

**Reference**: `docs/PHASE_2_AUTONOMOUS_QA_AGENT.md:1`

**Phase 2 Goal**: Build an AI-powered QA Agent that performs comprehensive analysis autonomously.

**Target Workflow**:
```bash
# Agent orchestrates entire workflow
qaagent full-analysis --target http://localhost:8000 --source src/

# Internally runs:
# 1. discover_routes()
# 2. assess_risks()
# 3. generate_strategy()
# 4. generate_tests()
# 5. security_scan()
# 6. generate_report()
```

---

## Creating Your Own Agents

### Pattern 1: MCP Tool Consumer (External Agent)

**Use Case**: External AI agent (like Claude Desktop) uses qaagent tools

**Steps**:

1. Start MCP server: `qaagent-mcp`
2. Configure AI client to connect via stdio
3. Agent calls tools via JSON-RPC

**Best for**: Integrating with existing AI tools

---

### Pattern 2: Add New MCP Tool

**Use Case**: Extend MCP server capabilities

**Example**: Add a `list_targets` tool

```python
# src/qaagent/mcp_server.py

class ListTargetsArgs(BaseModel):
    """Arguments for list_targets tool"""
    workspace_path: str | None = None

@mcp.tool()
def list_targets(args: ListTargetsArgs):
    """List all configured targets in workspace"""
    from .config.workspace import get_all_targets

    # Reuse internal function
    targets = get_all_targets(args.workspace_path)

    return {
        "targets": [
            {
                "name": t.name,
                "type": t.type,
                "last_run": t.last_run,
                "has_reports": len(t.reports) > 0
            }
            for t in targets
        ],
        "count": len(targets)
    }
```

**Key Patterns**:
- ✅ Use Pydantic BaseModel for arguments
- ✅ Reuse internal functions (don't duplicate logic)
- ✅ Return structured data (dicts/lists)
- ✅ Handle errors gracefully
- ✅ Add docstrings

---

### Pattern 3: Internal Workflow Agent

**Use Case**: qaagent itself orchestrates autonomous workflows

**Example**: Create an analysis workflow agent

```python
# src/qaagent/agents/workflow_agent.py

from ..collectors.route_discovery import discover_routes_internal
from ..analyzers.risk import assess_risks_internal

class WorkflowAgent:
    """Autonomous agent that orchestrates QA workflows"""

    def __init__(self, target: str):
        self.target = target
        self.context = {}

    def run_full_analysis(self):
        """Execute complete analysis workflow"""
        print("[1/5] Discovering routes...")
        self.context['routes'] = discover_routes_internal(target=self.target)

        print(f"[2/5] Found {len(self.context['routes'])} routes")
        self.context['risks'] = assess_risks_internal(self.context['routes'])

        print(f"[3/5] Identified {len(self.context['risks'])} risks")
        self.context['strategy'] = self._generate_strategy()

        print("[4/5] Running tests...")
        self.context['results'] = self._run_tests()

        print("[5/5] Generating report...")
        report = self._generate_report()

        return report

    def _generate_strategy(self):
        """Generate test strategy based on risks"""
        high_risk_routes = [
            r for r in self.context['routes']
            if r.get('risk_level') == 'high'
        ]

        return {
            "focus_areas": [r['path'] for r in high_risk_routes],
            "test_types": ["security", "integration", "e2e"],
            "priority_order": self._prioritize(high_risk_routes)
        }

    def _prioritize(self, routes):
        """Prioritize routes for testing"""
        # Sort by risk + criticality
        return sorted(
            routes,
            key=lambda r: (
                r.get('risk_score', 0),
                r.get('is_critical', False)
            ),
            reverse=True
        )

    def _run_tests(self):
        """Execute tests based on strategy"""
        # Implementation here
        pass

    def _generate_report(self):
        """Generate final report"""
        # Implementation here
        pass
```

**Add CLI command**:

```python
# src/qaagent/cli.py

@app.command("auto-analyze")
def auto_analyze(
    target: str = typer.Argument(..., help="Target name"),
    out: Path = typer.Option("reports/auto-analysis", help="Output dir")
):
    """Autonomous analysis workflow"""
    from .agents.workflow_agent import WorkflowAgent

    agent = WorkflowAgent(target=target)
    report = agent.run_full_analysis()

    # Save report
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(report)

    console.print(f"[green]✓[/green] Report saved to {out}/report.md")
```

**Usage**:
```bash
qaagent auto-analyze sonicgrid
# Agent runs full workflow autonomously
```

---

### Pattern 4: Multi-Agent Collaboration

**Use Case**: Multiple specialized agents working together

**Example Architecture**:

```python
# src/qaagent/agents/agent_system.py

class SecurityAgent:
    """Specializes in security analysis"""
    def analyze(self, routes):
        return [
            risk for route in routes
            for risk in self._check_security(route)
        ]

    def _check_security(self, route):
        """Security-specific checks"""
        risks = []

        # Check authentication
        if not route.get('requires_auth'):
            risks.append({
                "type": "security",
                "severity": "high",
                "issue": "Missing authentication",
                "route": route['path']
            })

        # Check for SQL injection surfaces
        if route.get('has_user_input'):
            risks.append({
                "type": "security",
                "severity": "critical",
                "issue": "Potential SQL injection",
                "route": route['path']
            })

        return risks

class PerformanceAgent:
    """Specializes in performance analysis"""
    def analyze(self, routes):
        return [
            risk for route in routes
            for risk in self._check_performance(route)
        ]

    def _check_performance(self, route):
        """Performance-specific checks"""
        risks = []

        # Check for missing pagination
        if route.get('returns_list') and not route.get('has_pagination'):
            risks.append({
                "type": "performance",
                "severity": "medium",
                "issue": "Missing pagination",
                "route": route['path']
            })

        # Check for N+1 queries (from code analysis)
        if route.get('has_n_plus_one'):
            risks.append({
                "type": "performance",
                "severity": "high",
                "issue": "N+1 query detected",
                "route": route['path']
            })

        return risks

class TestGenerationAgent:
    """Specializes in creating tests"""
    def generate(self, risks):
        """Generate tests for high-risk areas"""
        high_priority = [r for r in risks if r['severity'] in ['critical', 'high']]

        tests = []
        for risk in high_priority:
            if risk['type'] == 'security':
                tests.append(self._generate_security_test(risk))
            elif risk['type'] == 'performance':
                tests.append(self._generate_performance_test(risk))

        return tests

    def _generate_security_test(self, risk):
        """Generate security test"""
        # Implementation here
        pass

    def _generate_performance_test(self, risk):
        """Generate performance test"""
        # Implementation here
        pass

class OrchestratorAgent:
    """Coordinates other agents"""
    def __init__(self):
        self.security = SecurityAgent()
        self.performance = PerformanceAgent()
        self.test_gen = TestGenerationAgent()

    def analyze_application(self, target):
        """Full application analysis with specialized agents"""
        # 1. Discover routes (all agents need this)
        from ..collectors.route_discovery import discover_routes_internal
        routes = discover_routes_internal(target)

        # 2. Run specialized agents in parallel
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor() as executor:
            sec_future = executor.submit(self.security.analyze, routes)
            perf_future = executor.submit(self.performance.analyze, routes)

        sec_risks = sec_future.result()
        perf_risks = perf_future.result()

        # 3. Combine findings
        all_risks = sec_risks + perf_risks

        # 4. Generate tests for critical risks
        tests = self.test_gen.generate(all_risks)

        return {
            "security": sec_risks,
            "performance": perf_risks,
            "tests": tests,
            "summary": self._create_summary(all_risks)
        }

    def _create_summary(self, risks):
        """Create executive summary"""
        by_severity = {}
        for risk in risks:
            severity = risk['severity']
            by_severity[severity] = by_severity.get(severity, 0) + 1

        return {
            "total_risks": len(risks),
            "by_severity": by_severity,
            "recommendation": self._get_recommendation(by_severity)
        }

    def _get_recommendation(self, by_severity):
        """Get high-level recommendation"""
        critical = by_severity.get('critical', 0)
        high = by_severity.get('high', 0)

        if critical > 0:
            return "URGENT: Address critical security issues immediately"
        elif high > 5:
            return "HIGH PRIORITY: Multiple high-severity issues found"
        else:
            return "NORMAL: Address issues in priority order"
```

**CLI Integration**:

```python
# src/qaagent/cli.py

@app.command("agent-analyze")
def agent_analyze(
    target: str = typer.Argument(..., help="Target name"),
    agents: str = typer.Option("all", help="Agents to run: all, security, performance")
):
    """Multi-agent analysis system"""
    from .agents.agent_system import OrchestratorAgent

    orchestrator = OrchestratorAgent()
    results = orchestrator.analyze_application(target)

    # Display results
    console.print("\n[bold]Security Findings:[/bold]")
    for risk in results['security']:
        console.print(f"  [{risk['severity']}] {risk['issue']} - {risk['route']}")

    console.print("\n[bold]Performance Findings:[/bold]")
    for risk in results['performance']:
        console.print(f"  [{risk['severity']}] {risk['issue']} - {risk['route']}")

    console.print(f"\n[bold]Summary:[/bold] {results['summary']['recommendation']}")
```

---

## Examples and Patterns

### MCP Best Practices from Codebase

#### 1. Reuse Internal Functions

```python
# src/qaagent/mcp_server.py:87-91

@mcp.tool()
def discover_routes(args: DiscoverRoutesArgs):
    """Discover API routes from OpenAPI spec or source code"""
    # Good: Calls internal function, doesn't duplicate logic
    routes = discover_routes_internal(
        target=args.target,
        openapi_path=args.openapi,
        source_path=args.source
    )
    return {"routes": [route.to_dict() for route in routes]}
```

#### 2. Use Pydantic for Type Safety

```python
# src/qaagent/mcp_server.py:32-42

class SchemathesisArgs(BaseModel):
    """Type-safe arguments with validation"""
    openapi: str | None = None
    base_url: str | None = None
    outdir: str = "reports/schemathesis"
    auth_header: str | None = None
    auth_token_env: str | None = None
    auth_prefix: str = "Bearer "
    timeout: float | None = None
    tag: list[str] | None = None
    operation_id: list[str] | None = None
    endpoint_pattern: str | None = None
```

#### 3. Graceful Error Handling

```python
# src/qaagent/mcp_server.py:97-102

if not routes_list and not routes_file:
    return {
        "error": "Either routes_list or routes_file must be provided",
        "routes": [],
        "risks": []
    }
```

#### 4. Flexible Input Methods

```python
# Multiple ways to provide input
def assess_risks(args: AssessRisksArgs):
    # Option 1: Inline routes list
    if args.routes_list:
        routes = args.routes_list

    # Option 2: Routes from file
    elif args.routes_file:
        routes = json.loads(Path(args.routes_file).read_text())

    # Option 3: Discover routes automatically
    else:
        routes = discover_routes_internal(target=args.target)
```

---

## Next Steps and Opportunities

### Quick Wins

1. **Add workspace management tools to MCP**
   ```python
   @mcp.tool()
   def list_targets(): ...

   @mcp.tool()
   def get_workspace_status(target: str): ...
   ```

2. **Create simple workflow agent**
   - Chain `discover_routes` → `assess_risks` → `generate_report`
   - Add as `qaagent quick-analyze` command

3. **Add batch operation tool**
   ```python
   @mcp.tool()
   def run_workflow(workflow: str, target: str):
       # Predefined workflows: "quick", "full", "api-only"
   ```

### Medium-Term Enhancements

1. **Implement MCP streaming**
   - Progress updates for long operations
   - Useful for `schemathesis_run` and `lighthouse_audit`

2. **Add MCP resources**
   - Expose reports as resources: `/reports/findings.md`
   - Expose workspace files: `/workspace/{target}/openapi.yaml`

3. **Create specialized agents**
   - SecurityAgent, PerformanceAgent, TestGenerationAgent
   - Orchestrator that coordinates them

### Long-Term Vision (Phase 2)

**Reference**: `docs/PHASE_2_AUTONOMOUS_QA_AGENT.md:1`

Build autonomous QA agent that:
- 🔍 Analyzes UI routes and API endpoints automatically
- 🧪 Generates BDD tests (Behave) and unit tests in Python
- 🛡️ Assesses security, performance, and reliability risks
- 📊 Creates detailed executive and technical reports
- 🤖 Recommends test strategies and priorities

**Target**: Agent does 80% of QA work, human reviews and approves

---

## References

### Key Files

- **MCP Server**: `src/qaagent/mcp_server.py:1`
- **MCP Tests**: `tests/integration/test_mcp_server.py:1`
- **Agent Workflow**: `docs/AGENT_WORKFLOW.md:1`
- **Autonomous Agent Vision**: `docs/PHASE_2_AUTONOMOUS_QA_AGENT.md:1`
- **Project Status**: `docs/PROJECT_STATUS.md:1`

### External Resources

- **MCP Specification**: https://modelcontextprotocol.io
- **FastMCP Library**: Python MCP implementation used in this project
- **Claude Desktop MCP**: How to connect Claude to MCP servers

---

## Summary Table

| Aspect | Status | Notes |
|--------|--------|-------|
| **MCP Server** | ✅ Production | 11 tools, well-tested |
| **MCP Client Usage** | ✅ Documented | Claude Desktop integration |
| **Internal Agents** | 📋 Planned | Phase 2 vision |
| **Multi-Agent System** | 💡 Concept | Orchestrator pattern defined |
| **Streaming Support** | ❌ Missing | Future enhancement |
| **Resource Exposure** | ❌ Missing | Future enhancement |

**Status Legend**:
- ✅ Complete and working
- 📋 Planned/documented
- 💡 Conceptual/design
- ❌ Not implemented

---

**Last Updated**: 2025-10-27
**Next Review**: When starting Phase 2 implementation
