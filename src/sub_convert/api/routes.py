from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from sub_convert.subscriptions.service import SubscriptionService

router = APIRouter()
DEFAULT_SUBSCRIPTION_FILENAME = "subscription.yaml"


def get_service(request: Request) -> SubscriptionService:
    return request.app.state.subscription_service


def _safe_filename(filename: str | None) -> str:
    candidate = (filename or DEFAULT_SUBSCRIPTION_FILENAME).strip()
    candidate = candidate.replace("/", "_").replace("\\", "_")
    candidate = "".join(char for char in candidate if char.isprintable() and char not in {'"', ";"})
    if not candidate or candidate in {".", ".."}:
        return DEFAULT_SUBSCRIPTION_FILENAME
    return candidate


def _yaml_response(content: str, *, filename: str | None) -> PlainTextResponse:
    safe_filename = _safe_filename(filename)
    return PlainTextResponse(
        content,
        media_type="text/yaml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


def _default_filename_for_token(service: SubscriptionService, token: str) -> str:
    user = service.find_user_by_token(token)
    return f"{user.username}.yaml"


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
    content = await service.render_for_token(
        token,
        include_remote=should_include_remote,
    )
    return _yaml_response(content, filename=filename or _default_filename_for_token(service, token))


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
    content = await service.render_for_token(
        token,
        include_remote=should_include_remote,
    )
    return _yaml_response(content, filename=filename or _default_filename_for_token(service, token))
