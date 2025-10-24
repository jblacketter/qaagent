from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from .models import QAAgentProfile, TargetEntry, TargetRegistry


CONFIG_FILENAME = ".qaagent.yaml"
REGISTRY_FILENAME = "targets.yaml"


def get_qaagent_home() -> Path:
    root = Path(os.environ.get("QAAGENT_HOME", Path.home() / ".qaagent")).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_registry_path() -> Path:
    return get_qaagent_home() / REGISTRY_FILENAME


def find_config_file(start: Optional[Path] = None) -> Optional[Path]:
    current = (start or Path.cwd()).resolve()
    for ancestor in [current, *current.parents]:
        candidate = ancestor / CONFIG_FILENAME
        if candidate.exists():
            return candidate
    return None


def load_profile(path: Optional[Path] = None) -> QAAgentProfile:
    config_path = path or find_config_file()
    if not config_path or not config_path.exists():
        raise FileNotFoundError("Could not find .qaagent.yaml. Run `qaagent config init` first.")
    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    try:
        return QAAgentProfile(**data)
    except ValidationError as exc:
        raise ValueError(f"Invalid configuration in {config_path}: {exc}") from exc


def load_registry() -> TargetRegistry:
    registry_path = get_registry_path()
    if registry_path.exists():
        data = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        try:
            return TargetRegistry(**data)
        except ValidationError:
            pass
    return TargetRegistry()


def save_registry(registry: TargetRegistry) -> None:
    registry_path = get_registry_path()
    payload = registry.model_dump()
    with registry_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, sort_keys=False)


def get_active_target(registry: Optional[TargetRegistry] = None) -> Optional[TargetEntry]:
    registry = registry or load_registry()
    if registry.active and registry.active in registry.targets:
        return registry.targets[registry.active]
    return None


def load_active_profile() -> tuple[TargetEntry, QAAgentProfile]:
    registry = load_registry()
    entry = get_active_target(registry)
    if not entry:
        raise RuntimeError(
            "No active target configured. Run `qaagent targets list` to see available targets or "
            "`qaagent use <name>` to activate one."
        )
    config_path = entry.resolved_config_path()
    if config_path is None or not config_path.exists():
        config_path = find_config_file(entry.resolved_path())
    profile = load_profile(config_path)
    return entry, profile
