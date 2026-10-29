from __future__ import annotations

import json

import yaml
from fastapi.testclient import TestClient

from sub_convert.config import load_config
from sub_convert.main import create_app
from sub_convert.subscriptions.service import SubscriptionService, UserNotFoundError


def test_service_renders_user_subscription_without_leaking_other_users() -> None:
    config = load_config("config.example.yaml")
    service = SubscriptionService(config)

    rendered = __import__("asyncio").run(
        service.render_for_token("lemonjc-dev-token", include_remote=False)
    )
    data = yaml.safe_load(rendered)
    names = [proxy["name"] for proxy in data["proxies"]]
    serialized = yaml.safe_dump(data, allow_unicode=True)

    assert "🇺🇸Example-DL" in names
    assert "🇺🇸Example-CF" in names
    assert "Remote Example" not in names
    assert "22222222-2222-4222-8222-222222222222" not in serialized


def test_service_can_merge_local_remote_subscription() -> None:
    config = load_config("config.example.yaml")
    service = SubscriptionService(config)

    rendered = __import__("asyncio").run(service.render_for_token("lemonjc-dev-token"))
    data = yaml.safe_load(rendered)
    names = [proxy["name"] for proxy in data["proxies"]]

    assert "🇺🇸Example-DL" in names
    assert "Remote Example" in names
    assert "Remote SingBox Example" not in names


def test_invalid_token_is_hidden() -> None:
    config = load_config("config.example.yaml")
    service = SubscriptionService(config)

    try:
        service.find_user_by_token("wrong-token")
    except UserNotFoundError:
        pass
    else:
        raise AssertionError("expected UserNotFoundError")


def test_http_subscription_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("SUB_CONVERT_CONFIG", "config.example.yaml")
    app = create_app()
    with TestClient(app) as client:
        health = client.get("/healthz")
        response = client.get("/sub/lemonjc-dev-token?include_remote=false")
        mihomo_response = client.get(
            "/sub/lemonjc-dev-token?include_remote=false",
            headers={"User-Agent": "mihomo/1.19.0"},
        )
        singbox_response = client.get(
            "/sub/lemonjc-dev-token?include_remote=false",
            headers={"User-Agent": "sing-box/1.11.0"},
        )
        singbox_with_remote = client.get(
            "/sub/lemonjc-dev-token",
            headers={"User-Agent": "sing-box/1.11.0"},
        )
        response_by_alias = client.get(
            "/api/v1/subscription/lemonjc-dev-token?merge_remote=false&filename=custom.yaml",
            headers={"User-Agent": "clash-verge/v2.0.0"},
        )
        missing = client.get("/sub/wrong-token")

    assert health.json() == {"status": "ok"}
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/yaml")
    assert response.headers["content-disposition"] == "attachment; filename=alice.yaml"
    assert response.headers["vary"] == "User-Agent"
    assert "🇺🇸Example-DL" in response.text
    assert "Remote Example" not in response.text
    assert mihomo_response.headers["content-type"].startswith("text/yaml")
    assert "🇺🇸Example-DL" in mihomo_response.text
    assert singbox_response.status_code == 200
    assert singbox_response.headers["content-type"].startswith("application/json")
    assert singbox_response.headers["content-disposition"] == "attachment; filename=alice.json"
    singbox_data = json.loads(singbox_response.text)
    singbox_outbounds = {
        outbound["tag"]: outbound
        for outbound in singbox_data["outbounds"]
        if outbound.get("tag") not in {"Direct", "♾️Auto Select"}
    }
    assert "🇺🇸Example-DL" in singbox_outbounds
    assert "🇺🇸Example-CF" in singbox_outbounds
    assert "🇺🇸Example-DL" in singbox_data["outbounds"][0]["outbounds"]
    assert "Remote SingBox Example" not in singbox_outbounds
    assert "Remote Example" not in singbox_outbounds
    assert "22222222-2222-4222-8222-222222222222" not in singbox_response.text
    singbox_with_remote_data = json.loads(singbox_with_remote.text)
    remote_outbounds = {
        outbound["tag"]: outbound
        for outbound in singbox_with_remote_data["outbounds"]
    }
    assert "Remote SingBox Example" in remote_outbounds
    assert "Remote Selector" not in remote_outbounds
    assert "Remote SingBox Example" in remote_outbounds["🌏️Main Proxy"]["outbounds"]
    assert response_by_alias.status_code == 200
    assert response_by_alias.headers["content-disposition"] == (
        "attachment; filename=custom.yaml"
    )
    assert missing.status_code == 404
