"""Luneta API - FastAPI application entrypoint."""
from fastapi import FastAPI

from app.routes import health, orgs


def create_app() -> FastAPI:
    app = FastAPI(title="Luneta API", version="0.1.0")

    # Health
    app.include_router(health.router, prefix="/health", tags=["health"])

    # Organizations (first real MongoDB access)
    app.include_router(orgs.router, prefix="/orgs", tags=["orgs"])

    return app


app = create_app()
