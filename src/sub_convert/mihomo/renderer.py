from __future__ import annotations

import copy
import logging
from typing import Any

import yaml

from sub_convert.config.models import RenderConfig
from sub_convert.mihomo.models import MihomoProxy

logger = logging.getLogger(__name__)


def load_yaml(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def dump_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def deduplicate_proxies(proxies: list[MihomoProxy]) -> list[MihomoProxy]:
    seen: set[str] = set()
    result: list[MihomoProxy] = []

    for proxy in proxies:
        name = str(proxy.get("name") or "").strip()
        if not name:
            logger.warning("skipping proxy without name")
            continue

        candidate = name
        index = 2
        while candidate in seen:
            candidate = f"{name}-{index}"
            index += 1

        normalized = copy.deepcopy(proxy)
        if candidate != name:
            logger.warning("renaming duplicate proxy %r to %r", name, candidate)
            normalized["name"] = candidate

        seen.add(candidate)
        result.append(normalized)

    return result


def _merge_group_proxies(existing: Any, proxy_names: list[str]) -> list[str]:
    merged: list[str] = []
    if isinstance(existing, list):
        merged.extend(str(item) for item in existing)

    for name in proxy_names:
        if name not in merged:
            merged.append(name)
    return merged


def render_subscription(
    *,
    template: dict[str, Any],
    proxies: list[MihomoProxy],
    render_config: RenderConfig,
) -> str:
    document = copy.deepcopy(template)
    final_proxies = deduplicate_proxies(proxies)
    proxy_names = [str(proxy["name"]) for proxy in final_proxies]

    document["proxies"] = final_proxies
    groups = document.get("proxy-groups") or []
    if not isinstance(groups, list):
        raise ValueError("template proxy-groups must be a list")

    target_groups = set(render_config.inject_proxy_groups)
    for group in groups:
        if not isinstance(group, dict) or group.get("name") not in target_groups:
            continue
        group["proxies"] = _merge_group_proxies(group.get("proxies"), proxy_names)

    return dump_yaml(document)

