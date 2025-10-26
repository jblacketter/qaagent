# Prompt Guidelines — AI Summary Generation

**Version:** 1.0.0-mvp
**Last Updated:** 2025-10-24
**Audience:** Developers implementing AI summarization (Sprint 3)

---

## Overview

This document defines prompt templates and guidelines for generating AI-powered summaries of qaagent analysis results. All prompts must:

1. **Ground outputs in evidence** - cite specific evidence IDs
2. **Be deterministic** - same inputs → same outputs (low temperature)
3. **Respect privacy** - never include raw code or secrets
4. **Provide actionable insights** - not just describe, but recommend

---

## LLM Configuration

### Model Selection

**Default (Local):**
```python
{
    "provider": "ollama",
    "model": "qwen2.5:7b",
    "temperature": 0.1,  # Low for consistency
    "top_p": 0.9,
    "max_tokens": 2048
}
```

**Alternative Models:**
- `qwen2.5:14b` - Higher quality, slower
- `llama3.1:8b` - Good balance
- `mistral:7b` - Fast, concise

**External (if opted-in):**
```python
{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.2,
    "max_tokens": 2048
}
```

### Temperature Rationale

- **0.0-0.2**: Deterministic, factual - use for evidence summaries
- **0.3-0.5**: Slightly creative - use for recommendations
- **0.6+**: Too variable - avoid for qaagent

---

## Prompt Templates

### Template 1: Executive Summary

**Purpose:** High-level overview of analysis results

**Input Variables:**
- `run_id` - Unique run identifier
- `target_name` - Project name
- `total_findings` - Count of all findings
- `risk_distribution` - Dict of {band: count}
- `top_risks` - List of top 3-5 risk objects with evidence_ids
- `coverage_summary` - Overall coverage percentage

**Template:**
```
You are a technical quality analyst reviewing code analysis results.

Analyze the following qaagent scan results and provide an executive summary.

## Analysis Details
- Run ID: {{run_id}}
- Target: {{target_name}}
- Timestamp: {{created_at}}

## Findings Overview
- Total findings: {{total_findings}}
- Risk distribution: {{risk_distribution}}

## Top Risks
{{#each top_risks}}
- **{{band}} - {{category}}**: {{summary}} ({{risk_id}})
  - Score: {{score}}/100, Confidence: {{confidence}}
  - Evidence: {{related_evidence}}
{{/each}}

## Coverage
- Overall coverage: {{coverage_summary}}%

## Your Task
Provide a 3-4 paragraph executive summary that:
1. Summarizes the overall quality posture
2. Highlights the most critical issues (reference evidence IDs)
3. Recommends immediate next steps
4. Cites ALL evidence IDs using the format (EVIDENCE_ID)

Requirements:
- Use clear, non-technical language for executives
- Every claim MUST cite an evidence ID
- Be concise but specific
- Output format: Markdown
```

**Example Output:**
```markdown
# Executive Summary

The sonicgrid project analysis (20251024_193012Z) reveals **moderate risk** with 202 total findings across security, coverage, and code quality dimensions.

**Critical Issues:** Two P1 risks require immediate attention. The authentication module (RSK-20251024-0003) shows high churn combined with security vulnerabilities, specifically hard-coded secrets detected by bandit (FND-20251024-0007). Additionally, the dataset upload pipeline (RSK-20251024-0005) operates below the 70% coverage target at only 58% (COV-20251024-0018), increasing regression risk.

**Recommendations:**
1. Address authentication security findings immediately (FND-20251024-0007, FND-20251024-0009)
2. Increase test coverage for dataset upload flow (COV-20251024-0018)
3. Review high-churn modules for refactoring opportunities (CHN-20251024-0002, CHN-20251024-0011)

Overall, the codebase is maintainable with targeted improvements needed in security and test coverage.
```

---

### Template 2: Risk Deep-Dive

**Purpose:** Detailed analysis of a specific risk

**Input Variables:**
- `risk` - Complete RiskScore object
- `related_findings` - List of Finding objects referenced by evidence_ids
- `cuj_details` - CUJ information if linked

