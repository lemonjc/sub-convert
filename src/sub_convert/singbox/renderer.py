from __future__ import annotations

import copy
import json
import logging
from typing import Any

from sub_convert.converters.base import ProxyNode

logger = logging.getLogger(__name__)


def deduplicate_outbounds(
    template_outbounds: list[dict[str, Any]],
    outbounds: list[ProxyNode],
) -> list[ProxyNode]:
    seen = {
        str(outbound["tag"])
        for outbound in template_outbounds
        if isinstance(outbound, dict) and outbound.get("tag")
    }
    result: list[ProxyNode] = []

    for outbound in outbounds:
        tag = str(outbound.get("tag") or "").strip()
        if not tag:
            logger.warning("skipping outbound without tag")
            continue

        candidate = tag
        index = 2
        while candidate in seen:
            candidate = f"{tag}-{index}"
            index += 1

        normalized = copy.deepcopy(outbound)
        if candidate != tag:
            logger.warning("renaming duplicate outbound %r to %r", tag, candidate)
            normalized["tag"] = candidate
        seen.add(candidate)
        result.append(normalized)

    return result


def _merge_outbound_tags(existing: Any, outbound_tags: list[str]) -> list[str]:
    merged = [str(item) for item in existing] if isinstance(existing, list) else []
    for tag in outbound_tags:
        if tag not in merged:
            merged.append(tag)
    return merged


def render_subscription(
    *,
    template: dict[str, Any],
    outbounds: list[ProxyNode],
    inject_group_tags: list[str] | None = None,
) -> str:
    document = copy.deepcopy(template)
    template_outbounds = document.get("outbounds") or []
    if not isinstance(template_outbounds, list):
        raise ValueError("template outbounds must be a list")

    final_outbounds = deduplicate_outbounds(template_outbounds, outbounds)
    outbound_tags = [str(outbound["tag"]) for outbound in final_outbounds]
    document["outbounds"] = [*template_outbounds, *final_outbounds]

    target_tags = set(inject_group_tags) if inject_group_tags is not None else None
    for outbound in template_outbounds:
        if not isinstance(outbound, dict) or outbound.get("type") not in {"selector", "urltest"}:
            continue
        if target_tags is not None and outbound.get("tag") not in target_tags:
            continue
        outbound["outbounds"] = _merge_outbound_tags(outbound.get("outbounds"), outbound_tags)

    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"
