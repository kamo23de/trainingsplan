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
    records: list[dict] | None = None,
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
    for record in records or []:
        encoder.write_mesg({"mesg_num": MESG["RECORD"], **record})
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


def ride_records(start: datetime, seconds: int = 1800, power=None, hr: int = 140) -> list[dict]:
    """Messpunkte im Sekundentakt; ``power`` ist eine Funktion der Sekunde."""
    from datetime import timedelta

    power = power or (lambda s: 200)
    lat0, lon0 = 53.55, 9.99
    to_semi = 2**31 / 180
    return [
        {
            "timestamp": start + timedelta(seconds=s),
            "distance": s * 8.0,
            "enhanced_speed": 8.0,
            "enhanced_altitude": 20.0 + (s % 600) / 10,
            "power": int(power(s)),
            "heart_rate": hr,
            "cadence": 88,
            "position_lat": int((lat0 + s * 0.00005) * to_semi),
            "position_long": int((lon0 + s * 0.00003) * to_semi),
        }
        for s in range(seconds)
    ]
