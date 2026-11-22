"""FIT-Dateien lesen und auf eine Aktivitäts-Zusammenfassung abbilden.

Genutzt wird das offizielle Garmin FIT SDK. Aus der Datei werden gelesen:
- ``session``: Dauer, Distanz, Höhenmeter, Leistung, Herzfrequenz, Sportart
- ``zones_target`` bzw. ``session.threshold_power``: FTP und Schwellenpuls, die zum
  Zeitpunkt der Aufzeichnung auf dem Gerät eingestellt waren
- ``file_id`` / ``device_info``: Gerät
"""

from dataclasses import dataclass
from datetime import datetime

from garmin_fit_sdk import Decoder, Stream

EBIKE_SPORTS = {"e_biking"}
EBIKE_SUB_SPORTS = {"e_bike_fitness", "e_bike_mountain", "e_bike_enduro"}


class FitParseError(ValueError):
    pass


@dataclass
class ParsedActivity:
    start_time: datetime
    sport: str
    sub_sport: str | None
    is_ebike: bool
    elapsed_time_s: float | None
    moving_time_s: float | None
    distance_m: float | None
    elevation_gain_m: float | None
    avg_power_w: float | None
    normalized_power_w: float | None
    work_kj: float | None
    avg_hr_bpm: float | None
    max_hr_bpm: float | None
    file_ftp_w: int | None
    file_lthr_bpm: int | None
    device_tss: float | None
    device: str | None


def _str(value) -> str | None:
    return None if value is None else str(value)


def _num(value) -> float | None:
    # Das SDK liefert für unbekannte Enum-Werte Zahlen, für fehlende Werte None
    return float(value) if isinstance(value, int | float) else None


def parse_fit(data: bytes) -> ParsedActivity:
    """Liest eine Aktivitäts-FIT-Datei. Wirft FitParseError bei Nicht-Aktivitäten."""
    stream = Stream.from_byte_array(bytearray(data))
    decoder = Decoder(stream)
    if not decoder.is_fit():
        raise FitParseError("keine FIT-Datei")
    messages, errors = decoder.read()

    sessions = messages.get("session_mesgs") or []
    if not sessions:
        # z. B. Monitoring-, Einstellungs- oder Kursdateien im Garmin-Export
        raise FitParseError("keine Aktivität (keine session-Nachricht)" + _fmt(errors))

    # Mehrsport-Dateien enthalten mehrere Sessions; wir nehmen die längste.
    session = max(sessions, key=lambda s: _num(s.get("total_timer_time")) or 0)
    start_time = session.get("start_time") or session.get("timestamp")
    if not isinstance(start_time, datetime):
        raise FitParseError("Startzeit fehlt")

    sport = _str(session.get("sport")) or "generic"
    sub_sport = _str(session.get("sub_sport"))

    zones = (messages.get("zones_target_mesgs") or [{}])[0]
    ftp = session.get("threshold_power") or zones.get("functional_threshold_power")
    lthr = zones.get("threshold_heart_rate")

    file_id = (messages.get("file_id_mesgs") or [{}])[0]
    device = _str(file_id.get("garmin_product") or file_id.get("product_name"))

    work = _num(session.get("total_work"))
    return ParsedActivity(
        start_time=start_time,
        sport=sport,
        sub_sport=sub_sport,
        is_ebike=sport in EBIKE_SPORTS or sub_sport in EBIKE_SUB_SPORTS,
        elapsed_time_s=_num(session.get("total_elapsed_time")),
        moving_time_s=_num(session.get("total_timer_time")),
        distance_m=_num(session.get("total_distance")),
        elevation_gain_m=_num(session.get("total_ascent")),
        avg_power_w=_num(session.get("avg_power")),
        normalized_power_w=_num(session.get("normalized_power")),
        work_kj=work / 1000 if work is not None else None,
        avg_hr_bpm=_num(session.get("avg_heart_rate")),
        max_hr_bpm=_num(session.get("max_heart_rate")),
        file_ftp_w=int(ftp) if isinstance(ftp, int | float) and ftp > 0 else None,
        file_lthr_bpm=int(lthr) if isinstance(lthr, int | float) and lthr > 0 else None,
        device_tss=_num(session.get("training_stress_score")),
        device=device,
    )


def _fmt(errors: list) -> str:
    return f" ({errors[0]})" if errors else ""
