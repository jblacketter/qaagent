"""Base classes for test runners.

Provides TestCase, TestResult models and TestRunner ABC.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from qaagent.config.models import RunSettings, SuiteSettings


class TestCase(BaseModel):
    """A single test case result."""
    name: str
    classname: Optional[str] = None
    status: Literal["passed", "failed", "error", "skipped"] = "passed"
    duration: float = 0.0
    output: Optional[str] = None
    error_message: Optional[str] = None
    route: Optional[str] = None


class TestResult(BaseModel):
    """Aggregated result from running a test suite."""
    suite_name: str
    runner: str
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration: float = 0.0
    cases: List[TestCase] = Field(default_factory=list)
    artifacts: Dict[str, str] = Field(default_factory=dict)
    returncode: int = 0

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errors + self.skipped

    @property
    def success(self) -> bool:
        return self.failed == 0 and self.errors == 0


class TestRunner(ABC):
    """Abstract base for test suite runners."""

    runner_name: str = "base"

    def __init__(
        self,
        suite_settings: Optional[SuiteSettings] = None,
        run_settings: Optional[RunSettings] = None,
        base_url: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> None:
        self.suite_settings = suite_settings
        self.run_settings = run_settings or RunSettings()
        self.base_url = base_url or ""
        self.output_dir = output_dir or Path("reports")

    @abstractmethod
    def run(self, test_path: Path, **kwargs: Any) -> TestResult:
        """Execute tests and return structured results."""
        ...

    @abstractmethod
    def parse_results(self, junit_path: Path, stdout: str = "") -> TestResult:
        """Parse JUnit XML + stdout into a TestResult."""
        ...

    def _map_test_to_route(self, test_name: str) -> Optional[str]:
        """Attempt to map a test name to an API route.

        Convention: test_get_pets_pet_id_success -> GET /pets/{pet_id}
        Detects param patterns like `_id`, `_pk`, `_slug`, `_uuid` and
        merges them with the preceding segment into `{resource_id}`.
        """
        name = test_name.lower()
        for prefix in ("test_",):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break

        # Try to extract method
        methods = ("get", "post", "put", "patch", "delete")
        method = None
        for m in methods:
            if name.startswith(m + "_"):
                method = m.upper()
                name = name[len(m) + 1:]
                break

        if not method:
            return None

        # Remove suffix (success, invalid_data, etc.)
        for suffix in ("_success", "_invalid_data", "_invalid_params", "_error"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break

        # Convert underscores to path segments, detecting param patterns
        tokens = name.split("_")
        segments: list[str] = []
        param_suffixes = {"id", "pk", "slug", "uuid"}
        i = 0
        while i < len(tokens):
            # Check if next token is a param suffix (e.g., "pet" + "id" -> {pet_id})
            if i + 1 < len(tokens) and tokens[i + 1] in param_suffixes:
                segments.append("{" + tokens[i] + "_" + tokens[i + 1] + "}")
                i += 2
            else:
                segments.append(tokens[i])
                i += 1

        path = "/" + "/".join(segments)
        return f"{method} {path}"
