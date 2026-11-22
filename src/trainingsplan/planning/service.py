"""Verbindet den Planer mit der Datenbank: Ausgangslage, Events, Verfügbarkeit."""

from datetime import UTC, date, datetime, timedelta

import polars as pl
from sqlalchemy import select
from sqlalchemy.orm import Session

from trainingsplan.analytics.dashboard import fitness_series, load_frame
from trainingsplan.analytics.thresholds import manual_thresholds
from trainingsplan.planning.planner import DEFAULT_OPTIONS, Plan, PlanEvent, build_plan
from trainingsplan.storage.models import (
    DEFAULT_AVAILABILITY,
    Activity,
    Availability,
    Event,
    EventPriority,
    TrainingOption,
)

MAX_MAIN_EVENTS = 3


def get_availability(db: Session) -> dict[int, float]:
    rows = {a.weekday: a.hours for a in db.scalars(select(Availability))}
    if len(rows) < 7:
        for weekday, hours in DEFAULT_AVAILABILITY.items():
            if weekday not in rows:
                db.add(Availability(weekday=weekday, hours=hours))
                rows[weekday] = hours
        db.commit()
    return rows


def set_availability(db: Session, hours: dict[int, float]) -> dict[int, float]:
    get_availability(db)
    for weekday, value in hours.items():
        db.merge(Availability(weekday=weekday, hours=max(0.0, min(16.0, value))))
    db.commit()
    return get_availability(db)


def get_options(db: Session) -> dict[str, bool]:
    stored = {o.key: o.enabled for o in db.scalars(select(TrainingOption))}
    return {key: stored.get(key, default) for key, default in DEFAULT_OPTIONS.items()}


def set_options(db: Session, options: dict[str, bool]) -> dict[str, bool]:
    for key, enabled in options.items():
        if key in DEFAULT_OPTIONS:
            db.merge(TrainingOption(key=key, enabled=bool(enabled)))
    db.commit()
    return get_options(db)


def current_lthr(db: Session, df: pl.DataFrame, today: date) -> int | None:
    manual = manual_thresholds(db, today).lthr_bpm
    if manual:
        return manual
    known = df.filter(pl.col("file_lthr_bpm").is_not_null())
    return int(known.sort("start_time")["file_lthr_bpm"][-1]) if len(known) else None


def to_plan_event(e: Event) -> PlanEvent:
    return PlanEvent(
        id=e.id,
        title=e.title,
        start=e.start_date,
        days=e.days or 1,
        main=e.priority == EventPriority.MAIN,
        distance_km=e.distance_km,
        elevation_m=e.elevation_m,
    )


def current_ftp(db: Session, df: pl.DataFrame, today: date) -> int | None:
    manual = manual_thresholds(db, today).ftp_w
    if manual:
        return manual
    with_ftp = df.filter(pl.col("file_ftp_w").is_not_null() & ~pl.col("is_ebike"))
    return int(with_ftp.sort("start_time")["file_ftp_w"][-1]) if len(with_ftp) else None


def compute_plan(db: Session, today: date | None = None) -> tuple[Plan, dict]:
    """Plan ab heute (bzw. morgen, wenn heute schon trainiert wurde)."""
    today = today or datetime.now(UTC).date()
    df = load_frame(db)
    has_today = len(df.filter(pl.col("day") == today)) > 0 if len(df) else False
    plan_start = today + timedelta(days=1) if has_today else today

    ctl = atl = 0.0
    if len(df):
        series = fitness_series(df, today).filter(pl.col("day") < plan_start)
        if len(series):
            ctl, atl = float(series["ctl"][-1]), float(series["atl"][-1])

    week_start = plan_start - timedelta(days=plan_start.weekday())
    actual = {}
    if len(df):
        this_week = df.filter(pl.col("day").is_between(week_start, plan_start - timedelta(days=1)))
        actual = {
            d: float(t)
            for d, t in this_week.group_by("day").agg(pl.col("tss").fill_null(0).sum()).iter_rows()
        }

    events = [to_plan_event(e) for e in db.scalars(select(Event).order_by(Event.start_date))]
    ftp = current_ftp(db, df, today)
    plan = build_plan(
        plan_start,
        ctl,
        atl,
        ftp,
        events,
        get_availability(db),
        actual,
        options=get_options(db),
        lthr=current_lthr(db, df, today),
    )
    context = {
        "today": today.isoformat(),
        "plan_start": plan_start.isoformat(),
        "ctl": round(ctl, 1),
        "atl": round(atl, 1),
        "tsb": round(ctl - atl, 1),
        "ftp": ftp,
    }
    return plan, context


def calendar(db: Session, start: date, end: date) -> dict:
    """Ist-Aktivitäten, geplante Einheiten und Events je Tag im Zeitraum."""
    plan, context = compute_plan(db)
    activities = db.scalars(
        select(Activity)
        .where(
            Activity.start_time >= datetime.combine(start, datetime.min.time()),
            Activity.start_time < datetime.combine(end + timedelta(days=1), datetime.min.time()),
        )
        .order_by(Activity.start_time)
    ).all()
    events = db.scalars(select(Event).order_by(Event.start_date)).all()

    days: dict[str, dict] = {}
    d = start
    while d <= end:
        days[d.isoformat()] = {"activities": [], "workouts": [], "events": []}
        d += timedelta(days=1)

    for a in activities:
        key = a.start_time.date().isoformat()
        if key in days:
            days[key]["activities"].append(
                {
                    "id": a.id,
                    "name": a.name,
                    "time": a.start_time.strftime("%H:%M"),
                    "category": "eBike"
                    if a.is_ebike
                    else "Rad"
                    if a.sport == "cycling"
                    else "Sonstige",
                    "hours": round((a.moving_time_s or 0) / 3600, 2),
                    "km": round((a.distance_m or 0) / 1000, 1),
                    "tss": round(a.tss) if a.tss is not None else None,
                    "load_basis": a.load_basis,
                }
            )
    for w in plan.workouts:
        key = w.day.isoformat()
        if key in days and w.kind not in ("rest", "event"):
            days[key]["workouts"].append(
                {
                    "kind": w.kind,
                    "title": w.title,
                    "hours": w.hours,
                    "tss": w.tss,
                    "description": w.description,
                }
            )
    for e in events:
        for i in range(max(1, e.days or 1)):
            key = (e.start_date + timedelta(days=i)).isoformat()
            if key in days:
                days[key]["events"].append(
                    {
                        "id": e.id,
                        "title": e.title,
                        "main": e.priority == EventPriority.MAIN,
                        "day_index": i + 1,
                        "days": e.days or 1,
                        "distance_km": e.distance_km,
                    }
                )

    weeks = {
        w.start.isoformat(): {
            "phase": str(w.phase),
            "planned_tss": round(w.planned_tss),
            "planned_hours": round(w.planned_hours, 1),
        }
        for w in plan.weeks
    }
    return {"context": context, "days": days, "weeks": weeks, "message": plan.message}