**Template:**
```
You are a security and quality engineer investigating a specific risk.

## Risk Details
- ID: {{risk.risk_id}}
- Category: {{risk.category}}
- Score: {{risk.score}}/100
- Band: {{risk.band}}
- Confidence: {{risk.confidence}}
- Summary: {{risk.summary}}

## Related Evidence
{{#each related_findings}}
- {{evidence_id}}: {{tool}} - {{message}} ({{file}}:{{line}})
{{/each}}

## Linked User Journeys
{{#each cuj_details}}
- {{id}}: {{name}}
{{/each}}

## Your Task
Provide a detailed risk analysis including:
1. Root cause analysis based on evidence
2. Potential impact on user journeys
3. Specific remediation steps (with file paths and line numbers from evidence)
4. Prevention recommendations

Cite every piece of evidence used (EVIDENCE_ID format).
```

---

### Template 3: Test Gap Analysis

**Purpose:** Identify missing test coverage

**Input Variables:**
- `coverage_by_cuj` - Dict of {cuj_id: coverage_data}
- `cujs_below_target` - List of CUJs not meeting target
- `test_inventory` - List of existing tests

**Template:**
```
You are a QA engineer analyzing test coverage gaps.

## Coverage Summary
{{#each coverage_by_cuj}}
- **{{cuj_id}}**: {{actual}}% (target: {{target}}%)
  - Components: {{components}}
  - Evidence: {{coverage_id}}
{{/each}}

## Existing Tests
Total: {{test_count}}
- Unit: {{unit_count}}
- Integration: {{integration_count}}
- E2E: {{e2e_count}}

## Your Task
For each CUJ below target, recommend specific tests to add:
1. Test type (unit/integration/e2e)
2. Test scenario description
3. Which components to focus on
4. Expected coverage improvement

Reference coverage evidence IDs (COV-...) in recommendations.
```

---

## Citation Requirements

### Mandatory Citation Format

**Evidence IDs must appear** in one of these formats:

1. **Inline reference:** `(FND-20251024-0001)`
2. **Markdown link:** `[FND-20251024-0001](#findings)`
3. **List item:** `- Evidence: FND-20251024-0001`

### Citation Validation

Post-generation validation regex:
```python
import re

EVIDENCE_ID_PATTERN = r'\b(FND|RSK|COV|TST|CHN|API)-\d{8}-\d{4}\b'

def validate_citations(summary: str, expected_evidence_ids: set[str]) -> bool:
    """
    Ensure all expected evidence IDs are cited in summary.
    """
    found_ids = set(re.findall(EVIDENCE_ID_PATTERN, summary))
    missing = expected_evidence_ids - found_ids

    if missing:
        logger.warning(f"Summary missing citations: {missing}")
        return False
    return True
```

**Enforcement:**
- If validation fails, summary is flagged with warning banner
- Option to retry with stricter prompt
- User can override but sees confidence penalty

---

## System Prompts

### Base System Prompt (All Templates)

```
You are qaagent AI, a technical quality analyst assistant.

Your role is to help developers understand code quality analysis results by:
- Summarizing findings from static analysis tools
- Identifying patterns and priorities
- Recommending specific, actionable improvements

**Critical Rules:**
1. ALWAYS cite evidence IDs (format: FND-YYYYMMDD-####) for every claim
2. Never invent findings - only reference provided evidence
3. Use clear, technical language appropriate for software engineers
4. Be concise but specific (prefer "fix line 57" over "fix the code")
5. Output valid Markdown format

**Privacy:**
- Never output raw source code
- Only reference file paths and line numbers from evidence
- Redact any secrets or credentials if seen in evidence metadata
```

### Tone Modifiers

**For Executives (non-technical):**
```
Use business-friendly language. Avoid jargon like "cyclomatic complexity" - say "code complexity" instead. Focus on risk and business impact.
```

**For Developers (technical):**
```
Use precise technical terms. Reference specific tools (flake8, bandit) and their rule codes (e.g., B101). Developers want exact locations and root causes.
```

---

## Variable Injection

### Safe Injection (No Code Execution)

Use Mustache/Handlebars-style templates:

```python
from jinja2 import Template, Environment, select_autoescape

# Safe: auto-escaping enabled
env = Environment(autoescape=select_autoescape(['html', 'xml']))
template = env.from_string(PROMPT_TEMPLATE)

rendered = template.render(
    run_id=run.run_id,
    total_findings=run.counts.findings,
    top_risks=[r.to_dict() for r in run.top_risks]
)
```

