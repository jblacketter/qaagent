from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, Optional

from .loader import CONFIG_FILENAME, find_config_file, load_registry, save_registry
from .models import TargetEntry, TargetRegistry


class TargetManager:
    """Manage registered QA Agent targets."""

    def __init__(self, registry: Optional[TargetRegistry] = None) -> None:
        self._registry = registry or load_registry()

    @property
    def registry(self) -> TargetRegistry:
        return self._registry

    def list_targets(self) -> Iterable[TargetEntry]:
        return self.registry.targets.values()

    def get(self, name: str) -> Optional[TargetEntry]:
        return self.registry.targets.get(name)

    def add_target(self, name: str, path: str, project_type: Optional[str] = None) -> TargetEntry:
        name = name.strip()
        if not name:
            raise ValueError("Target name may not be empty.")
        if name in self.registry.targets:
            raise ValueError(f"Target `{name}` is already registered.")

        resolved_path = Path(path).expanduser().resolve()
        if not resolved_path.exists():
            raise FileNotFoundError(f"Target path does not exist: {resolved_path}")

        config_path = find_config_file(resolved_path)
        entry = TargetEntry(
            name=name,
            path=str(resolved_path),
            config_path=str(config_path.relative_to(resolved_path)) if config_path else None,
            project_type=project_type,
        )
        self.registry.targets[name] = entry
        save_registry(self.registry)
        return entry

    def remove_target(self, name: str) -> None:
        if name not in self.registry.targets:
            raise ValueError(f"Target `{name}` is not registered.")
        self.registry.targets.pop(name)
        if self.registry.active == name:
            self.registry.active = None
        save_registry(self.registry)

    def set_active(self, name: str) -> TargetEntry:
        if name not in self.registry.targets:
            raise ValueError(f"Target `{name}` is not registered.")
        self.registry.active = name
        save_registry(self.registry)
        return self.registry.targets[name]

    def get_active(self) -> Optional[TargetEntry]:
        if self.registry.active:
            return self.registry.targets.get(self.registry.active)
        return None

    def refresh(self) -> None:
        """Reload registry from disk."""
        self._registry = load_registry()
