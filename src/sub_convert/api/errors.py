from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sub_convert.converters.base import ConversionError
from sub_convert.subscriptions.service import UserNotFoundError

logger = logging.getLogger(__name__)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(UserNotFoundError)
    async def user_not_found_handler(_: Request, __: UserNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "not found"})

    @app.exception_handler(ConversionError)
    async def conversion_error_handler(_: Request, exc: ConversionError) -> JSONResponse:
        logger.warning("subscription conversion failed: %s", exc)
        return JSONResponse(status_code=422, content={"detail": "subscription conversion failed"})

    @app.exception_handler(Exception)
    async def generic_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled subscription error: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "internal server error"})

