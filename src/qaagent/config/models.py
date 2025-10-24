from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ProjectSettings(BaseModel):
    name: str
    type: str = Field(default="generic")
    version: Optional[str] = None
    description: Optional[str] = None


class EnvironmentSettings(BaseModel):
    base_url: Optional[str] = None
    start_command: Optional[str] = None
    health_endpoint: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    notes: Optional[str] = None


class OpenAPISettings(BaseModel):
    spec_path: Optional[str] = None
    auto_generate: bool = False
    source_dir: Optional[str] = None
    generator: Optional[str] = None  # e.g. "nextjs", "fastapi"


class SuiteSettings(BaseModel):
    enabled: bool = True
    output_dir: str
    framework: Optional[str] = None

    @field_validator("output_dir", mode="before")
    @classmethod
    def _normalize_output_dir(cls, value: str) -> str:
        return value or ""


class DataSuiteSettings(SuiteSettings):
    format: str = "json"  # json|yaml|csv
    count: int = 10


class TestsSettings(BaseModel):
    output_dir: str = "tests/qaagent"
    behave: Optional[SuiteSettings] = SuiteSettings(enabled=True, output_dir="tests/qaagent/behave", framework="behave")
    unit: Optional[SuiteSettings] = SuiteSettings(enabled=True, output_dir="tests/qaagent/unit", framework="pytest")
    e2e: Optional[SuiteSettings] = SuiteSettings(enabled=False, output_dir="tests/qaagent/e2e", framework="playwright")
    data: Optional[DataSuiteSettings] = DataSuiteSettings(enabled=True, output_dir="tests/qaagent/fixtures")


class ExcludeSettings(BaseModel):
    paths: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class RiskAssessmentSettings(BaseModel):
    disable_rules: List[str] = Field(default_factory=list)
    severity_thresholds: Dict[str, List[str]] = Field(default_factory=dict)


class LLMSettings(BaseModel):
    enabled: bool = False
    provider: str = "ollama"
    model: str = "qwen2.5-coder:7b"
    fallback_to_templates: bool = True


class QAAgentProfile(BaseModel):
    project: ProjectSettings
    app: Dict[str, EnvironmentSettings] = Field(default_factory=dict)
    openapi: OpenAPISettings = Field(default_factory=OpenAPISettings)
    tests: TestsSettings = Field(default_factory=TestsSettings)
    exclude: ExcludeSettings = Field(default_factory=ExcludeSettings)
    risk_assessment: RiskAssessmentSettings = Field(default_factory=RiskAssessmentSettings)
    llm: Optional[LLMSettings] = None

    def resolve_spec_path(self, project_root: Path) -> Optional[Path]:
        if not self.openapi.spec_path:
            return None
        candidate = Path(self.openapi.spec_path)
        if not candidate.is_absolute():
            candidate = project_root / candidate
        return candidate


class TargetEntry(BaseModel):
    name: str
    path: str
    config_path: Optional[str] = None
    project_type: Optional[str] = None
    description: Optional[str] = None

    def resolved_path(self) -> Path:
        return Path(self.path).expanduser().resolve()

    def resolved_config_path(self) -> Optional[Path]:
        if not self.config_path:
            return None
        config = Path(self.config_path)
        if not config.is_absolute():
            config = self.resolved_path() / config
        return config


class TargetRegistry(BaseModel):
    active: Optional[str] = None
    targets: Dict[str, TargetEntry] = Field(default_factory=dict)
