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

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class LoadBasis(StrEnum):
    POWER = "power"  # TSS aus Normalized Power und FTP
    HEART_RATE = "hr"  # hrTSS aus Herzfrequenz und Schwellenpuls
    NONE = "none"  # keine ausreichenden Daten


class GoalPriority(StrEnum):
    A = "A"  # Saisonhöhepunkt
    B = "B"  # wichtiges Zwischenziel
    C = "C"  # Trainingswettkampf / Nebenziel


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


class Goal(Base):
    """Frei definierbares Ziel; veränderbar, ohne die Historie zu verlieren."""

    __tablename__ = "goal"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(1), default=GoalPriority.A)
    event_date: Mapped[date | None] = mapped_column(Date)
    distance_km: Mapped[float | None] = mapped_column(Float)
    elevation_m: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
