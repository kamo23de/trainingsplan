"""Kennzahlen und Zeitreihen für das Dashboard.

Alle Berechnungen laufen auf den Aktivitäts-Zusammenfassungen in der Datenbank.
Fitness (CTL), Ermüdung (ATL) und Form (TSB) folgen dem gängigen
Impulse-Response-Modell mit exponentiell gewichteten Mitteln über 42 bzw. 7 Tage.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import polars as pl
from sqlalchemy import select
from sqlalchemy.orm import Session

from trainingsplan.storage.models import Activity, AthleteThreshold

CTL_DAYS = 42
ATL_DAYS = 7
LONG_RIDE_HOURS = 4.0

CATEGORY_BIKE = "Rad"
CATEGORY_EBIKE = "eBike"
CATEGORY_OTHER = "Sonstige"
CATEGORIES = [CATEGORY_BIKE, CATEGORY_EBIKE, CATEGORY_OTHER]

RANGES = {"3m": 91, "1y": 365, "2y": 730, "4y": 1461}


@dataclass
class Period:
    start: date
    end: date


def period_for(range_key: str, today: date | None = None) -> Period | None:
    """``None`` bedeutet: gesamter Datenbestand."""
    today = today or datetime.now(UTC).date()
    days = RANGES.get(range_key)
    return Period(today - timedelta(days=days - 1), today) if days else None


def load_frame(db: Session) -> pl.DataFrame:
    rows = db.execute(
        select(
            Activity.id,
            Activity.start_time,
            Activity.name,
            Activity.sport,
            Activity.sub_sport,
            Activity.is_ebike,
            Activity.moving_time_s,
            Activity.distance_m,
            Activity.elevation_gain_m,
            Activity.normalized_power_w,
            Activity.avg_power_w,
            Activity.avg_hr_bpm,
            Activity.tss,
            Activity.load_basis,
            Activity.file_ftp_w,
        ).order_by(Activity.start_time)
    ).all()
    schema = {
        "id": pl.Int64,
        "start_time": pl.Datetime,
        "name": pl.Utf8,
        "sport": pl.Utf8,
        "sub_sport": pl.Utf8,
        "is_ebike": pl.Boolean,
        "moving_time_s": pl.Float64,
        "distance_m": pl.Float64,
        "elevation_gain_m": pl.Float64,
        "normalized_power_w": pl.Float64,
        "avg_power_w": pl.Float64,
        "avg_hr_bpm": pl.Float64,
        "tss": pl.Float64,
        "load_basis": pl.Utf8,
        "file_ftp_w": pl.Int64,
    }
    df = pl.DataFrame([tuple(r) for r in rows], schema=schema, orient="row")
    return df.with_columns(
        day=pl.col("start_time").dt.date(),
        hours=pl.col("moving_time_s").fill_null(0) / 3600,
        km=pl.col("distance_m").fill_null(0) / 1000,
        elevation=pl.col("elevation_gain_m").fill_null(0),
        category=pl.when(pl.col("is_ebike"))
        .then(pl.lit(CATEGORY_EBIKE))
        .when(pl.col("sport") == "cycling")
        .then(pl.lit(CATEGORY_BIKE))
        .otherwise(pl.lit(CATEGORY_OTHER)),
    )


def _in_period(df: pl.DataFrame, period: Period | None) -> pl.DataFrame:
    if period is None:
        return df
    return df.filter(pl.col("day").is_between(period.start, period.end))


def kpis(df: pl.DataFrame) -> dict:
    bike = df.filter(pl.col("category") == CATEGORY_BIKE)
    weeks = max(1, df.select(pl.col("day").dt.truncate("1w").n_unique()).item()) if len(df) else 1
    return {
        "activities": len(df),
        "hours": round(df["hours"].sum(), 1),
        "km": round(df["km"].sum()),
        "elevation_m": round(df["elevation"].sum()),
        "bike_km": round(bike["km"].sum()),
        "bike_hours_per_week": round(bike["hours"].sum() / weeks, 1),
        "long_rides": len(bike.filter(pl.col("hours") >= LONG_RIDE_HOURS)),
        "longest_ride_km": round(bike["km"].max() or 0),
    }


def fitness_series(df: pl.DataFrame, today: date | None = None) -> pl.DataFrame:
    """Tägliche Belastung und CTL/ATL/TSB über den gesamten Datenbestand."""
    if df.is_empty():
        return pl.DataFrame(
            schema={
                "day": pl.Date,
                "tss": pl.Float64,
                "ctl": pl.Float64,
                "atl": pl.Float64,
                "tsb": pl.Float64,
            }
        )
    today = today or datetime.now(UTC).date()
    first = df["day"].min()
    days = pl.DataFrame({"day": pl.date_range(first, max(today, df["day"].max()), eager=True)})
    daily = df.group_by("day").agg(pl.col("tss").fill_null(0).sum())
    series = days.join(daily, on="day", how="left").with_columns(pl.col("tss").fill_null(0))

    ctl, atl = 0.0, 0.0
    ctl_values, atl_values, tsb_values = [], [], []
    for load in series["tss"]:
        tsb_values.append(ctl - atl)  # Form am Morgen = gestrige Fitness - gestrige Ermüdung
        ctl += (load - ctl) / CTL_DAYS
        atl += (load - atl) / ATL_DAYS
        ctl_values.append(ctl)
        atl_values.append(atl)
    return series.with_columns(
        ctl=pl.Series(ctl_values), atl=pl.Series(atl_values), tsb=pl.Series(tsb_values)
    )


def weekly(df: pl.DataFrame, period: Period | None) -> dict:
    """Stunden je Woche und Kategorie, plus Distanz und TSS je Woche."""
    if df.is_empty():
        return {"weeks": [], "hours": {c: [] for c in CATEGORIES}, "km": [], "tss": []}
    start = period.start if period else df["day"].min()
    end = period.end if period else df["day"].max()
    start -= timedelta(days=start.weekday())
    weeks = pl.DataFrame({"week": pl.date_range(start, end, interval="1w", eager=True)})
    data = df.with_columns(week=pl.col("day").dt.truncate("1w"))
    by_cat = data.group_by("week", "category").agg(pl.col("hours").sum())
    totals = data.group_by("week").agg(pl.col("km").sum(), pl.col("tss").fill_null(0).sum())
    out = weeks.join(totals, on="week", how="left").fill_null(0).sort("week")
    hours = {}
    for cat in CATEGORIES:
        col = (
            weeks.join(
                by_cat.filter(pl.col("category") == cat).select("week", "hours"),
                on="week",
                how="left",
            )
            .sort("week")["hours"]
            .fill_null(0)
        )
        hours[cat] = [round(v, 2) for v in col]
    return {
        "weeks": [d.isoformat() for d in out["week"]],
        "hours": hours,
        "km": [round(v, 1) for v in out["km"]],
        "tss": [round(v) for v in out["tss"]],
    }


def yearly_cumulative(df: pl.DataFrame) -> list[dict]:
    """Kumulierte Raddistanz je Kalenderjahr, je Tag des Jahres (ohne eBike)."""
    bike = df.filter(pl.col("category") == CATEGORY_BIKE)
    result = []
    for year in sorted(bike["day"].dt.year().unique().to_list()):
        per_day = (
            bike.filter(pl.col("day").dt.year() == year)
            .group_by(pl.col("day").dt.ordinal_day().alias("doy"))
            .agg(pl.col("km").sum())
            .sort("doy")
            .with_columns(pl.col("km").cum_sum())
        )
        result.append(
            {
                "year": year,
                "points": [
                    [d, round(k)] for d, k in zip(per_day["doy"], per_day["km"], strict=True)
                ],
                "total_km": round(per_day["km"].max() or 0),
            }
        )
    return result


def ftp_history(db: Session, df: pl.DataFrame) -> dict:
    """FTP laut Gerät (aus FIT-Dateien) und manuell erfasste Werte."""
    device = (
        df.filter(pl.col("file_ftp_w").is_not_null() & (pl.col("category") == CATEGORY_BIKE))
        .sort("start_time")
        .with_columns(changed=pl.col("file_ftp_w") != pl.col("file_ftp_w").shift(1))
        .filter(pl.col("changed").fill_null(True))
    )
    manual = db.scalars(
        select(AthleteThreshold)
        .where(AthleteThreshold.ftp_w.is_not(None))
        .order_by(AthleteThreshold.valid_from)
    ).all()
    return {
        "device": [
            [d.isoformat(), int(f)]
            for d, f in zip(device["day"], device["file_ftp_w"], strict=True)
        ],
        "manual": [[t.valid_from.isoformat(), t.ftp_w] for t in manual],
    }


def _activity_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "date": row["start_time"].strftime("%Y-%m-%d %H:%M"),
        "name": row["name"],
        "category": row["category"],
        "hours": round(row["hours"], 2),
        "km": round(row["km"], 1),
        "elevation_m": round(row["elevation"]),
        "np_w": round(row["normalized_power_w"]) if row["normalized_power_w"] else None,
        "avg_hr": round(row["avg_hr_bpm"]) if row["avg_hr_bpm"] else None,
        "tss": round(row["tss"]) if row["tss"] is not None else None,
        "load_basis": row["load_basis"],
    }


def long_rides(df: pl.DataFrame, limit: int = 15) -> list[dict]:
    rides = (
        df.filter((pl.col("category") == CATEGORY_BIKE) & (pl.col("hours") >= LONG_RIDE_HOURS))
        .sort("km", descending=True)
        .head(limit)
    )
    return [_activity_row(r) for r in rides.iter_rows(named=True)]


def recent(df: pl.DataFrame, limit: int = 12) -> list[dict]:
    return [
        _activity_row(r)
        for r in df.sort("start_time", descending=True).head(limit).iter_rows(named=True)
    ]


def build_dashboard(db: Session, range_key: str = "1y", today: date | None = None) -> dict:
    today = today or datetime.now(UTC).date()
    period = period_for(range_key, today)
    df = load_frame(db)
    selected = _in_period(df, period)

    fitness = fitness_series(df, today)
    current = fitness.filter(pl.col("day") <= today).tail(1)
    fitness_view = (
        fitness
        if period is None
        else fitness.filter(pl.col("day").is_between(period.start, period.end))
    )
    return {
        "range": range_key,
        "period": {
            "start": (
                period.start if period else (df["day"].min() if len(df) else today)
            ).isoformat(),
            "end": (period.end if period else today).isoformat(),
        },
        "kpis": kpis(selected),
        "current": {
            "ctl": round(current["ctl"].item(), 1) if len(current) else None,
            "atl": round(current["atl"].item(), 1) if len(current) else None,
            "tsb": round(current["tsb"].item(), 1) if len(current) else None,
        },
        "fitness": {
            "days": [d.isoformat() for d in fitness_view["day"]],
            "ctl": [round(v, 1) for v in fitness_view["ctl"]],
            "atl": [round(v, 1) for v in fitness_view["atl"]],
            "tsb": [round(v, 1) for v in fitness_view["tsb"]],
        },
        "weekly": weekly(selected, period),
        "years": yearly_cumulative(df),
        "ftp": ftp_history(db, df),
        "long_rides": long_rides(selected),
        "recent": recent(df),
        "load_basis_counts": {
            k: int(v) for k, v in selected.group_by("load_basis").len().iter_rows()
        }
        if len(selected)
        else {},
    }
