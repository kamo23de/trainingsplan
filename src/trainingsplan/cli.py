"""Kommandozeile: `uv run trainingsplan --help`."""

import typer

from trainingsplan.config import get_settings

app = typer.Typer(help="Trainingsplan – individuelle Trainingsplanung", no_args_is_help=True)


@app.command("init-db")
def init_db_cmd() -> None:
    """Legt Datenordner und Datenbank an."""
    from trainingsplan.storage.db import init_db

    init_db()
    typer.echo(f"Datenbank bereit: {get_settings().db_url}")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000, reload: bool = True) -> None:
    """Startet das Dashboard unter http://127.0.0.1:8000."""
    import uvicorn

    uvicorn.run("trainingsplan.web.app:app", host=host, port=port, reload=reload)


@app.command("garmin-key")
def garmin_key() -> None:
    """Speichert den Garmin Personal API Key im Schlüsselbund."""
    from trainingsplan.credentials import set_garmin_api_key

    value = typer.prompt("Garmin Personal API Key", hide_input=True)
    set_garmin_api_key(value.strip())
    typer.echo("Gespeichert im Schlüsselbund (Dienst: trainingsplan).")


@app.command("garmin-check")
def garmin_check() -> None:
    """Prüft, ob mit dem hinterlegten Key ein Access Token abgerufen werden kann."""
    from trainingsplan.sources.garmin_api import GarminAuthError, GarminPersonalClient

    try:
        GarminPersonalClient().access_token()
    except GarminAuthError as exc:
        typer.echo(f"Fehler: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo("Verbindung zu Garmin funktioniert – Access Token erhalten.")


@app.command("scan-export")
def scan_export() -> None:
    """Zählt die FIT-Dateien im Garmin-Export (ohne zu importieren)."""
    from trainingsplan.sources.garmin_export import iter_fit_files

    settings = get_settings()
    settings.ensure_dirs()
    count = sum(1 for _ in iter_fit_files(settings.export_dir))
    typer.echo(f"{count} FIT-Dateien gefunden in {settings.export_dir}")


if __name__ == "__main__":
    app()
