from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SingBoxUser(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    uuid: str | None = None
    password: str | None = None
    flow: str | None = None


class SingBoxInbound(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    tag: str
    listen: str | None = None
    listen_port: int
    users: list[SingBoxUser] = Field(default_factory=list)
    tls: dict[str, Any] | None = None
    transport: dict[str, Any] | None = None

    def user_by_name(self, username: str) -> SingBoxUser | None:
        return next((user for user in self.users if user.name == username), None)


class SingBoxServerConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    inbounds: list[SingBoxInbound] = Field(default_factory=list)

