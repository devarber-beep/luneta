from fastapi import FastAPI

from luneta.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Luneta API", version="0.1.0")

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok"}

    # Routers (auth, orgs, scenarios, comments, exports, ai, similarity)
    # will be included here as they are implemented.

    return app


app = create_app()

