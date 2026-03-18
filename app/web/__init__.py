import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.db import Database, RecordQueryService
from app.web.limiter import limiter
from app.web.routes import dashboard, explore

BASE_DIR = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Vangran Funding Tracker")

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.exception("Unhandled error")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com https://cdn.tailwindcss.com; "
            "img-src 'self' data: https://tile.openstreetmap.org https://*.tile.openstreetmap.org; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        return response

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

    db = Database()
    db.create_tables()
    app.state.db = db
    app.state.query_service = RecordQueryService(db)
    templates = Jinja2Templates(directory=BASE_DIR / "templates")
    templates.env.globals["last_updated"] = lambda: RecordQueryService(db).get_last_updated()
    app.state.templates = templates

    app.include_router(dashboard.router)
    app.include_router(explore.router)

    @app.get("/healthz")
    def healthz():
        return {"status": "healthy"}

    return app
