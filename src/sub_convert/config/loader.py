from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sub_convert.config.models import AppConfig


def _resolve_path(root: Path, path: Path | None) -> Path | None:
    if path is None or path.is_absolute():
        return path
    return (root / path).resolve()


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    config_path = Path(path).expanduser().resolve()
    with config_path.open("r", encoding="utf-8") as file:
        raw: dict[str, Any] = yaml.safe_load(file) or {}

    root = config_path.parent
    if "template" not in raw and "template_path" in raw:
        raw["template"] = {"file_path": raw.pop("template_path")}
    if raw.get("template", {}).get("file_path"):
        raw["template"]["file_path"] = _resolve_path(root, Path(raw["template"]["file_path"]))
    for server in raw.get("servers", []):
        server["config_path"] = _resolve_path(root, Path(server["config_path"]))
    for user in raw.get("users", []):
        for remote in user.get("remote_subscriptions", []):
            if remote.get("file_path"):
                remote["file_path"] = _resolve_path(root, Path(remote["file_path"]))

    return AppConfig.model_validate(raw)
