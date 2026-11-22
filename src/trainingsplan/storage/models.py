"""Datenmodell.

Grundsätze:
- Rohdaten (FIT-Dateien) bleiben unverändert auf der Platte; die Datenbank hält
  Zusammenfassungen pro Aktivität und Verweise auf die Rohdatei.
- Leistungswerte (FTP, Schwellenpuls) und Ziele haben einen Gültigkeitszeitraum,
  damit historische Belastungswerte mit den damals gültigen Schwellen berechnet werden.
- Jede Aktivität speichert, auf welcher Grundlage ihre Belastung berechnet wurde
  (Leistung oder Herzfrequenz), z. B. für eBike-Fahrten ohne Leistungsmesser.
"""

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class LoadBasis(StrEnum):
    POWER = "power"  # TSS aus Normalized Power und FTP
    HEART_RATE = "hr"  # hrTSS aus Herzfrequenz und Schwellenpuls
    NONE = "none"  # keine ausreichenden Daten


class EventPriority(StrEnum):
    MAIN = "A"  # Hauptevent: Saisonhöhepunkt, auf den der Plan hinarbeitet
    SIDE = "B"  # Nebenevent: Aufbauevent, wird in den Plan integriert


class Activity(Base):
    __tablename__ = "activity"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_activity_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32))  # "garmin_export", "garmin_api"
    source_id: Mapped[str] = mapped_column(String(64))

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    sport: Mapped[str] = mapped_column(String(32))  # FIT "sport", z. B. "cycling"
    sub_sport: Mapped[str | None] = mapped_column(String(32))  # z. B. "road", "e_bike"
    is_ebike: Mapped[bool] = mapped_column(default=False)
    device: Mapped[str | None] = mapped_column(String(64))

    elapsed_time_s: Mapped[float | None] = mapped_column(Float)
    moving_time_s: Mapped[float | None] = mapped_column(Float)
    distance_m: Mapped[float | None] = mapped_column(Float)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float)

    avg_power_w: Mapped[float | None] = mapped_column(Float)
    normalized_power_w: Mapped[float | None] = mapped_column(Float)
    work_kj: Mapped[float | None] = mapped_column(Float)
    avg_hr_bpm: Mapped[float | None] = mapped_column(Float)
    max_hr_bpm: Mapped[float | None] = mapped_column(Float)

    load_basis: Mapped[str] = mapped_column(String(8), default=LoadBasis.NONE)
    intensity_factor: Mapped[float | None] = mapped_column(Float)
    tss: Mapped[float | None] = mapped_column(Float)

    # Werte, die das Gerät zum Zeitpunkt der Aufzeichnung in der FIT-Datei hinterlegt hat
    file_ftp_w: Mapped[int | None] = mapped_column(Integer)
    file_lthr_bpm: Mapped[int | None] = mapped_column(Integer)
    device_tss: Mapped[float | None] = mapped_column(Float)  # vom Gerät berechnet, zum Vergleich

    raw_file: Mapped[str | None] = mapped_column(Text)  # Pfad relativ zu data_dir
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)  # SHA-256 der FIT-Datei
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class AthleteThreshold(Base):
    """Leistungsschwellen mit Gültigkeitsbeginn (gilt bis zum nächsten Eintrag)."""

    __tablename__ = "athlete_threshold"

    id: Mapped[int] = mapped_column(primary_key=True)
    valid_from: Mapped[date] = mapped_column(Date, index=True, unique=True)
    ftp_w: Mapped[int | None] = mapped_column(Integer)
    lthr_bpm: Mapped[int | None] = mapped_column(Integer)  # Schwellenpuls
    max_hr_bpm: Mapped[int | None] = mapped_column(Integer)
    rest_hr_bpm: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text)


class Event(Base):
    """Geplantes Event. Hauptevents (max. 3) bestimmen die Periodisierung,
    Nebenevents werden als Aufbauevents in den Plan eingebaut."""

    __tablename__ = "event"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[date] = mapped_column(Date, index=True)
    days: Mapped[int] = mapped_column(Integer, default=1)  # Dauer in Tagen (Etappen/Ultra)
    priority: Mapped[str] = mapped_column(String(1), default=EventPriority.SIDE)
    distance_km: Mapped[float | None] = mapped_column(Float)
    elevation_m: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Availability(Base):
    """Verfügbare Trainingszeit je Wochentag (0 = Montag)."""

    __tablename__ = "availability"

    weekday: Mapped[int] = mapped_column(Integer, primary_key=True)
    hours: Mapped[float] = mapped_column(Float, default=0)


class TrainingOption(Base):
    """Ein- und ausschaltbares Ergänzungstraining (row, run, core)."""

    __tablename__ = "training_option"

    key: Mapped[str] = mapped_column(String(16), primary_key=True)
    enabled: Mapped[bool] = mapped_column(default=True)


class PlannedWorkout(Base):
    """Geplante Einheit eines Tages. Für vergangene Tage eingefroren, damit sich
    absolvierte Aktivitäten mit dem damals gültigen Plan vergleichen lassen; für
    kommende Tage wird der Eintrag bei jeder Neuberechnung ersetzt."""

    __tablename__ = "planned_workout"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(255))
    hours: Mapped[float] = mapped_column(Float, default=0)
    tss: Mapped[float] = mapped_column(Float, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    program: Mapped[str | None] = mapped_column(String(16))
    variant: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=0)
    ftp_w: Mapped[int | None] = mapped_column(Integer)
    lthr_bpm: Mapped[int | None] = mapped_column(Integer)
    event_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PlanCompliance(Base):
    """Wie gut passt eine absolvierte Aktivität zur geplanten Einheit (0–10)?"""

    __tablename__ = "plan_compliance"

    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activity.id", ondelete="CASCADE"), primary_key=True
    )
    planned_id: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[float | None] = mapped_column(Float)
    sport_pts: Mapped[float | None] = mapped_column(Float)
    duration_pts: Mapped[float | None] = mapped_column(Float)
    load_pts: Mapped[float | None] = mapped_column(Float)
    intensity_pts: Mapped[float | None] = mapped_column(Float)
    planned_title: Mapped[str | None] = mapped_column(String(255))
    planned_kind: Mapped[str | None] = mapped_column(String(16))
    planned_hours: Mapped[float | None] = mapped_column(Float)
    planned_tss: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# Startwerte: unter der Woche kurze Einheiten nach Feierabend, am Wochenende lange Fahrten
DEFAULT_AVAILABILITY = {0: 0.0, 1: 1.5, 2: 1.0, 3: 1.5, 4: 0.0, 5: 6.0, 6: 3.5}
