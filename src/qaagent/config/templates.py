from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_FOLDER = Path(__file__).resolve().parent.parent / "templates" / "config"


@dataclass
class TemplateContext:
    project_name: str
    project_type: str
    base_url: str
    start_command: Optional[str] = None
    health_endpoint: str = "/health"
    spec_path: str = ".qaagent/openapi.yaml"
    source_dir: Optional[str] = None


def _ensure_environment() -> Environment:
    loader = FileSystemLoader(str(TEMPLATE_FOLDER))
    return Environment(
        loader=loader,
        autoescape=select_autoescape(disabled_extensions=("yaml.j2",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def available_templates() -> Dict[str, str]:
    env = _ensure_environment()
    mapping: Dict[str, str] = {}
    for template_name in env.list_templates(filter_func=lambda name: name.endswith(".yaml.j2")):
        key = template_name.replace(".yaml.j2", "")
        mapping[key] = template_name
    return mapping


def render_template(template_name: str, context: TemplateContext) -> str:
    env = _ensure_environment()
    mapping = available_templates()
    if template_name not in mapping:
        raise ValueError(f"Unknown template `{template_name}`. Available: {', '.join(sorted(mapping))}")
    template = env.get_template(mapping[template_name])
    return template.render(context=context)
