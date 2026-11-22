from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from garmin_fit_sdk import Decoder, Stream

from trainingsplan.config import get_settings
from trainingsplan.planning.fit_workout import build_fit, file_name, find_device_dir
from trainingsplan.planning.steps import total_seconds, workout_steps
from trainingsplan.storage.db import get_sessionmaker, init_db
from trainingsplan.storage.models import PlannedWorkout
from trainingsplan.web.app import app

BIKE = ["recovery", "openers", "endurance", "long", "tempo", "sweetspot", "threshold", "vo2"]


@pytest.mark.parametrize("kind", BIKE)
@pytest.mark.parametrize("variant", [0, 1, 2])
def test_bike_steps_fill_the_planned_time(kind, variant):
    hours = 4.5 if kind == "long" else 1.5
    seconds = total_seconds(workout_steps(kind, hours, variant))
    assert abs(seconds - hours * 3600) <= 15 * 60, (kind, variant, seconds)


def _decode(data: bytes) -> dict:
    messages, errors = Decoder(Stream.from_byte_array(bytearray(data))).read()
    assert errors == []
    return messages


def test_fit_file_contains_power_targets_in_percent_ftp():
    p = PlannedWorkout(
        id=1,
        day=date(2026, 12, 1),
        kind="sweetspot",
        title="Sweet Spot",
        hours=1.5,
        tss=108,
        variant=0,
        level=0,
    )
    msgs = _decode(build_fit(p))
    assert msgs["file_id_mesgs"][0]["type"] == "workout"
    workout = msgs["workout_mesgs"][0]
    steps = msgs["workout_step_mesgs"]
    assert workout["sport"] == "cycling" and workout["num_valid_steps"] == len(steps)
    work = [s for s in steps if s.get("wkt_step_name") == "Sweet Spot"][0]
    assert (work["custom_target_power_low"], work["custom_target_power_high"]) == (88, 93)
    repeat = [s for s in steps if s["duration_type"] == "repeat_until_steps_cmplt"][0]
    assert repeat["repeat_steps"] == 3  # 3 × 12 min wie im Text


def test_core_workout_uses_open_steps_and_ascii_names():
    p = PlannedWorkout(
        id=2,
        day=date(2026, 12, 2),
        kind="core",
        title="Rumpf C: Ultra-Spezial",
        hours=0.25,
        tss=6,
        variant=2,
        level=0,
        program="core-c",
    )
    msgs = _decode(build_fit(p))
    assert msgs["workout_mesgs"][0]["sport"] == "training"
    names = [s.get("wkt_step_name") for s in msgs["workout_step_mesgs"]]
    assert "Nacken-Isometrie" in names
    assert all(
        s["duration_type"] in ("open", "repeat_until_steps_cmplt")
        for s in msgs["workout_step_mesgs"]
    )
    assert file_name(p) == "TP_2026-12-02_Rumpf_C_Ultra_Spezial.fit"


def test_find_device_dir_on_mounted_volume(tmp_path):
    (tmp_path / "GARMIN" / "Garmin" / "NewFiles").mkdir(parents=True)
    (tmp_path / "Macintosh HD").mkdir()
    assert find_device_dir(volumes=tmp_path) == tmp_path / "GARMIN" / "Garmin" / "NewFiles"
    assert find_device_dir(volumes=tmp_path / "nichts") is None


@pytest.fixture
def planned_id():
    init_db()
    with get_sessionmaker()() as db:
        p = PlannedWorkout(
            day=date.today() + timedelta(days=2),
            position=0,
            kind="threshold",
            title="Schwelle",
            hours=1.25,
            tss=97,
            description="…",
            variant=1,
        )
        db.add(p)
        db.commit()
        return p.id


def test_api_download_and_send(planned_id, tmp_path, monkeypatch):
    device = tmp_path / "NewFiles"
    device.mkdir()
    with TestClient(app) as client:
        detail = client.get(f"/api/planned/{planned_id}").json()
        assert detail["exportable"] and detail["steps"]
        r = client.get(f"/api/planned/{planned_id}/fit")
        assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
        _decode(r.content)

        monkeypatch.setenv("TP_GARMIN_DEVICE_DIR", str(tmp_path / "fehlt"))
        get_settings.cache_clear()
        assert client.post(f"/api/planned/{planned_id}/send").status_code == 409

        monkeypatch.setenv("TP_GARMIN_DEVICE_DIR", str(device))
        get_settings.cache_clear()
        r = client.post(f"/api/planned/{planned_id}/send")
        assert r.status_code == 200
        assert list(device.glob("TP_*_Schwelle.fit"))
