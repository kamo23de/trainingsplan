"""Erzeugt plausible Demo-Daten für die Entwicklung des Dashboards.

Nutzung (schreibt in einen eigenen Datenordner, nicht in deine echten Daten):

    TP_DATA_DIR=./demo-data uv run python scripts/seed_demo.py
    TP_DATA_DIR=./demo-data uv run trainingsplan serve
"""

import hashlib
import random
from datetime import UTC, datetime, timedelta

from trainingsplan.ingest.importer import apply_load
from trainingsplan.storage.db import get_sessionmaker, init_db
from trainingsplan.storage.models import Activity


def main(years: int = 4, seed: int = 7) -> None:
    rnd = random.Random(seed)
    init_db()
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    day = today - timedelta(days=365 * years)
    count = 0
    with get_sessionmaker()() as db:
        db.query(Activity).delete()
        while day <= today:
            season = 0.6 + 0.4 * (1 if 3 <= day.month <= 9 else 0.3)
            ftp = 235 + int(30 * (day - (today - timedelta(days=365 * years))).days / (365 * years))
            rides = []
            wd = day.weekday()
            if wd in (1, 3) and rnd.random() < 0.7 * season:
                rides.append(
                    ("Feierabendrunde", rnd.uniform(1.0, 1.6), rnd.uniform(0.75, 0.88), False)
                )
            if wd in (0, 2, 4) and rnd.random() < 0.5:
                rides.append(("Pendeln eBike", rnd.uniform(0.4, 0.6), 0, True))
            if wd == 5 and rnd.random() < 0.8 * season:
                rides.append(
                    ("Lange Ausfahrt", rnd.uniform(3, 6.5) * season, rnd.uniform(0.62, 0.72), False)
                )
            if wd == 6 and rnd.random() < 0.6 * season:
                rides.append(("Sonntagsrunde", rnd.uniform(2, 4), rnd.uniform(0.65, 0.75), False))
            if day.month in (4, 5, 6) and wd == 5 and rnd.random() < 0.15:
                km = rnd.choice([200, 300, 400, 600])
                rides = [(f"Brevet {km} km", km / 24, 0.6, False)]
            winter = day.month in (11, 12, 1, 2, 3)
            extras = []
            if wd == 2 and winter and rnd.random() < 0.4:
                extras.append(("Lauf", "running", "generic", rnd.uniform(0.5, 0.8), 10.5))
            if wd == 3 and winter and rnd.random() < 0.3:
                extras.append(("Indoor-Rudern", "rowing", "indoor_rowing", rnd.uniform(0.5, 0.9), 12))
            if wd in (1, 4) and rnd.random() < 0.4:
                extras.append(("Rumpf-Stabi", "training", "strength_training", 0.3, 0))
            for name, sport, sub, hours, speed in extras:
                activity = Activity(
                    source="demo", source_id=str(count), name=name,
                    start_time=day + timedelta(hours=19), sport=sport, sub_sport=sub,
                    is_ebike=False, moving_time_s=hours * 3600, elapsed_time_s=hours * 3600,
                    distance_m=hours * speed * 1000, elevation_gain_m=0,
                    avg_hr_bpm=rnd.uniform(130, 150) if speed else 105,
                    file_lthr_bpm=165,
                    content_hash=hashlib.sha256(f"demo{count}".encode()).hexdigest(),
                )
                apply_load(db, activity)
                db.add(activity)
                count += 1
            for name, hours, intensity, ebike in rides:
                start = day + timedelta(hours=rnd.choice([7, 9, 17, 18]))
                speed = 17 if ebike else rnd.uniform(24, 29)
                np_w = None if ebike else ftp * intensity
                activity = Activity(
                    source="demo",
                    source_id=str(count),
                    start_time=start,
                    name=name,
                    sport="cycling",
                    sub_sport="e_bike_fitness" if ebike else "road",
                    is_ebike=ebike,
                    moving_time_s=hours * 3600,
                    elapsed_time_s=hours * 3600 * 1.1,
                    distance_m=hours * speed * 1000,
                    elevation_gain_m=hours * rnd.uniform(150, 450),
                    normalized_power_w=np_w,
                    avg_power_w=np_w * 0.9 if np_w else None,
                    avg_hr_bpm=rnd.uniform(118, 135) if ebike else 120 + 45 * intensity,
                    file_ftp_w=ftp // 5 * 5,
                    file_lthr_bpm=165,
                    content_hash=hashlib.sha256(f"demo{count}".encode()).hexdigest(),
                )
                apply_load(db, activity)
                db.add(activity)
                count += 1
            day += timedelta(days=1)
        db.commit()
    print(f"{count} Demo-Aktivitäten angelegt.")


if __name__ == "__main__":
    main()
