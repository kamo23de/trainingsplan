from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from trainingsplan.planning.planner import Phase, PlanEvent, build_plan, week_phase
from trainingsplan.storage.db import init_db
from trainingsplan.web.app import app

TODAY = date(2026, 11, 23)  # Montag
AVAIL = {0: 0.0, 1: 1.5, 2: 1.0, 3: 1.5, 4: 0.0, 5: 6.0, 6: 3.5}


def ultra(start=date(2027, 7, 3)):
    return PlanEvent(1, "Three Peaks", start, days=9, main=True, distance_km=2500)


def plan_for(events, ctl=50.0, atl=50.0):
    return build_plan(TODAY, ctl, atl, 260, events, AVAIL)


def test_without_main_event_there_is_no_plan():
    plan = plan_for([])
    assert plan.message
    assert plan.workouts == []


def test_phases_run_backwards_from_main_event():
    ev = ultra()
    monday = ev.start - timedelta(days=ev.start.weekday())
    assert week_phase(monday, [ev])[0] == Phase.EVENT
    assert week_phase(monday - timedelta(weeks=1), [ev])[0] == Phase.TAPER
    assert week_phase(monday - timedelta(weeks=2), [ev])[0] == Phase.TAPER
    assert week_phase(monday - timedelta(weeks=3), [ev])[0] == Phase.SPECIFIC
    assert week_phase(monday - timedelta(weeks=6), [ev])[0] == Phase.BUILD
    assert week_phase(monday - timedelta(weeks=12), [ev])[0] == Phase.BASE
    after = monday + timedelta(weeks=2)  # Event endet in der Folgewoche
    assert week_phase(after, [ev])[0] == Phase.RECOVERY


def test_deload_every_fourth_week():
    phases = [w.phase for w in plan_for([ultra()]).weeks]
    loading = [Phase.BASE, Phase.BUILD, Phase.SPECIFIC]
    run = 0
    for p in phases:
        if p in loading:
            run += 1
            assert run <= 3, "mehr als 3 Belastungswochen am Stück"
        else:
            run = 0
    assert Phase.DELOAD in phases


def test_fitness_rises_and_form_is_positive_at_event():
    ev = ultra()
    plan = plan_for([ev], ctl=45, atl=45)
    by_day = {p["day"]: p for p in plan.projection}
    at_event = by_day[ev.start.isoformat()]
    assert at_event["ctl"] > 60
    assert at_event["tsb"] > 0


def test_workouts_respect_availability():
    plan = plan_for([ultra()])
    for w in plan.workouts:
        if w.kind in ("event", "openers"):
            continue
        assert w.hours <= AVAIL[w.day.weekday()] + 1e-9, w


def test_side_event_is_integrated_with_rest_around_it():
    brevet = PlanEvent(2, "Brevet 300", date(2027, 4, 17), days=1, main=False, distance_km=300)
    plan = plan_for([ultra(), brevet])
    by_day = {w.day: w for w in plan.workouts}
    assert by_day[brevet.start].kind == "event"
    assert by_day[brevet.start].tss > 200
    assert by_day[brevet.start - timedelta(days=1)].kind in ("openers", "rest")
    assert by_day[brevet.start + timedelta(days=1)].kind == "rest"


def test_watts_in_descriptions():
    plan = plan_for([ultra()])
    sweetspot = next(w for w in plan.workouts if w.kind == "sweetspot")
    assert "229–242 W" in sweetspot.description  # 88–93 % von 260 W


# --- API ------------------------------------------------------------------------


@pytest.fixture
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def _event(title, start, priority="B", **kw):
    return {"title": title, "start_date": start.isoformat(), "priority": priority, **kw}


def test_event_crud_and_main_limit(client):
    future = date.today() + timedelta(days=120)
    ids = []
    for i in range(3):
        r = client.post(
            "/api/events", json=_event(f"Haupt {i}", future + timedelta(days=30 * i), "A")
        )
        assert r.status_code == 201
        ids.append(r.json()["id"])
    r = client.post("/api/events", json=_event("Haupt 4", future + timedelta(days=200), "A"))
    assert r.status_code == 409

    side = client.post(
        "/api/events", json=_event("Brevet", future - timedelta(days=30), distance_km=200)
    ).json()
    r = client.put(
        f"/api/events/{side['id']}",
        json=_event("Brevet 300", future - timedelta(days=30), distance_km=300),
    )
    assert r.json()["title"] == "Brevet 300"
    assert client.delete(f"/api/events/{side['id']}").status_code == 204
    assert len(client.get("/api/events").json()) == 3


def test_plan_and_calendar_endpoints(client):
    start = date.today() + timedelta(days=100)
    client.post("/api/events", json=_event("Ultra", start, "A", days=5, distance_km=1500))
    plan = client.get("/api/plan").json()
    assert plan["weeks"] and plan["workouts"]

    first = date.today().replace(day=1)
    cal = client.get(f"/api/calendar?start={first}&end={first + timedelta(days=41)}").json()
    assert len(cal["days"]) == 42
    assert any(day["workouts"] for day in cal["days"].values())


def test_availability_roundtrip(client):
    data = client.get("/api/availability").json()
    assert [d["label"] for d in data["days"]] == ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    r = client.put("/api/availability", json={"hours": [0, 1, 1, 1, 0, 5, 4]})
    assert [d["hours"] for d in r.json()["days"]] == [0, 1, 1, 1, 0, 5, 4]


def test_deload_moves_away_from_key_side_event():
    base = plan_for([ultra()])
    deloads = [w.start for w in base.weeks if w.phase == Phase.DELOAD]
    # Ein Brevet genau in eine Entlastungswoche legen
    week = deloads[2]
    brevet = PlanEvent(9, "Brevet 400", week + timedelta(days=5), 1, False, 400)
    plan = plan_for([ultra(), brevet])
    by_start = {w.start: w for w in plan.weeks}
    assert by_start[week].phase != Phase.DELOAD
    assert "verschoben" in by_start[week].note
    assert by_start[week + timedelta(weeks=1)].phase == Phase.DELOAD
    assert by_start[week].base_phase in (Phase.BASE, Phase.BUILD, Phase.SPECIFIC)


def test_short_side_event_does_not_move_deload():
    base = plan_for([ultra()])
    week = [w.start for w in base.weeks if w.phase == Phase.DELOAD][1]
    ride = PlanEvent(9, "RTF 100", week + timedelta(days=6), 1, False, 100)
    plan = plan_for([ultra(), ride])
    assert {w.start: w for w in plan.weeks}[week].phase == Phase.DELOAD
