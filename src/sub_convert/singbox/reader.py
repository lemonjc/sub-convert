from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from sub_convert.singbox.models import SingBoxInbound, SingBoxServerConfig


@lru_cache(maxsize=64)
def load_singbox_config(path: str) -> SingBoxServerConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    return SingBoxServerConfig.model_validate(raw)


def find_user_inbounds(path: Path, username: str) -> list[SingBoxInbound]:
    config = load_singbox_config(str(path))
    return [inbound for inbound in config.inbounds if inbound.user_by_name(username)]

