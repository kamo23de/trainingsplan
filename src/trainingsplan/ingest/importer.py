"""FIT-Dateien als Aktivitäten speichern.

- Duplikate werden über den SHA-256 der Datei und die Startzeit erkannt. Dadurch
  kann dieselbe Fahrt aus Export und API kommen, ohne doppelt gezählt zu werden.
- Die Rohdatei wird unverändert unter ``data/raw/JJJJ/`` abgelegt.
- Aktivitäten außerhalb des Historienzeitraums werden übersprungen.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from trainingsplan.analytics.load import compute_load
from trainingsplan.analytics.thresholds import effective_thresholds
from trainingsplan.config import Settings
from trainingsplan.ingest.fit import FitParseError, ParsedActivity, parse_fit
from trainingsplan.storage.models import Activity


class Outcome(StrEnum):
    IMPORTED = "importiert"
    DUPLICATE = "bereits vorhanden"
    TOO_OLD = "älter als Historienzeitraum"
    NOT_ACTIVITY = "keine Aktivität"


@dataclass
class ImportStats:
    counts: dict[Outcome, int] = field(default_factory=lambda: dict.fromkeys(Outcome, 0))
    errors: list[str] = field(default_factory=list)

    def add(self, outcome: Outcome) -> None:
        self.counts[outcome] += 1

    def summary(self) -> str:
        parts = [f"{n} {o.value}" for o, n in self.counts.items() if n]
        if self.errors:
            parts.append(f"{len(self.errors)} Fehler")
        return ", ".join(parts) or "keine Dateien"


def history_cutoff(settings: Settings, now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    return now - timedelta(days=round(365.25 * settings.history_years))


def import_fit(
    db: Session,
    settings: Settings,
    data: bytes,
    *,
    source: str,
    source_id: str,
    cutoff: datetime | None = None,
    name: str | None = None,
) -> Outcome:
    digest = hashlib.sha256(data).hexdigest()
    if db.scalar(select(Activity.id).where(Activity.content_hash == digest)):
        return Outcome.DUPLICATE

    try:
        parsed = parse_fit(data)
    except FitParseError:
        return Outcome.NOT_ACTIVITY

    start = parsed.start_time.astimezone(UTC)
    if cutoff and start < cutoff:
        return Outcome.TOO_OLD
    if db.scalar(select(Activity.id).where(Activity.start_time == start)):
        return Outcome.DUPLICATE

    raw_rel = _store_raw(settings, data, start, parsed.sport)
    activity = _to_activity(parsed, start, source, source_id, digest, raw_rel)
    activity.name = name
    apply_load(db, activity)
    db.add(activity)
    db.flush()
    return Outcome.IMPORTED


def apply_load(db: Session, activity: Activity) -> None:
    """Berechnet Belastung neu (z. B. nach Änderung der FTP-Historie)."""
    thresholds = effective_thresholds(
        db, activity.start_time.date(), activity.file_ftp_w, activity.file_lthr_bpm
    )
    basis, tss, intensity = compute_load(
        duration_s=activity.moving_time_s,
        normalized_power_w=activity.normalized_power_w,
        avg_hr_bpm=activity.avg_hr_bpm,
        ftp_w=thresholds.ftp_w,
        lthr_bpm=thresholds.lthr_bpm,
        is_ebike=activity.is_ebike,
    )
    activity.load_basis = basis
    activity.tss = round(tss, 1) if tss is not None else None
    activity.intensity_factor = round(intensity, 3) if intensity is not None else None


def _store_raw(settings: Settings, data: bytes, start: datetime, sport: str) -> str:
    rel = f"raw/{start:%Y}/{start:%Y-%m-%d_%H%M%S}_{sport}.fit"
    path = settings.data_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(data)
    return rel


def _to_activity(
    p: ParsedActivity, start: datetime, source: str, source_id: str, digest: str, raw: str
) -> Activity:
    return Activity(
        source=source,
        source_id=source_id,
        start_time=start,
        sport=p.sport,
        sub_sport=p.sub_sport,
        is_ebike=p.is_ebike,
        device=p.device,
        elapsed_time_s=p.elapsed_time_s,
        moving_time_s=p.moving_time_s,
        distance_m=p.distance_m,
        elevation_gain_m=p.elevation_gain_m,
        avg_power_w=p.avg_power_w,
        normalized_power_w=p.normalized_power_w,
        work_kj=p.work_kj,
        avg_hr_bpm=p.avg_hr_bpm,
        max_hr_bpm=p.max_hr_bpm,
        file_ftp_w=p.file_ftp_w,
        file_lthr_bpm=p.file_lthr_bpm,
        device_tss=p.device_tss,
        raw_file=raw,
        content_hash=digest,
    )
