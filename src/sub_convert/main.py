from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from sub_convert.api.errors import install_error_handlers
from sub_convert.api.routes import router
from sub_convert.config import load_config
from sub_convert.subscriptions.service import SubscriptionService


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("SUB_CONVERT_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    config_path = os.getenv("SUB_CONVERT_CONFIG", "config.yaml")
    config = load_config(config_path)
    app.state.subscription_service = SubscriptionService(config)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="sub-convert", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    install_error_handlers(app)
    return app


app = create_app()

