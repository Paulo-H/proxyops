"""FastAPI application entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.db.init_db import init_db


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
)

app = FastAPI(
    title=f"{settings.PROJECT_NAME} API",
    description=(
        "Proxy fleet manager — multi-provider proxy inventory, smart rotation "
        "strategies, and request analytics.\n\n"
        "Two authentication mechanisms exist:\n"
        "- **JWT bearer** for human/web access (see `/auth/login`).\n"
        "- **`X-Robot-Key` header** for scraping robots calling `/rotation/*`."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health", tags=["meta"], summary="Liveness probe")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
