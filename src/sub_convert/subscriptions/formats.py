from __future__ import annotations

import re
from enum import StrEnum


class SubscriptionFormat(StrEnum):
    MIHOMO = "mihomo"
    SING_BOX = "sing-box"


def detect_subscription_format(user_agent: str | None) -> SubscriptionFormat:
    normalized = re.sub(r"[^a-z0-9]+", "", (user_agent or "").lower())
    if "singbox" in normalized:
        return SubscriptionFormat.SING_BOX
    return SubscriptionFormat.MIHOMO
