from __future__ import annotations

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
        response_by_alias = client.get(
            "/api/v1/subscription/lemonjc-dev-token?merge_remote=false&filename=custom.yaml"
        )
        missing = client.get("/sub/wrong-token")

    assert health.json() == {"status": "ok"}
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/yaml")
    assert response.headers["content-disposition"] == "attachment; filename=alice.yaml"
    assert "🇺🇸Example-DL" in response.text
    assert "Remote Example" not in response.text
    assert response_by_alias.status_code == 200
    assert response_by_alias.headers["content-disposition"] == (
        "attachment; filename=custom.yaml"
    )
    assert missing.status_code == 404
