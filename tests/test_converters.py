from __future__ import annotations

from sub_convert.config import load_config
from sub_convert.converters.registry import default_registry
from sub_convert.converters.vless import reality_public_key
from sub_convert.singbox.reader import load_singbox_config


def test_reality_public_key_derivation_matches_example() -> None:
    assert (
        reality_public_key("KPJUT1ggq-6Cf-qbqOUp9ZRiEvSRm-woReQyfYJ_j0E")
        == "vv2-cw4_HcPu-aqvjBWuOmAw6Vmi2f3tE3447gdUICg"
    )


def test_vless_reality_and_httpupgrade_conversion() -> None:
    config = load_config("config.example.yaml")
    server = next(item for item in config.servers if item.id == "example-server")
    singbox = load_singbox_config(str(server.config_path))
    registry = default_registry()

    proxies = [
        registry.convert(
            server=server,
            inbound=inbound,
            username="alice",
            strict=True,
        )
        for inbound in singbox.inbounds
    ]

    assert proxies[0]["name"] == "🇺🇸Example-DL"
    assert proxies[0]["uuid"] == "11111111-1111-4111-8111-111111111111"
    assert proxies[0]["reality-opts"]["public-key"] == "vv2-cw4_HcPu-aqvjBWuOmAw6Vmi2f3tE3447gdUICg"
    assert proxies[1]["name"] == "🇺🇸Example-CF"
    assert proxies[1]["network"] == "ws"
    assert proxies[1]["ws-opts"]["v2ray-http-upgrade"] is True


def test_conversion_skips_other_users() -> None:
    config = load_config("config.example.yaml")
    server = next(item for item in config.servers if item.id == "example-server")
    inbound = load_singbox_config(str(server.config_path)).inbounds[0]

    proxy = default_registry().convert(
        server=server,
        inbound=inbound,
        username="missing-user",
        strict=True,
    )

    assert proxy is None
