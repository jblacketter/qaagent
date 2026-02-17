"""API routes for LLM agent analysis (Phase 20)."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("qaagent.api.agent")

router = APIRouter(tags=["agent"])

# ---------------------------------------------------------------------------
# In-memory stores (keyed by repo_id, never persisted to disk)
# ---------------------------------------------------------------------------

@dataclass
class _AgentConfig:
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5-20250929"
    api_key: str = ""


@dataclass
class _UsageAccumulator:
    requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, usage: Optional[Dict[str, Any]]) -> None:
        self.requests += 1
        if usage:
            self.prompt_tokens += usage.get("prompt_tokens") or 0
            self.completion_tokens += usage.get("completion_tokens") or 0
            self.total_tokens += usage.get("total_tokens") or 0


# Module-level stores — memory only, lost on restart
_configs: Dict[str, _AgentConfig] = {}
_usage: Dict[str, _UsageAccumulator] = {}

# Approximate cost per 1M tokens (input, output) in USD
_PRICE_TABLE: Dict[str, tuple[float, float]] = {
    "claude-sonnet-4-5-20250929": (3.0, 15.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-opus-4-6": (15.0, 75.0),
    "claude-haiku-4-5": (0.80, 4.0),
    "gpt-4o": (2.50, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.0, 30.0),
}

PROMPT_CHAR_LIMIT = 50_000
LLM_TIMEOUT_SECONDS = 300


def _mask_key(key: str) -> str:
    """Mask an API key: show first 4 + last 4 chars, rest ***."""
    if len(key) <= 8:
        return "***"
    return key[:4] + "***" + key[-4:]


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost in USD from token counts."""
    # Try exact match, then prefix match
    prices = _PRICE_TABLE.get(model)
    if not prices:
        for key, val in _PRICE_TABLE.items():
            if key in model or model in key:
                prices = val
                break
    if not prices:
        return 0.0
    input_cost = (prompt_tokens / 1_000_000) * prices[0]
    output_cost = (completion_tokens / 1_000_000) * prices[1]
    return round(input_cost + output_cost, 6)


def _require_repo_id(repo_id: Optional[str]) -> str:
    if not repo_id:
        raise HTTPException(status_code=400, detail="repo_id query parameter is required")
    from qaagent.api.routes.repositories import repositories
    if repo_id not in repositories:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found")
    return repo_id


def _effective_config(repo_id: str) -> _AgentConfig:
    """Return the in-memory config, falling back to ANTHROPIC_API_KEY env var."""
    cfg = _configs.get(repo_id)
    if cfg and cfg.api_key:
        return cfg
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key:
        return _AgentConfig(
            provider=(cfg.provider if cfg else "anthropic"),
            model=(cfg.model if cfg else "claude-sonnet-4-5-20250929"),
            api_key=env_key,
        )
    return cfg or _AgentConfig()


# ---------------------------------------------------------------------------
# Config endpoints
# ---------------------------------------------------------------------------

