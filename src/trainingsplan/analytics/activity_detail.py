"""Details einer einzelnen Aktivität: Kennzahlen, Verläufe, Zonen, Bestwerte, Strecke.

Die Verläufe kommen aus den ``record``-Nachrichten der abgelegten FIT-Datei.
Für die Auswertung wird auf ein 1-Sekunden-Raster gebracht (Garmin zeichnet je
nach Einstellung in variablen Abständen auf).
"""

from datetime import datetime
from pathlib import Path

import polars as pl
from garmin_fit_sdk import Decoder, Stream
from sqlalchemy.orm import Session

from trainingsplan.analytics.categories import category_of
from trainingsplan.analytics.compliance import compliance_dict
from trainingsplan.analytics.thresholds import effective_thresholds
from trainingsplan.storage.models import Activity, PlanCompliance, PlannedWorkout

MAX_POINTS = 600  # Punkte je Verlaufskurve für die Anzeige
SEMICIRCLE_TO_DEG = 180 / 2**31

# Leistungszonen nach Coggan (Anteil der FTP, Obergrenze)
POWER_ZONES = [
    ("Z1 Aktive Erholung", 0.55),
    ("Z2 Grundlage", 0.75),
    ("Z3 Tempo", 0.90),
    ("Z4 Schwelle", 1.05),
    ("Z5 VO2max", 1.20),
    ("Z6 Anaerob", 1.50),
    ("Z7 Neuromuskulär", None),
]
# Herzfrequenzzonen nach Friel (Anteil des Schwellenpulses, Obergrenze)
HR_ZONES = [
    ("Z1 Erholung", 0.81),
    ("Z2 Grundlage", 0.90),
    ("Z3 Tempo", 0.94),
    ("Z4 Schwelle", 1.00),
    ("Z5 Hoch", None),
]
BEST_EFFORTS = [(5, "5 s"), (60, "1 min"), (300, "5 min"), (1200, "20 min"), (3600, "60 min")]


def read_records(path: Path) -> pl.DataFrame:
    """Liest die Messpunkte einer FIT-Datei als Tabelle (eine Zeile je Punkt)."""
    messages, _ = Decoder(Stream.from_file(str(path))).read()
    rows = []
    for r in messages.get("record_mesgs") or []:
        ts = r.get("timestamp")
        if not isinstance(ts, datetime):
            continue
        lat, lon = r.get("position_lat"), r.get("position_long")
        rows.append(
            {
                "ts": ts,
                "distance": _f(r.get("distance")),
                "altitude": _f(r.get("enhanced_altitude", r.get("altitude"))),
                "speed": _f(r.get("enhanced_speed", r.get("speed"))),
                "power": _f(r.get("power")),
                "hr": _f(r.get("heart_rate")),
                "cadence": _f(r.get("cadence")),
                "lat": lat * SEMICIRCLE_TO_DEG if isinstance(lat, int) else None,
                "lon": lon * SEMICIRCLE_TO_DEG if isinstance(lon, int) else None,
            }
        )
    schema = {
        "ts": pl.Datetime("us", "UTC"),
        **{
            k: pl.Float64
            for k in ("distance", "altitude", "speed", "power", "hr", "cadence", "lat", "lon")
        },
    }
    return (
        pl.DataFrame(rows, schema=schema).sort("ts").unique("ts", keep="first", maintain_order=True)
    )


def _f(value) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def to_seconds(records: pl.DataFrame) -> pl.DataFrame:
    """1-Sekunden-Raster. Lücken bis 10 s werden fortgeschrieben, längere Pausen
    zählen bei Leistung als 0 W (wie bei der Normalized-Power-Berechnung üblich)."""
    if records.is_empty():
        return records
    grid = records.with_columns(pl.col("ts").dt.truncate("1s")).unique("ts", keep="first")
    grid = grid.sort("ts").upsample("ts", every="1s")
    filled = grid.with_columns(pl.all().exclude("ts").fill_null(strategy="forward", limit=10))
    return filled.with_columns(pl.col("power").fill_null(0))


def zone_times(values: pl.Series, reference: float | None, zones: list) -> list[dict]:
    """Sekunden je Zone; ``values`` im 1-Sekunden-Raster."""
    if reference is None or values.is_empty() or values.drop_nulls().is_empty():
        return []
    ratio = values.drop_nulls() / reference
    result, lower = [], 0.0
    for name, upper in zones:
        mask = ratio >= lower if upper is None else (ratio >= lower) & (ratio < upper)
        result.append(
            {
                "zone": name,
                "seconds": int(mask.sum()),
                "from": round(lower * reference),
                "to": round(upper * reference) if upper else None,
            }
        )
        lower = upper or lower
    return result


