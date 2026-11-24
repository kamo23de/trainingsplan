"""Kommandozeile: `uv run trainingsplan --help`."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import typer

from trainingsplan.config import get_settings

app = typer.Typer(help="Trainingsplan – individuelle Trainingsplanung", no_args_is_help=True)


@app.command("init-db")
def init_db_cmd(
    reset: bool = typer.Option(False, help="Datenbank löschen und neu anlegen (Rohdaten bleiben)"),
) -> None:
    """Legt Datenordner und Datenbank an."""
    from trainingsplan.storage.db import get_engine, init_db
    from trainingsplan.storage.models import Base

    if reset:
        typer.confirm("Alle Daten in der Datenbank löschen?", abort=True)
        Base.metadata.drop_all(get_engine())
    init_db()
    typer.echo(f"Datenbank bereit: {get_settings().db_url}")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000, reload: bool = True) -> None:
    """Startet das Dashboard unter http://127.0.0.1:8000."""
    import uvicorn

    uvicorn.run("trainingsplan.web.app:app", host=host, port=port, reload=reload)


# --- Garmin-Zugang -----------------------------------------------------------------


@app.command("garmin-key")
def garmin_key() -> None:
    """Speichert den Garmin Personal API Key im Schlüsselbund."""
    from trainingsplan.credentials import set_garmin_api_key

    value = typer.prompt("Garmin Personal API Key", hide_input=True)
    set_garmin_api_key(value.strip())
    typer.echo("Gespeichert im Schlüsselbund (Dienst: trainingsplan).")


@app.command("garmin-check")
def garmin_check() -> None:
    """Prüft die Verbindung und zeigt die neueste Aktivität."""
    from trainingsplan.sources.garmin_api import GarminAuthError, iter_activities, open_client

    try:
        client = open_client()
    except GarminAuthError as exc:
        typer.echo(f"Fehler: {exc}", err=True)
        raise typer.Exit(1) from exc
    with client:
        today = date.today()
        recent = list(iter_activities(client, today - timedelta(days=30), today))
    typer.echo(f"Verbindung funktioniert. {len(recent)} Aktivitäten in den letzten 30 Tagen.")
    if recent:
        first = recent[0]
        typer.echo(f"Beispiel: {first.get('startTimeLocal')} – {first.get('activityName')}")


def _score_new_activities(db, first_new_id: int) -> None:
    """Bewertet neu importierte Aktivitäten gegen die eingefrorene Tagesplanung."""
    from sqlalchemy import select

    from trainingsplan.analytics.compliance import evaluate_day
    from trainingsplan.storage.models import Activity, PlanCompliance

    days = {
        a.start_time.date() for a in db.scalars(select(Activity).where(Activity.id >= first_new_id))
    }
    scored = sum(evaluate_day(db, day) for day in sorted(days))
    db.commit()
    if scored:
        rows = db.scalars(
            select(PlanCompliance)
            .join(Activity, Activity.id == PlanCompliance.activity_id)
            .where(Activity.id >= first_new_id, PlanCompliance.score.is_not(None))
        ).all()
        for c in rows:
            a = db.get(Activity, c.activity_id)
            hint = (
                " – Zuordnung unklar, bitte in der App bestätigen" if c.needs_confirmation else ""
            )
            typer.echo(
                f"  Passung {a.start_time:%d.%m.} {a.name or a.sport}: "
                f"{c.score:.1f}/10 ({c.planned_title or 'Ruhetag'}){hint}"
            )


def _next_activity_id(db) -> int:
    from sqlalchemy import func, select

    from trainingsplan.storage.models import Activity

    return (db.scalar(select(func.max(Activity.id))) or 0) + 1


# --- Import ------------------------------------------------------------------------


@app.command("import-export")
def import_export(
    path: Path = typer.Argument(None, help="Ordner oder ZIP; Standard: data/garmin-export"),
) -> None:
    """Importiert alle FIT-Dateien aus dem Garmin-Datenexport (einmalig für die Historie)."""
    from trainingsplan.ingest.importer import ImportStats, history_cutoff, import_fit
    from trainingsplan.sources.garmin_export import iter_fit_files
    from trainingsplan.storage.db import get_sessionmaker, init_db

    settings = get_settings()
    settings.ensure_dirs()
    init_db()
    root = path or settings.export_dir
    cutoff = history_cutoff(settings)
    stats = ImportStats()

    with get_sessionmaker()() as db:
        first_new = _next_activity_id(db)
        for i, fit in enumerate(iter_fit_files(root), start=1):
            try:
                stats.add(
                    import_fit(
                        db,
                        settings,
                        fit.data,
                        source="garmin_export",
                        source_id=fit.name,
                        cutoff=cutoff,
                    )
                )
            except Exception as exc:  # eine defekte Datei soll den Import nicht stoppen
                stats.errors.append(f"{fit.name}: {exc}")
            if i % 200 == 0:
                db.commit()
                typer.echo(f"… {i} Dateien verarbeitet")
        db.commit()
        _score_new_activities(db, first_new)

    typer.echo(f"Fertig: {stats.summary()}")
    for err in stats.errors[:10]:
        typer.echo(f"  Fehler: {err}", err=True)


