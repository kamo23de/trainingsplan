"""FastAPI-Anwendung: Dashboard und JSON-Schnittstellen."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from trainingsplan import __version__
from trainingsplan.analytics.activity_detail import activity_detail
from trainingsplan.analytics.dashboard import RANGES, build_dashboard
from trainingsplan.config import get_settings
from trainingsplan.storage.db import init_db, session_scope
from trainingsplan.storage.models import Activity
from trainingsplan.web.planning_api import router as planning_router

DbSession = Annotated[Session, Depends(session_scope)]

STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES = Jinja2Templates(directory=Path(__file__).parent / "templates")


def static_url(path: str) -> str:
    """URL mit Änderungszeit als Parameter, damit der Browser nach Updates neu lädt."""
    file = STATIC_DIR / path
    version = int(file.stat().st_mtime) if file.exists() else 0
    return f"/static/{path}?v={version}"


TEMPLATES.env.globals["static_url"] = static_url


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Trainingsplan", version=__version__, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(planning_router)

RangeKey = Annotated[str, Query(pattern="^(" + "|".join([*RANGES, "all"]) + ")$")]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/summary")
def summary(db: DbSession) -> dict:
    count, distance, first, last = db.execute(
        select(
            func.count(Activity.id),
            func.coalesce(func.sum(Activity.distance_m), 0),
            func.min(Activity.start_time),
            func.max(Activity.start_time),
        )
    ).one()
    return {
        "activities": count,
        "distance_km": round(distance / 1000, 1),
        "first_activity": first.isoformat() if first else None,
        "last_activity": last.isoformat() if last else None,
    }


@app.get("/api/dashboard")
def dashboard_data(db: DbSession, range: RangeKey = "1y") -> dict:  # noqa: A002
    return build_dashboard(db, range)


@app.get("/api/activities/{activity_id}")
def activity_data(activity_id: int, db: DbSession) -> dict:
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Aktivität nicht gefunden")
    return activity_detail(db, activity, get_settings().data_dir)


def _page(request: Request, template: str, active: str, **ctx) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        request, template, {"version": __version__, "active": active, **ctx}
    )


@app.get("/", response_class=HTMLResponse)
def start_page(request: Request) -> HTMLResponse:
    return _page(request, "start.html", "start")


@app.get("/rueckblick", response_class=HTMLResponse)
def history_page(request: Request) -> HTMLResponse:
    return _page(request, "dashboard.html", "history")


@app.get("/planung", response_class=HTMLResponse)
def planning_page(request: Request) -> HTMLResponse:
    return _page(request, "planning.html", "plan")
