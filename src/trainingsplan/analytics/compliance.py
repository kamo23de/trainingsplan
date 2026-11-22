"""Passung zwischen geplanter und absolvierter Einheit: Score von 0 bis 10.

Bewertet wird jede Aktivität gegen die für ihren Tag eingefrorene Planung
(Tabelle ``planned_workout``). Der Score setzt sich zusammen aus:

| Teil        | Punkte | Grundlage                                               |
|-------------|--------|---------------------------------------------------------|
| Sportart    | 0–2    | passt genau 2, andere Ausdauersportart 1, sonst 0       |
| Dauer       | 0–3    | Verhältnis Ist/Plan, voll bei 1, null bei ≤ 0,4 oder ≥ 2,5 |
| Belastung   | 0–3    | dasselbe für TSS                                        |
| Intensität  | 0–2    | Intensitätsfaktor im Zielbereich der Einheit            |

Mehrere Aktivitäten an einem Tag werden den geplanten Einheiten so zugeordnet,
dass jede Einheit die am besten passende Aktivität bekommt. eBike-Pendelfahrten
werden nicht bewertet. Wird an einem geplanten Ruhetag trainiert, gibt es einen
festen Score: locker und kurz 6, sonst 3.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from trainingsplan.analytics.categories import BIKE, EBIKE, ROW, RUN, STRENGTH, category_of
from trainingsplan.planning.workouts import BIKE_KINDS
from trainingsplan.storage.models import Activity, PlanCompliance, PlannedWorkout

# Erwartete Sportart je Einheitstyp
EXPECTED = {
    **dict.fromkeys(BIKE_KINDS, BIKE),
    "event": BIKE,
    "run": RUN,
    "row": ROW,
    "core": STRENGTH,
}
ENDURANCE = {BIKE, RUN, ROW}

# Zielbereich des Intensitätsfaktors (ganze Einheit inkl. Ein- und Ausfahren)
IF_RANGE = {
    "recovery": (0.0, 0.62),
    "openers": (0.55, 0.78),
    "endurance": (0.55, 0.76),
    "long": (0.55, 0.76),
    "event": (0.5, 0.78),
    "tempo": (0.68, 0.86),
    "sweetspot": (0.74, 0.9),
    "threshold": (0.76, 0.95),
    "vo2": (0.75, 0.95),
    "row": (0.5, 0.85),
    "run": (0.5, 0.85),
}
RATIO_ZERO = math.log(2.5)  # ab Faktor 2,5 (bzw. 0,4) gibt es keine Punkte mehr


@dataclass
class Score:
    total: float | None
    sport: float | None
    duration: float | None
    load: float | None
    intensity: float | None
    note: str | None = None


def _ratio_points(actual: float | None, planned: float, max_pts: float) -> float:
    if planned <= 0:
        return max_pts
    if not actual or actual <= 0:
        return 0.0
    deviation = abs(math.log(actual / planned))
    return max_pts * max(0.0, 1 - deviation / RATIO_ZERO)


def score_pair(planned: PlannedWorkout, activity: Activity) -> Score:
    """Score einer Aktivität gegen eine geplante Einheit."""
    expected = EXPECTED.get(planned.kind)
    actual = category_of(activity.sport, activity.sub_sport, activity.is_ebike)
    if actual == expected:
        sport = 2.0
    elif expected in ENDURANCE and actual in ENDURANCE:
        sport = 1.0
    else:
        sport = 0.0

    hours = (activity.moving_time_s or 0) / 3600
    duration = _ratio_points(hours, planned.hours, 3)
    load = _ratio_points(activity.tss, planned.tss, 3) if planned.kind != "core" else duration

    rng = IF_RANGE.get(planned.kind)
    intensity_factor = activity.intensity_factor
    if rng is None:
        intensity = 2.0  # Rumpf: keine Intensitätsvorgabe
    elif intensity_factor is None:
        intensity = 1.0  # unbekannt: neutral
    else:
        lo, hi = rng
        distance = max(lo - intensity_factor, intensity_factor - hi, 0)
        intensity = 2 * max(0.0, 1 - distance / 0.12)

    notes = []
    if sport < 2:
        notes.append(f"Sportart {actual} statt {expected}")
    if planned.hours and hours < planned.hours * 0.75:
        notes.append("deutlich kürzer als geplant")
    elif planned.hours and hours > planned.hours * 1.35:
        notes.append("deutlich länger als geplant")
    if rng and intensity_factor is not None:
        if intensity_factor > rng[1] + 0.03:
            notes.append("intensiver als geplant")
        elif intensity_factor < rng[0] - 0.03:
            notes.append("lockerer als geplant")
    total = round(sport + duration + load + intensity, 1)
    return Score(
        total,
        round(sport, 1),
        round(duration, 1),
        round(load, 1),
        round(intensity, 1),
        "; ".join(notes) or None,
    )


def _rest_day_score(activity: Activity) -> Score:
    hours = (activity.moving_time_s or 0) / 3600
    easy = hours <= 1.0 and (activity.intensity_factor or 0) < 0.65
    total = 6.0 if easy else 3.0
    note = "Training an einem geplanten Ruhetag" + (" – locker, passt noch" if easy else "")
    return Score(total, 0, 0, 0, 0, note)


def evaluate_day(db: Session, day: date) -> int:
    """Bewertet alle Aktivitäten eines Tages neu. Gibt die Zahl der Bewertungen zurück.
    Ohne eingefrorene Planung für den Tag wird nichts bewertet."""
    planned = db.scalars(
        select(PlannedWorkout).where(PlannedWorkout.day == day).order_by(PlannedWorkout.position)
    ).all()
    if not planned:
        return 0
    activities = [
        a
        for a in db.scalars(select(Activity)).all()
        if a.start_time.date() == day and category_of(a.sport, a.sub_sport, a.is_ebike) != EBIKE
    ]
    db.execute(
        delete(PlanCompliance).where(
            PlanCompliance.activity_id.in_([a.id for a in activities] or [-1])
        )
    )

    sessions = [p for p in planned if p.kind != "rest"]
    results: dict[int, tuple[PlannedWorkout | None, Score]] = {}
    free = list(activities)
    # Wichtigste Einheit zuerst die beste Aktivität wählen lassen
    for p in sorted(sessions, key=lambda p: -p.tss):
        if not free:
            break
        best = max(free, key=lambda a: score_pair(p, a).total)
        results[best.id] = (p, score_pair(p, best))
        free.remove(best)
    for a in free:
        if not sessions:
            results[a.id] = (planned[0], _rest_day_score(a))
        else:
            results[a.id] = (
                None,
                Score(None, None, None, None, None, "zusätzliche Einheit, nicht geplant"),
            )

    for activity_id, (p, s) in results.items():
        db.add(
            PlanCompliance(
                activity_id=activity_id,
                planned_id=p.id if p else None,
                score=s.total,
                sport_pts=s.sport,
                duration_pts=s.duration,
                load_pts=s.load,
                intensity_pts=s.intensity,
                planned_title=p.title if p else None,
                planned_kind=p.kind if p else None,
                planned_hours=p.hours if p else None,
                planned_tss=p.tss if p else None,
                note=s.note,
            )
        )
    db.flush()
    return len(results)


def compliance_dict(c: PlanCompliance | None) -> dict | None:
    if c is None:
        return None
    return {
        "score": c.score,
        "parts": {
            "Sportart": [c.sport_pts, 2],
            "Dauer": [c.duration_pts, 3],
            "Belastung": [c.load_pts, 3],
            "Intensität": [c.intensity_pts, 2],
        }
        if c.score is not None and c.planned_kind != "rest"
        else None,
        "planned_id": c.planned_id,
        "planned_title": c.planned_title,
        "planned_kind": c.planned_kind,
        "planned_hours": c.planned_hours,
        "planned_tss": c.planned_tss,
        "note": c.note,
        "rating": rating(c.score),
    }


def rating(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 8:
        return "gut"
    if score >= 5:
        return "teilweise"
    return "abweichend"
