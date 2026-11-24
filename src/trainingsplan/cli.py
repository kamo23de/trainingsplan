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
def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = True,
    access_log: bool = typer.Option(True, help="Jeden Seitenaufruf protokollieren"),
) -> None:
    """Startet das Dashboard unter http://127.0.0.1:8000."""
    import uvicorn

    uvicorn.run(
        "trainingsplan.web.app:app", host=host, port=port, reload=reload, access_log=access_log
    )


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
    quiet: bool = typer.Option(
        False, "--quiet", help="Nur eine Zeile mit Zeitstempel ausgeben (für den Hintergrunddienst)"
    ),
) -> None:
    """Holt neue Aktivitäten über die Garmin Personal API."""
    say = (lambda *a, **k: None) if quiet else typer.echo
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
        say(f"Rufe Aktivitäten ab {start_date} ab …")

        # Planung von heute einfrieren, bevor neue Aktivitäten sie verschieben
        from trainingsplan.planning.service import compute_plan

        compute_plan(db)
        first_new = _next_activity_id(db)

        try:
            client = open_client()
        except GarminAuthError as exc:
            typer.echo(f"{datetime.now():%Y-%m-%d %H:%M} Fehler: {exc}", err=True)
            raise typer.Exit(1) from exc

        with client:
            summaries = list(iter_activities(client, start_date, datetime.now(UTC).date()))
            say(f"{len(summaries)} Aktivitäten gefunden")
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
                    say(f"… {i}/{len(summaries)}")
        db.commit()
        _score_new_activities(db, first_new)

    stamp = f"{datetime.now():%Y-%m-%d %H:%M} sync: " if quiet else "Fertig: "
    typer.echo(f"{stamp}{stats.summary()}")
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


# --- Hintergrunddienste (macOS) ---------------------------------------------------

service_app = typer.Typer(help="Hintergrunddienste auf dem Mac: Server und stündlicher Abruf")
app.add_typer(service_app, name="service")


@service_app.command("install")
def service_install(
    interval: int = typer.Option(60, min=15, max=1440, help="Abruf alle … Minuten"),
    port: int = typer.Option(8000, help="Port des Servers"),
    server: bool = typer.Option(True, help="Auch den Server als Dienst starten"),
) -> None:
    """Richtet die Dienste ein (oder aktualisiert sie) und startet sie sofort."""
    from trainingsplan import service

    try:
        cfg = service.ServiceConfig(uv=service.find_uv(), port=port, interval_minutes=interval)
        service._check_platform()
        written = service.install(cfg, with_server=server)
    except service.ServiceError as exc:
        typer.echo(f"Fehler: {exc}", err=True)
        raise typer.Exit(1) from exc
    for path in written:
        typer.echo(f"Eingerichtet: {path}")
    if server:
        typer.echo(
            f"Server läuft unter http://127.0.0.1:{port} – auch nach Neustart und Anmeldung."
        )
    typer.echo(f"Garmin-Abruf alle {interval} Minuten. Protokolle: {cfg.log_dir}")
    typer.echo(
        "Beim ersten Abruf fragt macOS evtl., ob der Zugriff auf den Schlüsselbund erlaubt ist: "
        "„Immer erlauben“ wählen."
    )


@service_app.command("uninstall")
def service_uninstall() -> None:
    """Stoppt und entfernt beide Dienste."""
    from trainingsplan import service

    removed = service.uninstall()
    typer.echo("Entfernt: " + (", ".join(p.name for p in removed) if removed else "nichts"))


@service_app.command("status")
def service_status() -> None:
    """Zeigt, ob die Dienste laufen, und die letzten Abrufe."""
    from trainingsplan import service

    names = {service.SERVER_LABEL: "Server", service.SYNC_LABEL: "Garmin-Abruf"}
    for st in service.status():
        if not st.installed:
            state = "nicht eingerichtet"
        elif st.running:
            state = "läuft"
        elif st.loaded:
            state = (
                "bereit (wartet auf den nächsten Lauf)"
                if st.label == service.SYNC_LABEL
                else "geladen, läuft aber nicht – Protokoll prüfen"
            )
        else:
            state = "eingerichtet, aber nicht geladen – `service install` erneut ausführen"
        exit_info = (
            f", letzter Exit-Code {st.last_exit}"
            if st.last_exit not in (None, "0", "(never exited)")
            else ""
        )
        typer.echo(f"{names[st.label]}: {state}{exit_info}")
    lines = service.tail(service.LOG_DIR / "sync.log", 5)
    if lines:
        typer.echo("Letzte Abrufe:")
        for line in lines:
            typer.echo(f"  {line}")


@service_app.command("logs")
def service_logs(
    which: str = typer.Argument("sync", help="sync oder server"),
    lines: int = typer.Option(40, help="Anzahl Zeilen"),
) -> None:
    """Zeigt das Protokoll eines Dienstes."""
    from trainingsplan import service

    for line in service.tail(service.LOG_DIR / f"{which}.log", lines):
        typer.echo(line)


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
