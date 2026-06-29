from __future__ import annotations

from sub_convert.config import load_config


def test_load_config_resolves_paths() -> None:
    config = load_config("config.example.yaml")

    assert config.template.file_path.name == "template.example.yaml"
    assert config.http_user_agent == "sub-convert/0.1"
    assert {server.id for server in config.servers} == {"example-server"}
    assert config.users[0].username == "alice"
    assert config.users[0].remote_subscriptions[0].file_path.name == (
        "remote-subscription.example.yaml"
    )
    assert config.users[0].remote_subscriptions[0].user_agent == "clash.meta"
