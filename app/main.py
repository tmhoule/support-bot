from fastapi import FastAPI
from app.config import get_settings
from app.routes import health


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Support Bot")
    app.state.settings = settings
    app.include_router(health.router)
    return app


app = create_app()