class AgentConfigRequest(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5-20250929"
    api_key: str = ""


class AgentConfigResponse(BaseModel):
    provider: str
    model: str
    api_key_masked: str
    configured: bool


@router.post("/agent/config")
def save_agent_config(
    body: AgentConfigRequest,
    repo_id: Optional[str] = Query(None),
) -> AgentConfigResponse:
    """Save agent configuration (memory-only)."""
    rid = _require_repo_id(repo_id)
    _configs[rid] = _AgentConfig(
        provider=body.provider,
        model=body.model,
        api_key=body.api_key,
    )
    return AgentConfigResponse(
        provider=body.provider,
        model=body.model,
        api_key_masked=_mask_key(body.api_key) if body.api_key else "",
        configured=bool(body.api_key),
    )


@router.get("/agent/config")
def get_agent_config(
    repo_id: Optional[str] = Query(None),
) -> AgentConfigResponse:
    """Get current agent configuration (API key masked)."""
    rid = _require_repo_id(repo_id)
    cfg = _effective_config(rid)
    return AgentConfigResponse(
        provider=cfg.provider,
        model=cfg.model,
        api_key_masked=_mask_key(cfg.api_key) if cfg.api_key else "",
        configured=bool(cfg.api_key),
    )


@router.delete("/agent/config")
def delete_agent_config(
    repo_id: Optional[str] = Query(None),
) -> dict[str, str]:
    """Clear agent configuration."""
    rid = _require_repo_id(repo_id)
    _configs.pop(rid, None)
    return {"status": "deleted", "repo_id": rid}


# ---------------------------------------------------------------------------
# Analyze endpoint
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    pass  # No body params needed — config comes from stored config


class AnalyzeResponse(BaseModel):
    content: str
    model: str = ""
    usage: Dict[str, Any] = {}


def _build_prompt(doc_data: dict) -> str:
    """Build a bounded prompt from documentation data."""
    parts: list[str] = []

    parts.append(f"Application: {doc_data.get('app_name', 'Unknown')}")
    parts.append(f"Summary: {doc_data.get('summary', '')}")
    parts.append(f"Total routes: {doc_data.get('total_routes', 0)}")

    if doc_data.get("tech_stack"):
        parts.append(f"Tech stack: {', '.join(doc_data['tech_stack'])}")

    if doc_data.get("app_overview"):
        parts.append(f"\nApp Overview:\n{doc_data['app_overview']}")

    # Features (truncate if needed)
    features = doc_data.get("features", [])
    if features:
        parts.append(f"\nFeatures ({len(features)}):")
        for f in features:
            entry = f"- {f.get('name', '?')}: {f.get('description', '')[:200]}"
            parts.append(entry)

    # Integrations
    integrations = doc_data.get("integrations", [])
    if integrations:
        parts.append(f"\nIntegrations ({len(integrations)}):")
        for i in integrations:
            parts.append(f"- {i.get('name', '?')} ({i.get('type', '?')}): {i.get('description', '')[:150]}")

    # User roles
    roles = doc_data.get("user_roles", [])
    if roles:
        parts.append(f"\nUser Roles ({len(roles)}):")
        for r in roles:
            parts.append(f"- {r.get('name', '?')}: {r.get('description', '')} [permissions: {', '.join(r.get('permissions', []))}]")

    # User journeys
    journeys = doc_data.get("user_journeys", [])
    if journeys:
        parts.append(f"\nUser Journeys ({len(journeys)}):")
        for j in journeys:
            steps = ", ".join(s.get("action", "") for s in j.get("steps", []))
            parts.append(f"- {j.get('name', '?')} ({j.get('priority', 'medium')}): {steps}")

    # CUJs
    cujs = doc_data.get("discovered_cujs", [])
    if cujs:
        parts.append(f"\nCritical User Journeys ({len(cujs)}):")
        for c in cujs:
            parts.append(f"- {c.get('name', '?')}: {c.get('description', '')[:150]}")

    prompt = "\n".join(parts)

    # Enforce character limit
    if len(prompt) > PROMPT_CHAR_LIMIT:
        prompt = prompt[:PROMPT_CHAR_LIMIT] + "\n\n[... truncated to stay within token budget]"

    return prompt


def _parse_sections(markdown: str) -> list:
    """Parse LLM markdown into sections by splitting on ## headings.

    Resilient: if there are no ## headings, returns a single section
    with title "Documentation" containing the full text.
    """
    from qaagent.doc.models import DocSection

    if not markdown.strip():
        return []

    # Split on lines that start with exactly two # (not ### or deeper)
    parts = re.split(r"^(## .+)$", markdown, flags=re.MULTILINE)

    sections: list[DocSection] = []

    # Handle preamble (text before any ## heading)
    preamble = parts[0].strip()
    if preamble:
        sections.append(DocSection(title="Introduction", content=preamble))

    # Pair up headings with their content
    i = 1
    while i < len(parts) - 1:
        heading_line = parts[i]
        content = parts[i + 1]
        title = heading_line.lstrip("#").strip()
        body = content.strip()
        if title:
            sections.append(DocSection(title=title, content=body))
        i += 2

    # Fallback: if no sections were parsed, wrap the entire text
    if not sections and markdown.strip():
        sections.append(DocSection(title="Documentation", content=markdown.strip()))

    return sections


@router.post("/agent/analyze")
def analyze_with_agent(
    repo_id: Optional[str] = Query(None),
) -> AnalyzeResponse:
    """Send project data to an LLM for enhanced product documentation."""
    rid = _require_repo_id(repo_id)

    # Check config exists (with env-var fallback)
    cfg = _effective_config(rid)
    if not cfg.api_key:
        raise HTTPException(
            status_code=400,
            detail="Agent not configured. Save your API key first via POST /api/agent/config.",
        )

    # Load documentation
    from pathlib import Path
    from qaagent.api.routes.repositories import repositories
    from qaagent.doc.generator import load_documentation, save_documentation
    from qaagent.doc.models import AgentAnalysis

    repo = repositories[rid]
    project_root = Path(repo.path)
    doc = load_documentation(project_root)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail="No documentation found for this repository. Run analysis first.",
        )

    # Build prompt
    doc_data = doc.model_dump()
    user_prompt = _build_prompt(doc_data)

    system_prompt = (
        "You are a senior product documentation writer. Based on the project analysis data provided, "
        "produce enhanced product documentation in Markdown format.\n\n"
        "Structure your output using EXACTLY these H2 section headings, in this order:\n\n"
        "## Product Overview\n"
        "What the application is, who it is for, and what problems it solves. Write 2-3 paragraphs.\n\n"
        "## Architecture & Tech Stack\n"
        "High-level system structure, key technologies, and how components relate.\n\n"
        "## Features\n"
        "Each feature as a subsection (### Feature Name) with a concise description, key capabilities, "
        "and user-facing behavior. Focus on what users can do, not implementation details.\n\n"
        "## User Roles & Permissions\n"
        "A Markdown table with columns: Role | Description | Key Permissions. "
        "One row per role.\n\n"
        "## User Journeys\n"
        "Step-by-step workflows. Use ### for each journey name, then a numbered list of steps. "
        "Include the actor (role) performing each journey.\n\n"
        "## Integrations\n"
        "External services and how they connect. Use a table or bullet list with: "
        "Name | Type | Purpose.\n\n"
        "## Configuration & Getting Started\n"
        "Setup guidance, environment variables needed, and first-run instructions.\n\n"
        "## Gaps & Recommendations\n"
        "What documentation is missing, what areas need more detail, and actionable suggestions.\n\n"
        "Formatting rules:\n"
        "- Use short, descriptive headings\n"
        "- Keep paragraphs to 3-7 lines\n"
        "- Use Markdown tables for structured data (roles, integrations)\n"
        "- Use numbered or bulleted lists when there are 3+ items\n"
        "- Maintain strict H2 -> H3 heading hierarchy (never skip to H4)\n"
        "- Write in clear, professional tone suitable for product documentation"
    )

    # Call LLM
    from qaagent.llm import LLMClient, ChatMessage, QAAgentLLMError

    client = LLMClient(
        provider=cfg.provider,
        model=cfg.model,
        api_key=cfg.api_key,
    )

    # Ensure usage accumulator exists
    if rid not in _usage:
        _usage[rid] = _UsageAccumulator()

    try:
        response = client.chat(
            [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt),
            ],
            timeout=LLM_TIMEOUT_SECONDS,
        )
    except QAAgentLLMError as exc:
        # Count the request even on failure (no usage data available)
        _usage[rid].requests += 1
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}")

    # Accumulate usage
    _usage[rid].add(response.usage)

    # Parse sections and auto-save agent analysis to appdoc.json
    sections = _parse_sections(response.content)
    doc.agent_analysis = AgentAnalysis(
        enhanced_markdown=response.content,
        sections=sections,
        model_used=response.model or cfg.model,
        generated_at=datetime.now().isoformat(),
    )
    try:
        save_documentation(doc, project_root)
    except Exception:
        logger.warning("Failed to persist agent analysis to appdoc.json", exc_info=True)

    return AnalyzeResponse(
        content=response.content,
        model=response.model,
        usage=response.usage or {},
    )


# ---------------------------------------------------------------------------
# Usage endpoints
# ---------------------------------------------------------------------------

class UsageResponse(BaseModel):
    repo_id: str
    requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


@router.get("/agent/usage")
def get_agent_usage(
    repo_id: Optional[str] = Query(None),
) -> UsageResponse:
    """Get cumulative token usage for a repository."""
    rid = _require_repo_id(repo_id)
    acc = _usage.get(rid, _UsageAccumulator())
    # Determine model for cost estimation
    cfg = _configs.get(rid)
    model = cfg.model if cfg else ""
    cost = _estimate_cost(model, acc.prompt_tokens, acc.completion_tokens)
    return UsageResponse(
        repo_id=rid,
        requests=acc.requests,
        prompt_tokens=acc.prompt_tokens,
        completion_tokens=acc.completion_tokens,
        total_tokens=acc.total_tokens,
        estimated_cost_usd=cost,
    )


@router.delete("/agent/usage")
def reset_agent_usage(
    repo_id: Optional[str] = Query(None),
) -> dict[str, str]:
    """Reset token usage counters for a repository."""
    rid = _require_repo_id(repo_id)
    _usage.pop(rid, None)
    return {"status": "reset", "repo_id": rid}
