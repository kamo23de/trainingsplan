"""Zentrale Konfiguration.

Alle Einstellungen kommen aus Umgebungsvariablen (Präfix ``TP_``) oder einer
``.env``-Datei. Dadurch läuft dieselbe Anwendung lokal und später auf einem
Server, ohne dass Code geändert werden muss.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TP_", env_file=".env", extra="ignore")

    data_dir: Path = Path("./data")
    database_url: str | None = None
    history_years: int = 4

    # Zielordner für Workouts auf einem per USB verbundenen Garmin-Gerät. Leer lassen:
    # die App sucht unter /Volumes nach Garmin/NewFiles.
    garmin_device_dir: Path | None = None

    # Nur für Server-Betrieb; lokal liegt der Schlüssel im macOS-Schlüsselbund.
    garmin_api_key: str | None = None

    @property
    def raw_dir(self) -> Path:
        """Ablage für unveränderte Rohdaten (FIT-Dateien)."""
        return self.data_dir / "raw"

    @property
    def export_dir(self) -> Path:
        """Ablage für den entpackten Garmin-Datenexport."""
        return self.data_dir / "garmin-export"

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'trainingsplan.db').as_posix()}"

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.raw_dir, self.export_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
