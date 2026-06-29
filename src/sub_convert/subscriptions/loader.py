from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import yaml

from sub_convert.config.models import HttpYamlSource, RemoteSubscription
from sub_convert.mihomo.models import MihomoProxy


@dataclass
class _CacheEntry:
    expires_at: float
    data: dict[str, Any]


class YamlSourceLoader:
    def __init__(
        self,
        *,
        timeout_seconds: float,
        ttl_seconds: int,
        default_user_agent: str,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._ttl_seconds = ttl_seconds
        self._default_user_agent = default_user_agent
        self._cache: dict[str, _CacheEntry] = {}

    async def load_many(self, remotes: list[RemoteSubscription]) -> list[MihomoProxy]:
        proxies: list[MihomoProxy] = []
        for remote in remotes:
            proxies.extend(await self.load_proxies(remote))
        return proxies

    async def load_document(self, source: HttpYamlSource) -> dict[str, Any]:
        key = self._cache_key(source)
        if not key:
            return {}

        now = time.monotonic()
        cached = self._cache.get(key)
        if cached and cached.expires_at > now:
            return cached.data

        if source.file_path:
            text = Path(source.file_path).read_text(encoding="utf-8")
        else:
            headers = {"User-Agent": source.user_agent or self._default_user_agent}
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(str(source.url), headers=headers)
                response.raise_for_status()
                text = response.text

        data: dict[str, Any] = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            data = {}

        expires_at = now + self._ttl_seconds if self._ttl_seconds else now
        if self._ttl_seconds:
            self._cache[key] = _CacheEntry(expires_at=expires_at, data=data)
        return data

    async def load_proxies(self, remote: RemoteSubscription) -> list[MihomoProxy]:
        data = await self.load_document(remote)
        proxies = data.get("proxies") or []
        if not isinstance(proxies, list):
            proxies = []

        return [proxy for proxy in proxies if isinstance(proxy, dict)]

    def _cache_key(self, source: HttpYamlSource) -> str:
        location = source.url or str(source.file_path)
        user_agent = source.user_agent or self._default_user_agent
        return f"{location}|ua={user_agent}"


RemoteSubscriptionLoader = YamlSourceLoader
