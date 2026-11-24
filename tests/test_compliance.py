import hashlib
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from fitfactory import make_fit
from sqlalchemy import select
from typer.testing import CliRunner

from trainingsplan.analytics.compliance import evaluate_day, score_pair
from trainingsplan.cli import app as cli
from trainingsplan.planning.planner import PlanEvent, build_plan
from trainingsplan.planning.service import save_snapshot
from trainingsplan.storage.db import get_sessionmaker, init_db
from trainingsplan.storage.models import Activity, PlanCompliance, PlannedWorkout
from trainingsplan.web.app import app

DAY = date(2025, 6, 1)


def planned(kind="endurance", hours=2.0, tss=100, position=0, day=DAY, title=None):
    return PlannedWorkout(
        day=day,
        position=position,
        kind=kind,
        title=title or kind,
        hours=hours,
        tss=tss,
        description="",
    )


def activity(
    n, sport="cycling", sub="road", hours=2.0, tss=100, intensity=0.65, ebike=False, day=DAY
):
    return Activity(
        source="t",
        source_id=str(n),
        sport=sport,
        sub_sport=sub,
        is_ebike=ebike,
        start_time=datetime.combine(day, datetime.min.time(), UTC) + timedelta(hours=8 + n),
        moving_time_s=hours * 3600,
        tss=tss,
        intensity_factor=intensity,
        content_hash=hashlib.sha256(str(n).encode()).hexdigest(),
    )


def test_perfect_match_scores_ten():
    assert score_pair(planned(), activity(1)).total == 10


def test_shorter_and_harder_loses_points():
    s = score_pair(planned(), activity(1, hours=1.0, tss=70, intensity=0.85))
    assert 3 < s.total < 7
    assert "kürzer" in s.note and "intensiver" in s.note


def test_other_endurance_sport_gets_partial_sport_points():
    s = score_pair(planned(), activity(1, sport="running", sub="generic"))
    assert s.sport == 1


@pytest.fixture
def db():
    init_db()
    with get_sessionmaker()() as session:
        yield session


def _scores(db):
    return {c.activity_id: c for c in db.scalars(select(PlanCompliance))}


def test_day_matches_each_activity_to_best_planned_session(db):
    db.add_all([planned("sweetspot", 1.5, 108, 0), planned("core", 0.25, 6, 1)])
    bike = activity(1, hours=1.5, tss=105, intensity=0.84)
    core = activity(2, sport="training", sub="strength_training", hours=0.3, tss=8, intensity=None)
    commute = activity(3, hours=0.5, tss=30, ebike=True)
    db.add_all([bike, core, commute])
    db.flush()
    evaluate_day(db, DAY)
    scores = _scores(db)
    assert scores[bike.id].planned_kind == "sweetspot" and scores[bike.id].score >= 9
    assert scores[core.id].planned_kind == "core" and scores[core.id].score >= 8
    assert commute.id not in scores  # eBike-Pendeln wird nicht bewertet


def test_training_on_rest_day(db):
    db.add(planned("rest", 0, 0))
    easy, hard = activity(1, hours=0.75, tss=35, intensity=0.55), activity(2, hours=3, tss=200)
    db.add_all([easy, hard])
    db.flush()
    evaluate_day(db, DAY)
    scores = _scores(db)
    assert scores[easy.id].score == 6 and scores[hard.id].score == 3


def test_extra_activity_is_marked_unplanned(db):
    db.add(planned("endurance", 1, 50))
    a, b = activity(1, hours=1, tss=50), activity(2, hours=0.5, tss=20)
    db.add_all([a, b])
    db.flush()
    evaluate_day(db, DAY)
    scores = _scores(db)
    assert scores[a.id].score == 10
    assert scores[b.id].score is None and "nicht geplant" in scores[b.id].note


def test_snapshot_keeps_past_days_and_replaces_future(db):
    avail = {0: 0.0, 1: 1.5, 2: 1.0, 3: 1.5, 4: 0.0, 5: 6.0, 6: 3.5}
    ev = [PlanEvent(1, "Ultra", date(2027, 7, 3), 5, True, 1500)]
    first = date(2026, 11, 23)
    save_snapshot(db, build_plan(first, 50, 50, 260, ev, avail), first, 260, 165)
    frozen = db.scalars(select(PlannedWorkout).where(PlannedWorkout.day == first)).all()
    later = first + timedelta(days=3)
    save_snapshot(db, build_plan(later, 20, 20, 200, ev, avail), later, 200, 165)
    kept = db.scalars(select(PlannedWorkout).where(PlannedWorkout.day == first)).all()
    assert [p.id for p in kept] == [p.id for p in frozen]
    assert {
        p.ftp_w for p in db.scalars(select(PlannedWorkout).where(PlannedWorkout.day >= later))
    } == {200}


