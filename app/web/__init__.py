from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import Database, RecordQueryService
from app.web.routes import dashboard, explore

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def create_app() -> FastAPI:
    app = FastAPI(title="Vangran Funding Tracker")

    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

    db = Database()
    db.create_tables()
    app.state.db = db
    app.state.query_service = RecordQueryService(db)
    app.state.templates = Jinja2Templates(directory=BASE_DIR / "templates")

    app.include_router(dashboard.router)
    app.include_router(explore.router)

    return app