def best_efforts(power: pl.Series) -> list[dict]:
    out = []
    for seconds, label in BEST_EFFORTS:
        if len(power) < seconds:
            continue
        best = power.rolling_mean(window_size=seconds).max()
        if best:
            out.append({"duration": label, "seconds": seconds, "watts": round(best)})
    return out


def downsample(df: pl.DataFrame, max_points: int = MAX_POINTS) -> pl.DataFrame:
    step = max(1, len(df) // max_points)
    return df.gather_every(step)


def route(records: pl.DataFrame, max_points: int = 800) -> list[list[float]]:
    pts = records.select("lat", "lon").drop_nulls()
    if pts.is_empty():
        return []
    pts = downsample(pts, max_points)
    return [[round(a, 5), round(b, 5)] for a, b in pts.iter_rows()]


def activity_detail(db: Session, activity: Activity, data_dir: Path) -> dict:
    thresholds = effective_thresholds(
        db, activity.start_time.date(), activity.file_ftp_w, activity.file_lthr_bpm
    )
    summary = {
        "id": activity.id,
        "name": activity.name,
        "start_time": activity.start_time.isoformat(),
        "sport": activity.sport,
        "sub_sport": activity.sub_sport,
        "is_ebike": activity.is_ebike,
        "category": category_of(activity.sport, activity.sub_sport, activity.is_ebike),
        "device": activity.device,
        "moving_time_s": activity.moving_time_s,
        "elapsed_time_s": activity.elapsed_time_s,
        "distance_km": round((activity.distance_m or 0) / 1000, 2),
        "elevation_m": round(activity.elevation_gain_m or 0),
        "avg_speed_kmh": round(activity.distance_m / activity.moving_time_s * 3.6, 1)
        if activity.distance_m and activity.moving_time_s
        else None,
        "avg_power_w": _round(activity.avg_power_w),
        "np_w": _round(activity.normalized_power_w),
        "work_kj": _round(activity.work_kj),
        "avg_hr": _round(activity.avg_hr_bpm),
        "max_hr": _round(activity.max_hr_bpm),
        "tss": _round(activity.tss),
        "if": activity.intensity_factor,
        "load_basis": activity.load_basis,
        "device_tss": _round(activity.device_tss),
        "ftp_w": thresholds.ftp_w,
        "lthr_bpm": thresholds.lthr_bpm,
    }

    compliance = compliance_dict(db.get(PlanCompliance, activity.id))
    if compliance and compliance["planned_id"]:
        planned = db.get(PlannedWorkout, compliance["planned_id"])
        compliance["planned_description"] = planned.description if planned else None

    raw = data_dir / activity.raw_file if activity.raw_file else None
    if raw is None or not raw.exists():
        return {
            "summary": summary,
            "streams": None,
            "raw_file_missing": True,
            "compliance": compliance,
        }

    records = read_records(raw)
    seconds = to_seconds(records)
    has_power = not activity.is_ebike and records["power"].drop_nulls().len() > 0
    view = downsample(records)
    start = records["ts"].min() if len(records) else None

    def col(name, factor=1.0, digits=1):
        return [None if v is None else round(v * factor, digits) for v in view[name]]

    streams = {
        "minutes": [round((t - start).total_seconds() / 60, 2) for t in view["ts"]]
        if start
        else [],
        "distance_km": col("distance", 0.001, 2),
        "altitude": col("altitude", 1, 0),
        "speed": col("speed", 3.6, 1),
        "power": col("power", 1, 0) if has_power else [],
        "hr": col("hr", 1, 0),
        "cadence": col("cadence", 1, 0),
    }
    return {
        "summary": summary,
        "streams": streams,
        "power_zones": zone_times(seconds["power"], thresholds.ftp_w, POWER_ZONES)
        if has_power
        else [],
        "hr_zones": zone_times(seconds["hr"], thresholds.lthr_bpm, HR_ZONES),
        "best_efforts": best_efforts(seconds["power"]) if has_power else [],
        "route": route(records),
        "raw_file_missing": False,
        "compliance": compliance,
    }


def _round(value):
    return round(value) if value is not None else None
