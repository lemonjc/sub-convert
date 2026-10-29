from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

from sub_convert.config.models import AppConfig, ServerSource, SubscriptionUser
from sub_convert.converters.base import ProxyNode
from sub_convert.converters.registry import ConverterRegistry, default_registry
from sub_convert.mihomo.renderer import render_subscription as render_mihomo_subscription
from sub_convert.singbox.reader import load_singbox_config
from sub_convert.singbox.renderer import render_subscription as render_singbox_subscription
from sub_convert.subscriptions.formats import SubscriptionFormat
from sub_convert.subscriptions.loader import YamlSourceLoader


class UserNotFoundError(LookupError):
    """Raised when a subscription token is invalid."""


class TemplateNotConfiguredError(RuntimeError):
    """Raised when the requested output format has no template."""


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

    async def render_for_token(
        self,
        token: str,
        *,
        include_remote: bool = True,
        output_format: SubscriptionFormat = SubscriptionFormat.MIHOMO,
    ) -> str:
        user = self.find_user_by_token(token)
        nodes = self._convert_nodes_for_user(user, output_format=output_format)

        if output_format is SubscriptionFormat.SING_BOX:
            source = self._config.templates.singbox
            if source is None:
                raise TemplateNotConfiguredError("sing-box template is not configured")
            template = await self._yaml_loader.load_document(source)
            remote_outbounds = (
                await self._yaml_loader.load_singbox_many(user.remote_subscriptions)
                if include_remote
                else []
            )
            return render_singbox_subscription(
                template=template,
                outbounds=[*nodes, *remote_outbounds],
            )

        source = self._config.templates.mihomo
        if source is None:
            raise TemplateNotConfiguredError("Mihomo template is not configured")
        template = await self._yaml_loader.load_document(source)
        remote_proxies = (
            await self._yaml_loader.load_many(user.remote_subscriptions)
            if include_remote
            else []
        )
        return render_mihomo_subscription(
            template=template,
            proxies=[*nodes, *remote_proxies],
            render_config=self._config.render,
        )

    def _convert_nodes_for_user(
        self,
        user: SubscriptionUser,
        *,
        output_format: SubscriptionFormat,
    ) -> list[ProxyNode]:
        nodes: list[ProxyNode] = []
        allowed = self._servers_for_user(user)
        for server in allowed:
            singbox = load_singbox_config(str(Path(server.config_path)))
            for inbound in singbox.inbounds:
                node = self._registry.convert(
                    server=server,
                    inbound=inbound,
                    username=user.username,
                    strict=self._config.strict_conversion,
                    output_format=output_format,
                )
                if node:
                    nodes.append(node)
        return nodes

    def _servers_for_user(self, user: SubscriptionUser) -> list[ServerSource]:
        by_id = {server.id: server for server in self._config.servers}
        return [by_id[server_id] for server_id in user.allowed_servers if server_id in by_id]
