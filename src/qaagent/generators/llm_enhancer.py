"""LLM-powered test enhancement.

Generates test fragments (assertions, edge cases, test bodies) using the LLM client.
Each method has a clear template fallback — callers check llm_enabled before calling.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from qaagent.analyzers.models import Risk, Route
from qaagent.config.models import LLMSettings
from qaagent.llm import ChatMessage, LLMClient, QAAgentLLMError

logger = logging.getLogger(__name__)


class LLMTestEnhancer:
    """Uses LLMClient to generate test fragments for generators."""

    def __init__(self, llm_settings: LLMSettings) -> None:
        self.settings = llm_settings
        self._client = LLMClient(
            provider=llm_settings.provider,
            model=llm_settings.model,
        )

    def _chat(self, system: str, user: str) -> str:
        """Send a chat and return content, or raise QAAgentLLMError."""
        messages = [
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=user),
        ]
        response = self._client.chat(messages)
        return response.content.strip()

    @staticmethod
    def _format_retrieval_context(retrieval_context: Optional[List[str]]) -> str:
        """Format bounded retrieval snippets for prompt injection."""
        if not retrieval_context:
            return ""
        sections = []
        for idx, snippet in enumerate(retrieval_context[:5], start=1):
            trimmed = snippet[:1200]
            sections.append(f"[Snippet {idx}]\n{trimmed}")
        return "\n\nRepository context:\n" + "\n\n".join(sections)

    def enhance_assertions(
        self,
        route: Route,
        response_schema: Optional[Dict[str, Any]] = None,
        retrieval_context: Optional[List[str]] = None,
    ) -> List[str]:
        """Generate schema-aware assertion lines for a route's response.

        Returns a list of Python assertion strings (without leading 'assert').
        """
        schema_desc = json.dumps(response_schema, indent=2) if response_schema else "unknown"
        system = (
            "You are a QA engineer. Generate Python assertion lines for a pytest API test. "
            "Return ONLY assertion statements, one per line. No imports, no function definitions. "
            "Each line should start with 'assert'. Use 'response' as the variable name for the HTTP response object."
        )
        user = (
            f"Route: {route.method} {route.path}\n"
            f"Expected response schema:\n{schema_desc}\n\n"
            "Generate 3-5 specific assertion lines."
            f"{self._format_retrieval_context(retrieval_context)}"
        )
        try:
            content = self._chat(system, user)
            lines = [
                line.strip()
                for line in content.splitlines()
                if line.strip().startswith("assert")
            ]
            return lines if lines else self._fallback_assertions(route)
        except QAAgentLLMError:
            logger.warning("LLM assertion enhancement failed, using fallback")
            return self._fallback_assertions(route)

    def generate_edge_cases(
        self,
        route: Route,
        risks: List[Risk],
        retrieval_context: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate specific edge case inputs with expected status codes.

        Returns a list of dicts with keys: name, params, expected_status, description.
        """
        risk_desc = "\n".join(
            f"- [{r.severity.value}] {r.title}: {r.description}"
            for r in risks[:5]
        )
        system = (
            "You are a QA engineer. Generate edge case test inputs for an API endpoint. "
            "Return a JSON array of objects with keys: name (str), params (dict), expected_status (int), description (str). "
            "Return ONLY valid JSON, no markdown fences."
        )
        user = (
            f"Route: {route.method} {route.path}\n"
            f"Parameters: {json.dumps(route.params)}\n"
            f"Known risks:\n{risk_desc}\n\n"
            "Generate 3-5 edge cases."
            f"{self._format_retrieval_context(retrieval_context)}"
        )
        try:
            content = self._chat(system, user)
            # Strip markdown fences if present
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            cases = json.loads(content)
            if isinstance(cases, list) and cases:
                return cases
        except (QAAgentLLMError, json.JSONDecodeError, TypeError):
            logger.warning("LLM edge case generation failed, using fallback")
        return self._fallback_edge_cases(route)

    def generate_test_body(
        self,
        route: Route,
        test_type: str = "happy_path",
        retrieval_context: Optional[List[str]] = None,
    ) -> str:
        """Generate a complete function body for a test type.

        Returns Python code for the body of a test function (no def line).
        """
        system = (
            "You are a QA engineer writing pytest tests using httpx. "
            "Generate ONLY the function body (indented with 4 spaces). "
            "No function definition, no imports. Use 'client' as the httpx client fixture name. "
            "Use 'base_url' as a variable for the API base URL."
        )
        user = (
            f"Route: {route.method} {route.path}\n"
            f"Test type: {test_type}\n"
            f"Auth required: {route.auth_required}\n"
            "Generate the test function body."
            f"{self._format_retrieval_context(retrieval_context)}"
        )
        try:
            content = self._chat(system, user)
            # Ensure proper indentation
            lines = content.splitlines()
            return "\n".join(lines)
        except QAAgentLLMError:
            logger.warning("LLM test body generation failed, using fallback")
            return self._fallback_test_body(route, test_type)

    def refine_code(self, code: str, error_message: str) -> str:
        """Ask LLM to fix code after syntax validation fails.

        Returns the corrected code string.
        """
        system = (
            "You are a Python developer. Fix the syntax error in the following code. "
            "Return ONLY the corrected Python code, no explanations or markdown fences."
        )
        user = f"Error: {error_message}\n\nCode:\n{code}"
        try:
            content = self._chat(system, user)
            # Strip markdown fences if present
            content = re.sub(r"^```(?:python)?\s*\n?", "", content)
            content = re.sub(r"\n?```\s*$", "", content)
            return content
        except QAAgentLLMError:
            logger.warning("LLM code refinement failed, returning original code")
            return code

    def generate_step_definitions(
        self,
        route: Route,
        risk: Optional[Risk] = None,
        retrieval_context: Optional[List[str]] = None,
    ) -> List[str]:
        """Generate Behave step definition lines for a scenario.

        Returns a list of 'then' step strings.
        """
        risk_context = ""
        if risk:
            risk_context = f"Risk: [{risk.severity.value}] {risk.title} - {risk.description}\n"

        system = (
            "You are a QA engineer writing BDD test steps. "
            "Generate 'Then' steps for a Behave scenario. "
            "Return one step per line, each starting with 'the' (lowercase). "
            "Steps should be specific and testable. No 'Given' or 'When' steps."
        )
        user = (
            f"Route: {route.method} {route.path}\n"
            f"{risk_context}"
            "Generate 2-4 specific verification steps."
            f"{self._format_retrieval_context(retrieval_context)}"
        )
        try:
            content = self._chat(system, user)
            steps = [
                line.strip()
                for line in content.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            return steps if steps else self._fallback_then_steps(route)
        except QAAgentLLMError:
            logger.warning("LLM step generation failed, using fallback")
            return self._fallback_then_steps(route)

    def generate_response_assertions(
        self,
        route: Route,
        retrieval_context: Optional[List[str]] = None,
    ) -> List[str]:
        """Generate Behave 'then' steps that assert response body structure.

        Returns list of Behave step strings.
        """
        system = (
            "You are a QA engineer writing BDD test steps. "
            "Generate 'Then' steps that verify the response body structure for a REST API. "
            "Return one step per line, each starting with 'the' (lowercase). "
            "Focus on response body fields and types."
        )
        user = (
            f"Route: {route.method} {route.path}\n"
            f"Responses: {json.dumps(route.responses)}\n"
            "Generate 2-3 response body assertion steps."
            f"{self._format_retrieval_context(retrieval_context)}"
        )
        try:
            content = self._chat(system, user)
            steps = [
                line.strip()
                for line in content.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            return steps if steps else self._fallback_then_steps(route)
        except QAAgentLLMError:
            return self._fallback_then_steps(route)

    # -- Fallback methods (template-quality) --------------------------------

    @staticmethod
    def _fallback_assertions(route: Route) -> List[str]:
        status_map = {"GET": 200, "POST": 201, "PUT": 200, "PATCH": 200, "DELETE": 204}
        expected = status_map.get(route.method, 200)
        return [
            f"assert response.status_code == {expected}",
            "assert response.headers.get('content-type', '').startswith('application/json')",
        ]

    @staticmethod
    def _fallback_edge_cases(route: Route) -> List[Dict[str, Any]]:
        return [
            {"name": "negative_id", "params": {"id": -1}, "expected_status": 404, "description": "Negative ID"},
            {"name": "zero_id", "params": {"id": 0}, "expected_status": 404, "description": "Zero ID"},
            {"name": "string_id", "params": {"id": "invalid"}, "expected_status": 422, "description": "Non-numeric ID"},
        ]

    @staticmethod
    def _fallback_test_body(route: Route, test_type: str) -> str:
        method = route.method.lower()
        return (
            f'    response = client.{method}(base_url + "{route.path}")\n'
            f"    assert response.status_code < 500"
        )

    @staticmethod
    def _fallback_then_steps(route: Route) -> List[str]:
        return [
            "the response status should be 200",
            "the response should contain valid JSON",
        ]
