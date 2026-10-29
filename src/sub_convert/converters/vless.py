from __future__ import annotations

import base64
from typing import Any

from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from sub_convert.config.models import InboundPublishOptions, ServerSource
from sub_convert.converters.base import (
    ConversionError,
    ProtocolConverter,
    ProxyNode,
    build_proxy_name,
)
from sub_convert.mihomo.models import MihomoProxy
from sub_convert.singbox.models import SingBoxInbound, SingBoxUser
from sub_convert.subscriptions.formats import SubscriptionFormat


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def reality_public_key(private_key: str) -> str:
    private_bytes = _b64url_decode(private_key)
    key = x25519.X25519PrivateKey.from_private_bytes(private_bytes)
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return _b64url_encode(public)


def _singbox_tls(
    *,
    publish: InboundPublishOptions,
    server_name: str | None,
) -> dict[str, Any] | None:
    if not publish.tls:
        return None
    return {
        "enabled": True,
        "server_name": server_name,
        "insecure": publish.skip_cert_verify,
        "utls": {
            "enabled": True,
            "fingerprint": publish.client_fingerprint,
        },
    }


class VlessRealityConverter(ProtocolConverter):
    def supports(self, inbound: SingBoxInbound) -> bool:
        reality = (inbound.tls or {}).get("reality") or {}
        return inbound.type == "vless" and bool(reality.get("enabled"))

    def convert(
        self,
        *,
        server: ServerSource,
        inbound: SingBoxInbound,
        user: SingBoxUser,
        publish: InboundPublishOptions,
        output_format: SubscriptionFormat = SubscriptionFormat.MIHOMO,
    ) -> ProxyNode:
        if not user.uuid:
            raise ConversionError(f"inbound {inbound.tag} user {user.name} has no uuid")
        if not server.direct_server:
            raise ConversionError(f"server {server.id} needs direct_server for Reality inbound")

        tls = inbound.tls or {}
        reality = tls.get("reality") or {}
        private_key = reality.get("private_key")
        short_ids = reality.get("short_id") or []
        if not private_key or not short_ids:
            raise ConversionError(f"inbound {inbound.tag} missing Reality private_key or short_id")

        public_key = reality_public_key(private_key)
        if output_format is SubscriptionFormat.SING_BOX:
            outbound: ProxyNode = {
                "type": "vless",
                "tag": build_proxy_name(server, publish),
                "server": server.direct_server,
                "server_port": publish.port or inbound.listen_port,
                "uuid": user.uuid,
                "packet_encoding": "xudp",
            }
            if user.flow:
                outbound["flow"] = user.flow
            tls_config = _singbox_tls(publish=publish, server_name=tls.get("server_name"))
            if tls_config:
                tls_config["reality"] = {
                    "enabled": True,
                    "public_key": public_key,
                    "short_id": str(short_ids[0]),
                }
                outbound["tls"] = tls_config
            return outbound

        proxy: MihomoProxy = {
            "name": build_proxy_name(server, publish),
            "type": "vless",
            "server": server.direct_server,
            "udp": True,
            "port": publish.port or inbound.listen_port,
            "uuid": user.uuid,
            "packet-encoding": "xudp",
            "tls": publish.tls,
            "servername": tls.get("server_name"),
            "client-fingerprint": publish.client_fingerprint,
            "skip-cert-verify": publish.skip_cert_verify,
            "reality-opts": {
                "public-key": public_key,
                "short-id": str(short_ids[0]),
            },
        }
        if user.flow:
            proxy["flow"] = user.flow
        return proxy


class VlessHttpUpgradeConverter(ProtocolConverter):
    def supports(self, inbound: SingBoxInbound) -> bool:
        transport = inbound.transport or {}
        return inbound.type == "vless" and transport.get("type") == "httpupgrade"

    def convert(
        self,
        *,
        server: ServerSource,
        inbound: SingBoxInbound,
        user: SingBoxUser,
        publish: InboundPublishOptions,
        output_format: SubscriptionFormat = SubscriptionFormat.MIHOMO,
    ) -> ProxyNode:
        if not user.uuid:
            raise ConversionError(f"inbound {inbound.tag} user {user.name} has no uuid")

        transport: dict[str, Any] = inbound.transport or {}
        headers: dict[str, Any] = transport.get("headers") or {}
        transport_host = transport.get("host")
        host = headers.get("Host") or headers.get("host") or transport_host or publish.server
        node_server = publish.server or transport_host
        if not node_server or not host:
            raise ConversionError(f"inbound {inbound.tag} missing HTTPUpgrade host")

        if output_format is SubscriptionFormat.SING_BOX:
            outbound = {
                "type": "vless",
                "tag": build_proxy_name(server, publish),
                "server": node_server,
                "server_port": publish.port or inbound.listen_port,
                "uuid": user.uuid,
                "packet_encoding": "xudp",
                "transport": {
                    "type": "httpupgrade",
                    "host": host,
                    "path": transport.get("path") or "/",
                },
            }
            if headers:
                outbound["transport"]["headers"] = headers
            tls_config = _singbox_tls(publish=publish, server_name=host)
            if tls_config:
                outbound["tls"] = tls_config
            return outbound

        return {
            "name": build_proxy_name(server, publish),
            "type": "vless",
            "server": node_server,
            "port": publish.port or inbound.listen_port,
            "udp": True,
            "uuid": user.uuid,
            "packet-encoding": "xudp",
            "tls": publish.tls,
            "servername": host,
            "client-fingerprint": publish.client_fingerprint,
            "skip-cert-verify": publish.skip_cert_verify,
            "network": "ws",
            "ws-opts": {
                "path": transport.get("path") or "/",
                "headers": {"Host": host},
                "v2ray-http-upgrade": True,
            },
        }

