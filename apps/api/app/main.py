"""Luneta API - FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import (
    admin_catalogs,
    admin_evaluations,
    admin_users,
    auth,
    catalog,
    health,
    orgs,
    public,
    scenarios,
    evaluations,
    suggestions,
    workflow,
)


def create_app() -> FastAPI:
    app = FastAPI(title="Luneta API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health
    app.include_router(health.router, prefix="/health", tags=["health"])

    # Organizations (first real MongoDB access)
    app.include_router(orgs.router, prefix="/orgs", tags=["orgs"])
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(catalog.router, prefix="/catalog", tags=["catalog"])
    app.include_router(admin_users.router, prefix="/admin", tags=["admin"])
    app.include_router(admin_catalogs.router, prefix="/admin", tags=["admin"])
    app.include_router(admin_evaluations.router, prefix="/admin", tags=["admin"])
    app.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
    app.include_router(suggestions.router, prefix="/scenarios", tags=["suggestions"])
    app.include_router(evaluations.router, prefix="/scenarios", tags=["evaluations"])
    app.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
    app.include_router(public.router, prefix="/public", tags=["public"])

    return app


app = create_app()
