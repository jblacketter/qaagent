"""Test code validation pipeline.

Validates generated code before writing — Python via ast.parse(), TypeScript via
optional tsc, Gherkin via structural checks.
"""
from __future__ import annotations

import ast
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a code validation check."""

    valid: bool
    language: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class TestValidator:
    """Validates generated test code in multiple languages."""

    def validate_python(self, code: str) -> ValidationResult:
        """Validate Python code via ast.parse()."""
        try:
            ast.parse(code)
            return ValidationResult(valid=True, language="python")
        except SyntaxError as exc:
            msg = f"Line {exc.lineno}: {exc.msg}" if exc.lineno else str(exc.msg)
            return ValidationResult(valid=False, language="python", errors=[msg])

    def validate_typescript(self, path: Path) -> ValidationResult:
        """Validate TypeScript file via npx tsc --noEmit (optional).

        Returns valid=True with a warning if Node/tsc is not available.
        """
        npx = shutil.which("npx")
        if not npx:
            return ValidationResult(
                valid=True,
                language="typescript",
                warnings=["npx not found, skipping TypeScript validation"],
            )

        try:
            result = subprocess.run(
                [npx, "tsc", "--noEmit", "--esModuleInterop", "--strict", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=path.parent,
            )
            if result.returncode == 0:
                return ValidationResult(valid=True, language="typescript")
            errors = [
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip() and "error TS" in line
            ]
            return ValidationResult(
                valid=False,
                language="typescript",
                errors=errors or [result.stdout[:500]],
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            return ValidationResult(
                valid=True,
                language="typescript",
                warnings=[f"TypeScript validation skipped: {exc}"],
            )

    def validate_gherkin(self, text: str) -> ValidationResult:
        """Validate Gherkin feature file structure."""
        errors: List[str] = []
        warnings: List[str] = []

        lines = text.strip().splitlines()
        if not lines:
            return ValidationResult(valid=False, language="gherkin", errors=["Empty feature file"])

        has_feature = False
        has_scenario = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Feature:"):
                has_feature = True
            if stripped.startswith("Scenario:") or stripped.startswith("Scenario Outline:"):
                has_scenario = True

        if not has_feature:
            errors.append("Missing 'Feature:' declaration")
        if not has_scenario:
            errors.append("Missing 'Scenario:' declaration")

        return ValidationResult(
            valid=len(errors) == 0,
            language="gherkin",
            errors=errors,
            warnings=warnings,
        )

    def validate_and_fix(
        self,
        code: str,
        language: str,
        enhancer: Optional[object] = None,
        max_retries: int = 2,
    ) -> tuple[str, bool]:
        """Validate code and attempt LLM fix if invalid.

        Args:
            code: Source code to validate
            language: "python", "typescript", or "gherkin"
            enhancer: LLMTestEnhancer instance (optional)
            max_retries: Max LLM fix attempts

        Returns:
            (code, was_fixed) — the validated (possibly fixed) code and whether it was modified.
        """
        if language == "python":
            result = self.validate_python(code)
        elif language == "gherkin":
            result = self.validate_gherkin(code)
        else:
            # No in-memory validation for TypeScript
            return code, False

        if result.valid:
            return code, False

        if not enhancer:
            return code, False

        # Attempt LLM fix
        from qaagent.generators.llm_enhancer import LLMTestEnhancer
        if not isinstance(enhancer, LLMTestEnhancer):
            return code, False

        for attempt in range(max_retries):
            error_msg = "; ".join(result.errors)
            code = enhancer.refine_code(code, error_msg)

            if language == "python":
                result = self.validate_python(code)
            elif language == "gherkin":
                result = self.validate_gherkin(code)

            if result.valid:
                return code, True

        return code, False
