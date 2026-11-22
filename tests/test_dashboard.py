import hashlib
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from trainingsplan.analytics.dashboard import CTL_DAYS, build_dashboard, fitness_series, load_frame
from trainingsplan.storage.db import get_sessionmaker, init_db
from trainingsplan.storage.models import Activity
from trainingsplan.web.app import app

TODAY = date(2026, 11, 22)


def _activity(n, day, hours, tss, *, ebike=False, km=None):
    return Activity(
        source="test",
        source_id=str(n),
        start_time=datetime.combine(day, datetime.min.time(), UTC) + timedelta(hours=9),
        name=f"Fahrt {n}",
        sport="cycling",
        sub_sport="e_bike_fitness" if ebike else "road",
        is_ebike=ebike,
        moving_time_s=hours * 3600,
        distance_m=(km if km is not None else hours * 25) * 1000,
        elevation_gain_m=300,
        tss=tss,
        load_basis="hr" if ebike else "power",
        file_ftp_w=250,
        content_hash=hashlib.sha256(str(n).encode()).hexdigest(),
    )


@pytest.fixture
def db():
    init_db()
    with get_sessionmaker()() as session:
        session.add_all(
            [
                _activity(1, TODAY - timedelta(days=1), 2, 100),
                _activity(2, TODAY - timedelta(days=3), 0.5, 30, ebike=True),
                _activity(3, TODAY - timedelta(days=200), 8, 400, km=250),
                _activity(4, TODAY - timedelta(days=700), 1, 60),
            ]
        )
        session.commit()
        yield session


def test_kpis_respect_range(db):
    one_year = build_dashboard(db, "1y", TODAY)["kpis"]
    assert one_year["activities"] == 3
    assert one_year["bike_km"] == 50 + 250  # eBike zählt nicht als Rad
    assert one_year["long_rides"] == 1
    assert one_year["longest_ride_km"] == 250
    assert build_dashboard(db, "all", TODAY)["kpis"]["activities"] == 4


def test_weekly_splits_categories(db):
    weekly = build_dashboard(db, "3m", TODAY)["weekly"]
    assert sum(weekly["hours"]["Rad"]) == pytest.approx(2)
    assert sum(weekly["hours"]["eBike"]) == pytest.approx(0.5)
    assert all(w <= TODAY.isoformat() for w in weekly["weeks"])


def test_ctl_follows_exponential_model(db):
    series = fitness_series(load_frame(db), TODAY)
    # Ein einzelner Tag mit 100 TSS ohne Vorbelastung ergibt CTL = 100/42
    day = TODAY - timedelta(days=700)
    first = series.filter(series["day"] == day)
    assert first["ctl"].item() == pytest.approx(60 / CTL_DAYS)


def test_years_are_cumulative_without_ebike(db):
    years = {y["year"]: y for y in build_dashboard(db, "all", TODAY)["years"]}
    assert years[2026]["total_km"] == 250 + 50


def test_api_endpoint_and_validation(db):
    with TestClient(app) as client:
        assert client.get("/api/dashboard?range=2y").status_code == 200
        assert client.get("/api/dashboard?range=10y").status_code == 422


def test_empty_database():
    init_db()
    with get_sessionmaker()() as session:
        data = build_dashboard(session, "1y", TODAY)
    assert data["kpis"]["activities"] == 0
    assert data["current"]["ctl"] is None


@pytest.mark.parametrize(
    ("sport", "sub_sport", "ebike", "expected"),
    [
        ("cycling", "road", False, "Rad"),
        ("cycling", "e_bike_fitness", True, "eBike"),
        ("running", "trail", False, "Laufen"),
        ("rowing", "indoor_rowing", False, "Rudern"),
        ("fitness_equipment", "indoor_rowing", False, "Rudern"),
        ("training", "strength_training", False, "Kraft"),
        ("fitness_equipment", "strength_training", False, "Kraft"),
        ("hiking", None, False, "Sonstige"),
    ],
)
def test_category_mapping(sport, sub_sport, ebike, expected):
    from trainingsplan.analytics.categories import category_of

    assert category_of(sport, sub_sport, ebike) == expected


def test_cross_training_has_own_categories(db):
    run = _activity(10, TODAY - timedelta(days=2), 0.75, 40, km=8)
    run.sport, run.sub_sport = "running", "generic"
    row = _activity(11, TODAY - timedelta(days=4), 0.5, 30, km=7)
    row.sport, row.sub_sport = "rowing", "indoor_rowing"
    core = _activity(12, TODAY - timedelta(days=5), 0.25, 8, km=0)
    core.sport, core.sub_sport = "training", "strength_training"
    db.add_all([run, row, core])
    db.commit()
    data = build_dashboard(db, "3m", TODAY)
    cats = {c["category"]: c for c in data["categories"]}
    assert (
        cats["Laufen"]["km"] == 8 and cats["Rudern"]["count"] == 1 and cats["Kraft"]["hours"] == 0.2
    )
    assert sum(data["weekly"]["hours"]["Laufen"]) == pytest.approx(0.75)
    assert data["kpis"]["cross_hours"] == pytest.approx(1.5, abs=0.1)
    assert [c["category"] for c in data["categories"]] == [
        "Rad",
        "eBike",
        "Laufen",
        "Rudern",
        "Kraft",
    ]
