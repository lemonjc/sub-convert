from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from sub_convert.subscriptions.formats import (
    SubscriptionFormat,
    detect_subscription_format,
)
from sub_convert.subscriptions.service import SubscriptionService

router = APIRouter()
DEFAULT_SUBSCRIPTION_FILENAME = "subscription.yaml"


def get_service(request: Request) -> SubscriptionService:
    return request.app.state.subscription_service


def _safe_filename(filename: str | None, *, default: str) -> str:
    candidate = (filename or default).strip()
    candidate = candidate.replace("/", "_").replace("\\", "_")
    candidate = "".join(char for char in candidate if char.isprintable() and char not in {'"', ";"})
    if not candidate or candidate in {".", ".."}:
        return default
    return candidate


def _subscription_response(
    content: str,
    *,
    output_format: SubscriptionFormat,
    filename: str | None,
) -> PlainTextResponse:
    if output_format is SubscriptionFormat.SING_BOX:
        default = "subscription.json"
        media_type = "application/json; charset=utf-8"
    else:
        default = DEFAULT_SUBSCRIPTION_FILENAME
        media_type = "text/yaml; charset=utf-8"
    safe_filename = _safe_filename(filename, default=default)
    return PlainTextResponse(
        content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={safe_filename}",
            "Vary": "User-Agent",
        },
    )


def _default_filename_for_token(
    service: SubscriptionService,
    token: str,
    output_format: SubscriptionFormat,
) -> str:
    user = service.find_user_by_token(token)
    extension = "json" if output_format is SubscriptionFormat.SING_BOX else "yaml"
    return f"{user.username}.{extension}"


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sub/{token}", response_class=PlainTextResponse)
async def subscription(
    token: str,
    request: Request,
    include_remote: bool = True,
    merge_remote: bool | None = None,
    filename: str | None = None,
) -> PlainTextResponse:
    should_include_remote = include_remote if merge_remote is None else merge_remote
    service = get_service(request)
    output_format = detect_subscription_format(request.headers.get("user-agent"))
    content = await service.render_for_token(
        token,
        include_remote=should_include_remote,
        output_format=output_format,
    )
    return _subscription_response(
        content,
        output_format=output_format,
        filename=filename or _default_filename_for_token(service, token, output_format),
    )


@router.get("/api/v1/subscription/{token}", response_class=PlainTextResponse)
async def subscription_v1(
    token: str,
    request: Request,
    include_remote: bool = True,
    merge_remote: bool | None = None,
    filename: str | None = None,
) -> PlainTextResponse:
    should_include_remote = include_remote if merge_remote is None else merge_remote
    service = get_service(request)
    output_format = detect_subscription_format(request.headers.get("user-agent"))
    content = await service.render_for_token(
        token,
        include_remote=should_include_remote,
        output_format=output_format,
    )
    return _subscription_response(
        content,
        output_format=output_format,
        filename=filename or _default_filename_for_token(service, token, output_format),
    )
