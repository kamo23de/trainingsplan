"""JSON-Schnittstellen der Trainingsplanung: Events, Verfügbarkeit, Plan, Kalender."""

from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from trainingsplan.planning.service import (
    MAX_MAIN_EVENTS,
    calendar,
    compute_plan,
    get_availability,
    get_options,
    set_availability,
    set_options,
)
from trainingsplan.storage.db import session_scope
from trainingsplan.storage.models import Event, EventPriority

router = APIRouter(prefix="/api")
DbSession = Annotated[Session, Depends(session_scope)]


class EventIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    start_date: date
    days: int = Field(default=1, ge=1, le=30)
    priority: Literal["A", "B"] = "B"
    distance_km: float | None = Field(default=None, ge=0, le=10000)
    elevation_m: float | None = Field(default=None, ge=0, le=100000)
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def strip(cls, v: str) -> str:
        return v.strip()


def _event_dict(e: Event) -> dict:
    return {
        "id": e.id,
        "title": e.title,
        "start_date": e.start_date.isoformat(),
        "end_date": (e.start_date + timedelta(days=(e.days or 1) - 1)).isoformat(),
        "days": e.days,
        "priority": e.priority,
        "distance_km": e.distance_km,
        "elevation_m": e.elevation_m,
        "notes": e.notes,
    }


def _check_main_limit(db: Session, data: EventIn, exclude_id: int | None = None) -> None:
    if data.priority != EventPriority.MAIN:
        return
    query = select(func.count(Event.id)).where(
        Event.priority == EventPriority.MAIN, Event.start_date >= date.today()
    )
    if exclude_id:
        query = query.where(Event.id != exclude_id)
    if db.scalar(query) >= MAX_MAIN_EVENTS:
        raise HTTPException(
            status_code=409,
            detail=f"Es sind höchstens {MAX_MAIN_EVENTS} anstehende Hauptevents möglich.",
        )


@router.get("/events")
def list_events(db: DbSession) -> list[dict]:
    return [_event_dict(e) for e in db.scalars(select(Event).order_by(Event.start_date))]


@router.post("/events", status_code=201)
def create_event(data: EventIn, db: DbSession) -> dict:
    _check_main_limit(db, data)
    event = Event(**data.model_dump())
    db.add(event)
    db.commit()
    return _event_dict(event)


@router.put("/events/{event_id}")
def update_event(event_id: int, data: EventIn, db: DbSession) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event nicht gefunden")
    _check_main_limit(db, data, exclude_id=event_id)
    for key, value in data.model_dump().items():
        setattr(event, key, value)
    db.commit()
    return _event_dict(event)


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, db: DbSession) -> None:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event nicht gefunden")
    db.delete(event)
    db.commit()


WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


@router.get("/availability")
def read_availability(db: DbSession) -> dict:
    hours = get_availability(db)
    return {"days": [{"weekday": i, "label": WEEKDAYS[i], "hours": hours[i]} for i in range(7)]}


class AvailabilityIn(BaseModel):
    hours: list[float] = Field(min_length=7, max_length=7)


@router.put("/availability")
def write_availability(data: AvailabilityIn, db: DbSession) -> dict:
    set_availability(db, dict(enumerate(data.hours)))
    return read_availability(db)


@router.get("/plan")
def read_plan(db: DbSession) -> dict:
    plan, context = compute_plan(db)
    return {"context": context, **plan.to_dict()}


@router.get("/calendar")
def read_calendar(
    db: DbSession,
    start: Annotated[date, Query()],
    end: Annotated[date, Query()],
) -> dict:
    if end < start or (end - start).days > 62:
        raise HTTPException(status_code=422, detail="Zeitraum ungültig (max. 62 Tage)")
    return calendar(db, start, end)


OPTION_LABELS = {
    "row": "Indoor-Rudern",
    "run": "Laufen",
    "core": "Rumpf-Stabi",
}


@router.get("/options")
def read_options(db: DbSession) -> dict:
    values = get_options(db)
    return {
        "options": [{"key": k, "label": OPTION_LABELS[k], "enabled": v} for k, v in values.items()]
    }


class OptionsIn(BaseModel):
    options: dict[Literal["row", "run", "core"], bool]


@router.put("/options")
def write_options(data: OptionsIn, db: DbSession) -> dict:
    set_options(db, dict(data.options))
    return read_options(db)
