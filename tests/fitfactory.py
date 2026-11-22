"""Erzeugt synthetische FIT-Dateien für Tests (mit dem Encoder des Garmin FIT SDK)."""

from datetime import UTC, datetime

from garmin_fit_sdk import Encoder, Profile

MESG = Profile["mesg_num"]


def make_fit(
    *,
    start: datetime = datetime(2025, 6, 1, 7, 0, tzinfo=UTC),
    sport: str = "cycling",
    sub_sport: str = "road",
    duration_s: float = 7200.0,
    normalized_power: int | None = 200,
    avg_hr: int | None = 140,
    ftp: int | None = 250,
    lthr: int | None = 165,
    serial: int = 123,
) -> bytes:
    encoder = Encoder()
    encoder.write_mesg(
        {
            "mesg_num": MESG["FILE_ID"],
            "type": "activity",
            "manufacturer": "garmin",
            "product": 1,
            "serial_number": serial,
            "time_created": start,
        }
    )
    zones = {"mesg_num": MESG["ZONES_TARGET"]}
    if ftp:
        zones["functional_threshold_power"] = ftp
    if lthr:
        zones["threshold_heart_rate"] = lthr
    encoder.write_mesg(zones)

    session = {
        "mesg_num": MESG["SESSION"],
        "timestamp": start,
        "start_time": start,
        "sport": sport,
        "sub_sport": sub_sport,
        "total_elapsed_time": duration_s + 120,
        "total_timer_time": duration_s,
        "total_distance": 60000.0,
        "total_ascent": 500,
    }
    if normalized_power:
        session.update(avg_power=normalized_power - 20, normalized_power=normalized_power)
        session["total_work"] = (normalized_power - 20) * int(duration_s)
    if avg_hr:
        session.update(avg_heart_rate=avg_hr, max_heart_rate=avg_hr + 30)
    encoder.write_mesg(session)
    encoder.write_mesg(
        {"mesg_num": MESG["ACTIVITY"], "timestamp": start, "num_sessions": 1, "type": "manual"}
    )
    return encoder.close()


def make_non_activity_fit() -> bytes:
    """Eine FIT-Datei ohne Session (wie Monitoring-Dateien im Garmin-Export)."""
    encoder = Encoder()
    encoder.write_mesg(
        {
            "mesg_num": MESG["FILE_ID"],
            "type": "monitoring_b",
            "manufacturer": "garmin",
            "product": 1,
            "serial_number": 1,
            "time_created": datetime(2025, 6, 1, tzinfo=UTC),
        }
    )
    return encoder.close()
