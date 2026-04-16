from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigBundle:
    def __init__(self, project_root: Path):
        config_dir = project_root / "config"
        self.settings = self._load_yaml(config_dir / "settings.yaml")
        self.equipment_keywords = self._load_yaml(config_dir / "equipment_keywords.yaml")
        self.room_type_keywords = self._load_yaml(config_dir / "room_type_keywords.yaml")
        self.page_type_rules = self._load_yaml(config_dir / "page_type_rules.yaml")

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
