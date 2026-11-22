"""FastAPI-Anwendung: Dashboard und JSON-Schnittstellen."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from trainingsplan import __version__
from trainingsplan.storage.db import init_db, session_scope
from trainingsplan.storage.models import Activity

DbSession = Annotated[Session, Depends(session_scope)]

TEMPLATES = Jinja2Templates(directory=Path(__file__).parent / "templates")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Trainingsplan", version=__version__, lifespan=lifespan)


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


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: DbSession) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        request, "dashboard.html", {"summary": summary(db), "version": __version__}
    )
