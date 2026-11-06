from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from sub_convert.config import load_config
from sub_convert.config.models import HttpYamlSource
from sub_convert.main import create_app
from sub_convert.subscriptions import loader as loader_module
from sub_convert.subscriptions.formats import SubscriptionFormat
from sub_convert.subscriptions.loader import YamlSourceLoader, _with_notun_parameter
from sub_convert.subscriptions.service import SubscriptionService


def test_with_notun_parameter_preserves_existing_query() -> None:
    url = "https://example.com/template.yaml?token=abc&notun=false#section"

    assert _with_notun_parameter(url) == (
        "https://example.com/template.yaml?token=abc&notun=true#section"
    )


class _FakeResponse:
    text = "proxies:\n  - name: Remote\n"

    def raise_for_status(self) -> None:
        return None


class _FakeClient:
    instances: list[_FakeClient] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.requests: list[str] = []
        self.instances.append(self)

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *args) -> None:
        await self.kwargs["transport"].aclose()

    async def get(self, url: str, *, headers: dict[str, str]) -> _FakeResponse:
        self.requests.append(url)
        return _FakeResponse()


def test_remote_documents_use_ipv4_and_separate_notun_cache(monkeypatch) -> None:
    _FakeClient.instances = []
    monkeypatch.setattr(loader_module.httpx, "AsyncClient", _FakeClient)
    loader = YamlSourceLoader(
        timeout_seconds=1,
        ttl_seconds=60,
        default_user_agent="test-agent",
    )
    source = HttpYamlSource(url="https://example.com/template.yaml?token=abc")

    async def load_documents() -> None:
        await loader.load_document(source)
        await loader.load_document(source)
        await loader.load_document(source, notun=True)
        await loader.load_document(source, notun=True)

    asyncio.run(load_documents())

    assert [url for client in _FakeClient.instances for url in client.requests] == [
        "https://example.com/template.yaml?token=abc",
        "https://example.com/template.yaml?token=abc&notun=true",
    ]
    for client in _FakeClient.instances:
        transport = client.kwargs["transport"]
        assert transport._pool._local_address == "0.0.0.0"


def test_explicit_notun_url_is_used_without_modification(monkeypatch) -> None:
    _FakeClient.instances = []
    monkeypatch.setattr(loader_module.httpx, "AsyncClient", _FakeClient)
    loader = YamlSourceLoader(
        timeout_seconds=1,
        ttl_seconds=60,
        default_user_agent="test-agent",
    )
    source = HttpYamlSource(
        url="https://example.com/config.json",
        notun_url="https://example.com/config-notun.json?token=abc",
    )

    async def load_documents() -> None:
        await loader.load_document(source)
        await loader.load_document(source, notun=True)

    asyncio.run(load_documents())

    assert [url for client in _FakeClient.instances for url in client.requests] == [
        "https://example.com/config.json",
        "https://example.com/config-notun.json?token=abc",
    ]


class _RecordingLoader:
    def __init__(self, config) -> None:
        self.config = config
        self.calls: list[tuple[str, bool]] = []

    async def load_document(
        self,
        source: HttpYamlSource,
        *,
        notun: bool = False,
    ) -> dict:
        self.calls.append(("document", notun))
        if source is self.config.templates.singbox:
            return {"outbounds": []}
        return {"proxies": [], "proxy-groups": []}

    async def load_many(self, remotes, *, notun: bool = False) -> list:
        self.calls.append(("mihomo_remotes", notun))
        return []

    async def load_singbox_many(self, remotes, *, notun: bool = False) -> list:
        self.calls.append(("singbox_remotes", notun))
        return []


@pytest.mark.parametrize(
    ("output_format", "remote_call"),
    [
        (SubscriptionFormat.MIHOMO, "mihomo_remotes"),
        (SubscriptionFormat.SING_BOX, "singbox_remotes"),
    ],
)
def test_service_forwards_notun_to_template_and_remotes(
    output_format: SubscriptionFormat,
    remote_call: str,
) -> None:
    config = load_config("config.example.yaml")
    recording_loader = _RecordingLoader(config)
    service = SubscriptionService(config, yaml_loader=recording_loader)

    asyncio.run(
        service.render_for_token(
            "lemonjc-dev-token",
            output_format=output_format,
            notun=True,
        )
    )

    assert recording_loader.calls == [
        ("document", True),
        (remote_call, True),
    ]


def test_http_endpoints_forward_notun(monkeypatch) -> None:
    monkeypatch.setenv("SUB_CONVERT_CONFIG", "config.example.yaml")
    calls: list[bool] = []

    async def fake_render(
        self,
        token: str,
        *,
        include_remote: bool = True,
        output_format: SubscriptionFormat = SubscriptionFormat.MIHOMO,
        notun: bool = False,
    ) -> str:
        calls.append(notun)
        return "proxies: []\n"

    monkeypatch.setattr(SubscriptionService, "render_for_token", fake_render)
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/sub/lemonjc-dev-token?notun=true")
        alias_response = client.get(
            "/api/v1/subscription/lemonjc-dev-token?notun=1"
        )

    assert response.status_code == 200
    assert alias_response.status_code == 200
    assert calls == [True, True]