def test_import_scores_against_frozen_plan(tmp_path, db):
    db.add(planned("sweetspot", 2.0, 144, title="Sweet Spot"))
    db.commit()
    export = tmp_path / "x"
    export.mkdir()
    (export / "ride.fit").write_bytes(make_fit())  # 2 h, IF 0,8, 128 TSS
    result = CliRunner().invoke(cli, ["import-export", str(export)])
    assert result.exit_code == 0, result.output
    assert "Passung" in result.output
    c = db.scalars(select(PlanCompliance)).one()
    assert c.planned_title == "Sweet Spot" and c.score >= 8
    with TestClient(app) as client:
        detail = client.get(f"/api/activities/{c.activity_id}").json()
    assert detail["compliance"]["score"] == c.score
    assert detail["compliance"]["rating"] == "gut"


# --- Zuordnung ------------------------------------------------------------------


def test_strength_session_is_matched_to_core_not_to_bike(db):
    """Fall aus der Praxis: morgens Krafttraining, Radeinheit kommt erst noch."""
    bike_plan, core_plan = planned("sweetspot", 1.5, 108, 0), planned("core", 0.25, 6, 1)
    db.add_all([bike_plan, core_plan])
    core = activity(1, sport="training", sub="strength_training", hours=0.3, tss=8, intensity=None)
    db.add(core)
    db.flush()
    evaluate_day(db, DAY)
    c = _scores(db)[core.id]
    assert c.planned_kind == "core" and not c.needs_confirmation


def test_strength_without_core_plan_is_not_matched_to_bike(db):
    db.add(planned("endurance", 1, 50))
    core = activity(1, sport="training", sub="strength_training", hours=0.3, tss=8, intensity=None)
    db.add(core)
    db.flush()
    evaluate_day(db, DAY)
    c = _scores(db)[core.id]
    assert c.planned_id is None and c.score is None


def test_order_in_plan_does_not_matter(db):
    db.add_all([planned("core", 0.25, 6, 0), planned("endurance", 1.0, 50, 1)])
    ride = activity(1, hours=1.0, tss=50)
    core = activity(2, sport="training", sub="strength_training", hours=0.25, tss=6, intensity=None)
    db.add_all([core, ride])
    db.flush()
    evaluate_day(db, DAY)
    scores = _scores(db)
    assert scores[ride.id].planned_kind == "endurance"
    assert scores[core.id].planned_kind == "core"


def test_two_similar_rides_for_one_plan_need_confirmation(db):
    db.add(planned("endurance", 1.0, 50))
    a, b = activity(1, hours=0.9, tss=45), activity(2, hours=1.1, tss=55)
    db.add_all([a, b])
    db.flush()
    evaluate_day(db, DAY)
    scores = _scores(db)
    assert scores[a.id].needs_confirmation and scores[b.id].needs_confirmation


def test_substitute_sport_needs_confirmation(db):
    db.add(planned("row", 0.75, 41))
    run = activity(1, sport="running", sub="generic", hours=0.75, tss=45)
    db.add(run)
    db.flush()
    evaluate_day(db, DAY)
    c = _scores(db)[run.id]
    assert c.planned_kind == "row" and c.needs_confirmation


def test_manual_assignment_is_kept_on_reevaluation(db):
    from trainingsplan.analytics.compliance import assign

    bike_plan = planned("endurance", 1.0, 50)
    db.add(bike_plan)
    a, b = activity(1, hours=0.9, tss=45), activity(2, hours=1.1, tss=55)
    db.add_all([a, b])
    db.flush()
    evaluate_day(db, DAY)
    assign(db, b, bike_plan.id)
    evaluate_day(db, DAY)
    scores = _scores(db)
    assert scores[b.id].planned_id == bike_plan.id and scores[b.id].manual
    assert scores[a.id].planned_id is None and not scores[a.id].needs_confirmation


def test_assignment_api(db):
    p = planned("endurance", 1.0, 50, day=DAY)
    db.add(p)
    a, b = activity(1, hours=0.9, tss=45), activity(2, hours=1.1, tss=55)
    db.add_all([a, b])
    db.flush()
    evaluate_day(db, DAY)
    db.commit()
    with TestClient(app) as client:
        assert len(client.get("/api/compliance/open").json()) == 2
        r = client.post(f"/api/activities/{a.id}/assignment", json={"planned_id": p.id})
        assert r.status_code == 200 and r.json()["manual"] and r.json()["score"] is not None
        assert client.get("/api/compliance/open").json() == []
        r = client.post(f"/api/activities/{b.id}/assignment", json={"planned_id": None})
        assert r.json()["score"] is None