**Never** use string interpolation with user-controlled data:
```python
# UNSAFE - avoid this
prompt = f"Analyze {user_input}"  # Could be injection attack
```

---

## Output Post-Processing

### Markdown Cleanup

```python
def clean_summary(raw_output: str) -> str:
    """
    Clean up LLM output for consistency.
    """
    # Remove thinking/reasoning sections
    output = re.sub(r'<thinking>.*?</thinking>', '', raw_output, flags=re.DOTALL)

    # Normalize evidence ID links
    output = re.sub(
        r'\b(FND|RSK|COV|TST|CHN|API)-(\d{8})-(\d{4})\b',
        r'[\1-\2-\3](#\1-\2-\3)',  # Convert to markdown links
        output
    )

    # Remove empty sections
    output = re.sub(r'\n\n\n+', '\n\n', output)

    return output.strip()
```

### Confidence Scoring

```python
def score_summary_quality(summary: str, evidence_ids: set[str]) -> float:
    """
    Heuristic quality score for summary.
    """
    score = 1.0

    # Penalty for missing citations
    cited = len(re.findall(EVIDENCE_ID_PATTERN, summary))
    expected = len(evidence_ids)
    if cited < expected:
        score *= (cited / expected)

    # Penalty for too short (likely hallucination)
    if len(summary) < 200:
        score *= 0.5

    # Penalty for too long (verbose)
    if len(summary) > 4000:
        score *= 0.8

    return score
```

---

## Testing Prompts

### Unit Test Structure

```python
def test_executive_summary_template():
    """Test prompt generates valid summary with citations."""

    # Mock LLM response
    mock_response = """
    # Executive Summary

    Analysis found 5 critical issues (RSK-001) including
    security vulnerabilities (FND-001, FND-002).
    """

    # Validate
    assert validate_citations(mock_response, {"RSK-001", "FND-001", "FND-002"})
    assert "# Executive Summary" in mock_response
```

### Regression Tests

Maintain golden examples:
```
tests/fixtures/prompt_outputs/
  executive_summary_example1.md
  risk_deepdive_example1.md
```

Compare new outputs against baseline for consistency.

---

## Best Practices

### DO ✅

- Keep prompts under 4000 tokens when possible
- Use structured output format (Markdown headings, lists)
- Provide few-shot examples in prompt for complex tasks
- Validate outputs programmatically
- Log all LLM interactions for debugging

### DON'T ❌

- Send raw code contents in prompts (only metadata)
- Use high temperature (>0.3) for factual tasks
- Trust LLM outputs blindly - always validate
- Include secrets or credentials in prompt context
- Generate new evidence IDs (only reference existing ones)

---

## Prompt Catalog

**Sprint 3 Minimum:**
1. Executive Summary (implemented)
2. Risk Deep-Dive (implemented)
3. Test Gap Analysis (implemented)

**Post-MVP:**
4. Trend Analysis (compare runs over time)
5. Security Posture Report
6. Refactoring Recommendations
7. CUJ Health Check

---

## Example Workflow

```python
from qaagent.llm import OllamaClient
from qaagent.prompts import EXECUTIVE_SUMMARY_TEMPLATE

# Load analysis results
run = load_run("20251024_193012Z")

# Prepare prompt context
context = {
    "run_id": run.run_id,
    "target_name": run.target.name,
    "total_findings": run.counts.findings,
    "top_risks": run.get_top_risks(limit=5),
    "coverage_summary": run.get_coverage_summary(),
}

# Render prompt
prompt = EXECUTIVE_SUMMARY_TEMPLATE.render(context)

# Call LLM
client = OllamaClient(model="qwen2.5:7b", temperature=0.1)
raw_summary = client.generate(prompt)

# Post-process
summary = clean_summary(raw_summary)

# Validate
evidence_ids = {r.risk_id for r in context["top_risks"]}
if not validate_citations(summary, evidence_ids):
    logger.warning("Summary failed citation validation")

# Save
run.save_summary(summary)
```

---

**Status:** Ready for Sprint 3 implementation
**Next Steps:** Implement OllamaClient wrapper and first template

