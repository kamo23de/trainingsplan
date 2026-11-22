"""Welche FTP und welcher Schwellenpuls galten an einem Tag?

Reihenfolge:
1. Manuell gepflegte Werte (Tabelle ``athlete_threshold``), gültig ab ``valid_from``
2. Werte, die das Gerät in der FIT-Datei hinterlegt hat
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from trainingsplan.storage.models import AthleteThreshold


@dataclass
class Thresholds:
    ftp_w: int | None
    lthr_bpm: int | None


def manual_thresholds(db: Session, day: date) -> Thresholds:
    """Jeweils der jüngste Wert mit ``valid_from <= day`` (je Kennzahl getrennt)."""

    def latest(column):
        return db.scalar(
            select(column)
            .where(AthleteThreshold.valid_from <= day, column.is_not(None))
            .order_by(AthleteThreshold.valid_from.desc())
            .limit(1)
        )

    return Thresholds(
        ftp_w=latest(AthleteThreshold.ftp_w),
        lthr_bpm=latest(AthleteThreshold.lthr_bpm),
    )


def effective_thresholds(
    db: Session, day: date, file_ftp_w: int | None, file_lthr_bpm: int | None
) -> Thresholds:
    manual = manual_thresholds(db, day)
    return Thresholds(
        ftp_w=manual.ftp_w or file_ftp_w,
        lthr_bpm=manual.lthr_bpm or file_lthr_bpm,
    )
