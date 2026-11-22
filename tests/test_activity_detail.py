from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from fitfactory import make_fit, ride_records
from sqlalchemy import select

from trainingsplan.config import get_settings
from trainingsplan.ingest.importer import import_fit
from trainingsplan.storage.db import get_sessionmaker, init_db
from trainingsplan.storage.models import Activity
from trainingsplan.web.app import app

START = datetime(2025, 6, 1, 7, 0, tzinfo=UTC)


def _import(data):
    init_db()
    with get_sessionmaker()() as db:
        import_fit(db, get_settings(), data, source="test", source_id="x")
        db.commit()
        return db.scalars(select(Activity)).one().id


def test_detail_with_power_zones_and_best_efforts():
    # 10 min mit 290 W (Z5 bei FTP 250), danach 20 min mit 150 W (Z2)
    records = ride_records(START, 1800, power=lambda s: 290 if s < 600 else 150)
    activity_id = _import(make_fit(start=START, duration_s=1800, records=records))
    with TestClient(app) as client:
        data = client.get(f"/api/activities/{activity_id}").json()

    assert data["raw_file_missing"] is False
    zones = {z["zone"][:2]: z["seconds"] for z in data["power_zones"]}
    assert zones["Z5"] == 600
    assert zones["Z2"] == 1200
    efforts = {e["duration"]: e["watts"] for e in data["best_efforts"]}
    assert efforts["5 min"] == 290
    assert efforts["20 min"] == pytest.approx((600 * 290 + 600 * 150) / 1200, abs=1)
    assert "60 min" not in efforts  # Fahrt kürzer als 60 min
    assert len(data["streams"]["power"]) <= 650
    assert len(data["route"]) > 10
    assert data["summary"]["ftp_w"] == 250


def test_ebike_has_no_power_analysis():
    records = ride_records(START, 600)
    activity_id = _import(
        make_fit(start=START, sub_sport="e_bike_fitness", duration_s=600, records=records)
    )
    with TestClient(app) as client:
        data = client.get(f"/api/activities/{activity_id}").json()
    assert data["power_zones"] == []
    assert data["best_efforts"] == []
    assert data["hr_zones"]  # Herzfrequenzzonen gibt es trotzdem


def test_unknown_activity_returns_404():
    init_db()
    with TestClient(app) as client:
        assert client.get("/api/activities/999").status_code == 404
