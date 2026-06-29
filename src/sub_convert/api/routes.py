from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from sub_convert.subscriptions.service import SubscriptionService

router = APIRouter()


def get_service(request: Request) -> SubscriptionService:
    return request.app.state.subscription_service


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sub/{token}", response_class=PlainTextResponse)
async def subscription(
    token: str,
    request: Request,
    include_remote: bool = True,
    merge_remote: bool | None = None,
) -> PlainTextResponse:
    should_include_remote = include_remote if merge_remote is None else merge_remote
    content = await get_service(request).render_for_token(
        token,
        include_remote=should_include_remote,
    )
    return PlainTextResponse(content, media_type="text/yaml; charset=utf-8")


@router.get("/api/v1/subscription/{token}", response_class=PlainTextResponse)
async def subscription_v1(
    token: str,
    request: Request,
    include_remote: bool = True,
    merge_remote: bool | None = None,
) -> PlainTextResponse:
    should_include_remote = include_remote if merge_remote is None else merge_remote
    content = await get_service(request).render_for_token(
        token,
        include_remote=should_include_remote,
    )
    return PlainTextResponse(content, media_type="text/yaml; charset=utf-8")