@app.command()
def sync(
    since: datetime = typer.Option(
        None, formats=["%Y-%m-%d"], help="Ab Datum abrufen; Standard: ab letzter Aktivität"
    ),
) -> None:
    """Holt neue Aktivitäten über die Garmin Personal API."""
    from sqlalchemy import func, select

    from trainingsplan.ingest.importer import ImportStats, Outcome, history_cutoff, import_fit
    from trainingsplan.sources.garmin_api import (
        GarminAuthError,
        download_fit_files,
        iter_activities,
        open_client,
    )
    from trainingsplan.storage.db import get_sessionmaker, init_db
    from trainingsplan.storage.models import Activity

    settings = get_settings()
    settings.ensure_dirs()
    init_db()
    cutoff = history_cutoff(settings)
    stats = ImportStats()

    with get_sessionmaker()() as db:
        if since is None:
            latest = db.scalar(select(func.max(Activity.start_time)))
            since = (latest - timedelta(days=1)) if latest else cutoff
        start_date = max(since.date(), cutoff.date())
        typer.echo(f"Rufe Aktivitäten ab {start_date} ab …")

        # Planung von heute einfrieren, bevor neue Aktivitäten sie verschieben
        from trainingsplan.planning.service import compute_plan

        compute_plan(db)
        first_new = _next_activity_id(db)

        try:
            client = open_client()
        except GarminAuthError as exc:
            typer.echo(f"Fehler: {exc}", err=True)
            raise typer.Exit(1) from exc

        with client:
            summaries = list(iter_activities(client, start_date, datetime.now(UTC).date()))
            typer.echo(f"{len(summaries)} Aktivitäten gefunden")
            for i, summary in enumerate(summaries, start=1):
                activity_id = summary.get("activityId")
                if activity_id is None:
                    continue
                name = summary.get("activityName")
                existing = db.scalar(
                    select(Activity).where(
                        Activity.source == "garmin_api", Activity.source_id == str(activity_id)
                    )
                )
                if existing:
                    if name and not existing.name:
                        existing.name = name  # Namen nachtragen, ohne erneuten Download
                    stats.add(Outcome.DUPLICATE)
                    continue
                try:
                    for _, data in download_fit_files(client, activity_id):
                        stats.add(
                            import_fit(
                                db,
                                settings,
                                data,
                                source="garmin_api",
                                source_id=str(activity_id),
                                cutoff=cutoff,
                                name=name,
                            )
                        )
                except Exception as exc:
                    stats.errors.append(f"{activity_id}: {exc}")
                if i % 25 == 0:
                    db.commit()
                    typer.echo(f"… {i}/{len(summaries)}")
        db.commit()
        _score_new_activities(db, first_new)

    typer.echo(f"Fertig: {stats.summary()}")
    for err in stats.errors[:10]:
        typer.echo(f"  Fehler: {err}", err=True)
    if stats.errors:
        typer.echo(
            f"Fehlgeschlagene Downloads erneut versuchen: "
            f"`trainingsplan sync --since {start_date}` "
            "(bereits importierte Aktivitäten werden dabei übersprungen)."
        )


@app.command()
def score(
    since: datetime = typer.Option(None, formats=["%Y-%m-%d"], help="ab Datum; Standard: alles"),
) -> None:
    """Bewertet Aktivitäten erneut gegen die eingefrorene Tagesplanung (Score 0–10)."""
    from sqlalchemy import select

    from trainingsplan.analytics.compliance import evaluate_day
    from trainingsplan.storage.db import get_sessionmaker, init_db
    from trainingsplan.storage.models import PlannedWorkout

    init_db()
    with get_sessionmaker()() as db:
        query = select(PlannedWorkout.day).distinct()
        if since:
            query = query.where(PlannedWorkout.day >= since.date())
        days = [d for d in db.scalars(query) if d <= datetime.now(UTC).date()]
        scored = sum(evaluate_day(db, d) for d in days)
        db.commit()
    typer.echo(f"{scored} Aktivitäten an {len(days)} geplanten Tagen bewertet.")


# --- Leistungsschwellen ------------------------------------------------------------


@app.command("threshold-add")
def threshold_add(
    valid_from: datetime = typer.Argument(..., formats=["%Y-%m-%d"], help="gültig ab"),
    ftp: int = typer.Option(None, help="FTP in Watt"),
    lthr: int = typer.Option(None, help="Schwellenpuls in bpm"),
    note: str = typer.Option(None, help="Notiz, z. B. 'FTP-Test'"),
) -> None:
    """Erfasst FTP/Schwellenpuls ab einem Datum und berechnet die Belastung neu."""
    from sqlalchemy import select

    from trainingsplan.storage.db import get_sessionmaker, init_db
    from trainingsplan.storage.models import AthleteThreshold

    init_db()
    with get_sessionmaker()() as db:
        entry = db.scalar(
            select(AthleteThreshold).where(AthleteThreshold.valid_from == valid_from.date())
        ) or AthleteThreshold(valid_from=valid_from.date())
        entry.ftp_w = ftp if ftp is not None else entry.ftp_w
        entry.lthr_bpm = lthr if lthr is not None else entry.lthr_bpm
        entry.note = note or entry.note
        db.add(entry)
        db.commit()
    typer.echo("Gespeichert.")
    recompute()


@app.command()
def recompute() -> None:
    """Berechnet die Belastung (TSS) aller Aktivitäten neu."""
    from sqlalchemy import select

    from trainingsplan.ingest.importer import apply_load
    from trainingsplan.storage.db import get_sessionmaker, init_db
    from trainingsplan.storage.models import Activity

    init_db()
    with get_sessionmaker()() as db:
        activities = db.scalars(select(Activity)).all()
        for activity in activities:
            apply_load(db, activity)
        db.commit()
    typer.echo(f"Belastung für {len(activities)} Aktivitäten neu berechnet.")


if __name__ == "__main__":
    app()
