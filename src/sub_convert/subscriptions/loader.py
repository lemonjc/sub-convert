from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
import yaml

from sub_convert.config.models import HttpYamlSource, RemoteSubscription
from sub_convert.converters.base import ProxyNode
from sub_convert.mihomo.models import MihomoProxy
from sub_convert.subscriptions.formats import SubscriptionFormat

logger = logging.getLogger(__name__)

SINGBOX_CONTROL_OUTBOUND_TYPES = frozenset({"block", "direct", "dns", "selector", "urltest"})
IPV4_LOCAL_ADDRESS = "0.0.0.0"


def _with_notun_parameter(url: str) -> str:
    parts = urlsplit(url)
    query = [
        (name, value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
        if name != "notun"
    ]
    query.append(("notun", "true"))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


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

    async def load_many(
        self,
        remotes: list[RemoteSubscription],
        *,
        notun: bool = False,
    ) -> list[MihomoProxy]:
        proxies: list[MihomoProxy] = []
        for remote in remotes:
            if remote.type is not SubscriptionFormat.MIHOMO:
                continue
            proxies.extend(await self.load_proxies(remote, notun=notun))
        return proxies

    async def load_singbox_many(
        self,
        remotes: list[RemoteSubscription],
        *,
        notun: bool = False,
    ) -> list[ProxyNode]:
        outbounds: list[ProxyNode] = []
        for remote in remotes:
            if remote.type is not SubscriptionFormat.SING_BOX:
                continue
            outbounds.extend(await self.load_singbox_outbounds(remote, notun=notun))
        return outbounds

    async def load_document(
        self,
        source: HttpYamlSource,
        *,
        notun: bool = False,
    ) -> dict[str, Any]:
        key = self._cache_key(source, notun=notun)
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
            location = self._source_location(source, notun=notun)
            transport = httpx.AsyncHTTPTransport(local_address=IPV4_LOCAL_ADDRESS)
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=transport,
            ) as client:
                response = await client.get(location, headers=headers)
                response.raise_for_status()
                text = response.text

        data: dict[str, Any] = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            data = {}

        expires_at = now + self._ttl_seconds if self._ttl_seconds else now
        if self._ttl_seconds:
            self._cache[key] = _CacheEntry(expires_at=expires_at, data=data)
        return data

    async def load_proxies(
        self,
        remote: RemoteSubscription,
        *,
        notun: bool = False,
    ) -> list[MihomoProxy]:
        data = await self.load_document(remote, notun=notun)
        proxies = data.get("proxies") or []
        if not isinstance(proxies, list):
            proxies = []

        return [proxy for proxy in proxies if isinstance(proxy, dict)]

    async def load_singbox_outbounds(
        self,
        remote: RemoteSubscription,
        *,
        notun: bool = False,
    ) -> list[ProxyNode]:
        data = await self.load_document(remote, notun=notun)
        outbounds = data.get("outbounds") or []
        if not isinstance(outbounds, list):
            return []

        nodes = [
            outbound
            for outbound in outbounds
            if isinstance(outbound, dict)
            and outbound.get("type") not in SINGBOX_CONTROL_OUTBOUND_TYPES
        ]
        if not nodes:
            logger.warning(
                "remote subscription %r has no sing-box outbounds; "
                "check its URL and configured user_agent",
                remote.name,
            )
        return nodes

    def _cache_key(self, source: HttpYamlSource, *, notun: bool = False) -> str:
        location = self._source_location(source, notun=notun)
        user_agent = source.user_agent or self._default_user_agent
        return f"{location}|ua={user_agent}"

    def _source_location(self, source: HttpYamlSource, *, notun: bool = False) -> str:
        if source.file_path:
            return str(source.file_path)
        if not source.url:
            return ""
        if not notun:
            return source.url
        return source.notun_url or _with_notun_parameter(source.url)


RemoteSubscriptionLoader = YamlSourceLoader
