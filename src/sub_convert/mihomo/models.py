from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from sub_convert.config.models import ServerSource, SubscriptionUser

MihomoProxy = dict[str, Any]


class RenderContext(BaseModel):
    user: SubscriptionUser
    servers: list[ServerSource]
    local_proxies: list[MihomoProxy] = Field(default_factory=list)
    remote_proxies: list[MihomoProxy] = Field(default_factory=list)

