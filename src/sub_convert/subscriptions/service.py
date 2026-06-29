from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

from sub_convert.config.models import AppConfig, ServerSource, SubscriptionUser
from sub_convert.converters.registry import ConverterRegistry, default_registry
from sub_convert.mihomo.renderer import render_subscription
from sub_convert.singbox.reader import load_singbox_config
from sub_convert.subscriptions.loader import YamlSourceLoader


class UserNotFoundError(LookupError):
    """Raised when a subscription token is invalid."""


class SubscriptionService:
    def __init__(
        self,
        config: AppConfig,
        *,
        registry: ConverterRegistry | None = None,
        yaml_loader: YamlSourceLoader | None = None,
    ) -> None:
        self._config = config
        self._registry = registry or default_registry()
        self._yaml_loader = yaml_loader or YamlSourceLoader(
            timeout_seconds=config.http_timeout_seconds,
            ttl_seconds=config.remote_cache_ttl_seconds,
            default_user_agent=config.http_user_agent,
        )

    def find_user_by_token(self, token: str) -> SubscriptionUser:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        for user in self._config.users:
            if hmac.compare_digest(digest, user.token_hash):
                return user
        raise UserNotFoundError("invalid subscription token")

    async def render_for_token(self, token: str, *, include_remote: bool = True) -> str:
        user = self.find_user_by_token(token)
        allowed = self._servers_for_user(user)

        local_proxies = []
        for server in allowed:
            singbox = load_singbox_config(str(Path(server.config_path)))
            for inbound in singbox.inbounds:
                proxy = self._registry.convert(
                    server=server,
                    inbound=inbound,
                    username=user.username,
                    strict=self._config.strict_conversion,
                )
                if proxy:
                    local_proxies.append(proxy)

        template = await self._yaml_loader.load_document(self._config.template)
        remote_proxies = (
            await self._yaml_loader.load_many(user.remote_subscriptions)
            if include_remote
            else []
        )
        return render_subscription(
            template=template,
            proxies=[*local_proxies, *remote_proxies],
            render_config=self._config.render,
        )

    def _servers_for_user(self, user: SubscriptionUser) -> list[ServerSource]:
        by_id = {server.id: server for server in self._config.servers}
        return [by_id[server_id] for server_id in user.allowed_servers if server_id in by_id]
