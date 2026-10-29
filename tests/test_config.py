from __future__ import annotations

from sub_convert.config import load_config


def test_load_config_resolves_paths() -> None:
    config = load_config("config.example.yaml")

    assert config.templates.mihomo.file_path.name == "template.example.yaml"
    assert config.templates.singbox.file_path.name == "config.template.json"
    assert config.http_user_agent == "sub-convert/0.1"
    assert {server.id for server in config.servers} == {"example-server"}
    assert config.users[0].username == "alice"
    assert config.users[0].remote_subscriptions[0].file_path.name == (
        "remote-subscription.example.yaml"
    )
    assert config.users[0].remote_subscriptions[0].user_agent == "clash.meta"
    assert config.users[0].remote_subscriptions[0].type == "mihomo"
    assert config.users[0].remote_subscriptions[1].file_path.name == (
        "remote-singbox-subscription.example.json"
    )
    assert config.users[0].remote_subscriptions[1].user_agent == "sing-box"
    assert config.users[0].remote_subscriptions[1].type == "sing-box"


def test_load_config_supports_legacy_template(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
template:
  file_path: template.yaml
servers: []
users: []
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.template.file_path == tmp_path / "template.yaml"
    assert config.templates.singbox is None
