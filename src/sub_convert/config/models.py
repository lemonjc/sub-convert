from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator


class RenderConfig(BaseModel):
    inject_proxy_groups: list[str] = Field(
        default_factory=lambda: ["🌏️Main Proxy", "⚖Load Balance", "♾️Auto Select"]
    )


class InboundPublishOptions(BaseModel):
    suffix: str | None = None
    server: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    tls: bool = True
    client_fingerprint: str = "chrome"
    skip_cert_verify: bool = False


class ServerSource(BaseModel):
    id: str
    name: str
    config_path: Path
    direct_server: str | None = None
    inbounds: dict[str, InboundPublishOptions] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("server id cannot be empty")
        return value


class HttpYamlSource(BaseModel):
    url: str | None = None
    file_path: Path | None = None
    user_agent: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> HttpYamlSource:
        if bool(self.url) == bool(self.file_path):
            raise ValueError("YAML source requires exactly one of url or file_path")
        return self


class TemplateSource(HttpYamlSource):
    pass


class RemoteSubscription(HttpYamlSource):
    name: str


class SubscriptionUser(BaseModel):
    username: str
    token_hash: str
    allowed_servers: list[str] = Field(default_factory=list)
    remote_subscriptions: list[RemoteSubscription] = Field(default_factory=list)

    @field_validator("token_hash")
    @classmethod
    def validate_token_hash(cls, value: str) -> str:
        normalized = value.lower()
        if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
            raise ValueError("token_hash must be a SHA-256 hex digest")
        return normalized


class AppConfig(BaseModel):
    template: TemplateSource
    servers: list[ServerSource]
    users: list[SubscriptionUser]
    render: RenderConfig = Field(default_factory=RenderConfig)
    strict_conversion: bool = False
    http_timeout_seconds: float = Field(default=10.0, gt=0)
    remote_cache_ttl_seconds: int = Field(default=300, ge=0)
    http_user_agent: str = "sub-convert/0.1"

    @model_validator(mode="after")
    def validate_references(self) -> AppConfig:
        server_ids = {server.id for server in self.servers}
        if len(server_ids) != len(self.servers):
            raise ValueError("server ids must be unique")

        for user in self.users:
            unknown = set(user.allowed_servers) - server_ids
            if unknown:
                raise ValueError(
                    f"user {user.username!r} references unknown servers: {sorted(unknown)}"
                )
        return self
