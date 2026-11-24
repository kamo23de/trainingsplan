"""Passung zwischen geplanter und absolvierter Einheit: Score von 0 bis 10.

Bewertet wird jede Aktivität gegen die für ihren Tag eingefrorene Planung
(Tabelle ``planned_workout``). Der Score setzt sich zusammen aus:

| Teil        | Punkte | Grundlage                                               |
|-------------|--------|---------------------------------------------------------|
| Sportart    | 0–2    | passt genau 2, andere Ausdauersportart 1, sonst 0       |
| Dauer       | 0–3    | Verhältnis Ist/Plan, voll bei 1, null bei ≤ 0,4 oder ≥ 2,5 |
| Belastung   | 0–3    | dasselbe für TSS                                        |
| Intensität  | 0–2    | Intensitätsfaktor im Zielbereich der Einheit            |

Zuordnung bei mehreren Einheiten am Tag: Die Reihenfolge im Plan spielt keine
Rolle. Zugeordnet wird nur, was von der Sportart her passt (gleiche Sportart oder
Ausdauer gegen Ausdauer); unter den möglichen Zuordnungen gewinnt die mit den
meisten passenden Sportarten und dem höchsten Gesamtscore. Ist das nicht eindeutig
– zwei Zuordnungen liegen fast gleichauf, oder eine Aktivität passt nur als Ersatz
mit anderer Sportart –, wird sie zur Bestätigung markiert und die App fragt nach.
Von Hand festgelegte Zuordnungen bleiben bei jeder Neubewertung erhalten.

eBike-Pendelfahrten werden nicht bewertet. Wird an einem geplanten Ruhetag
trainiert, gibt es einen festen Score: locker und kurz 6, sonst 3.
"""

from __future__ import annotations

import itertools
import json
import math
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
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


AMBIGUITY_MARGIN = 1.5  # Punkte: so nah dürfen zwei Zuordnungen nicht beieinanderliegen
EXACT_BONUS, PARTIAL_BONUS = 20.0, 5.0  # passende Sportart zuerst, dann Score


def _objective(
    assignment: dict[int, PlannedWorkout | None], scores: dict[tuple[int, int], Score]
) -> float:
    total = 0.0
    for activity_id, p in assignment.items():
        if p is None:
            continue
        s = scores[(activity_id, p.id)]
        total += s.total + (EXACT_BONUS if s.sport == 2 else PARTIAL_BONUS)
    return total


def _assignments(
    activities: list[Activity], sessions: list[PlannedWorkout], scores: dict[tuple[int, int], Score]
):
    """Alle zulässigen Zuordnungen: jede Einheit höchstens einmal, nur passende Sportarten."""
    options = [[None, *[p for p in sessions if scores[(a.id, p.id)].sport > 0]] for a in activities]
    for combo in itertools.product(*options):
        used = [p.id for p in combo if p is not None]
        if len(used) == len(set(used)):
            yield dict(zip([a.id for a in activities], combo, strict=True))


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
        for a in db.scalars(select(Activity).order_by(Activity.start_time)).all()
        if a.start_time.date() == day and category_of(a.sport, a.sub_sport, a.is_ebike) != EBIKE
    ]
    existing = {
        c.activity_id: c
        for c in db.scalars(
            select(PlanCompliance).where(
                PlanCompliance.activity_id.in_([a.id for a in activities] or [-1])
            )
        )
    }
    sessions = [p for p in planned if p.kind != "rest"]
    by_id = {p.id: p for p in sessions}

    # Von Hand festgelegte Zuordnungen bleiben stehen
    fixed: dict[int, PlannedWorkout | None] = {}
    for a in activities:
        c = existing.get(a.id)
        if c is not None and c.manual:
            fixed[a.id] = by_id.get(c.planned_id) if c.planned_id else None
    open_acts = [a for a in activities if a.id not in fixed]
    open_sessions = [p for p in sessions if p not in fixed.values()]
    scores = {(a.id, p.id): score_pair(p, a) for a in activities for p in sessions}

    ranked = sorted(
        _assignments(open_acts, open_sessions, scores), key=lambda asg: -_objective(asg, scores)
    )
    best = ranked[0] if ranked else {}
    unclear: set[int] = set()
    if len(ranked) > 1:
        top = _objective(best, scores)
        for alt in ranked[1:]:
            if top - _objective(alt, scores) >= AMBIGUITY_MARGIN:
                break
            unclear |= {aid for aid in best if alt[aid] is not best[aid]}
    for aid, p in best.items():
        if p is not None and scores[(aid, p.id)].sport < 2:
            unclear.add(aid)  # andere Sportart als geplant: Ersatz oder zusätzlich?

    for c in existing.values():
        if not c.manual:
            db.delete(c)
    db.flush()

    count = 0
    for a in activities:
        p = fixed[a.id] if a.id in fixed else best.get(a.id)
        if p is not None:
            s = scores[(a.id, p.id)]
        elif not sessions:
            s = _rest_day_score(a)
        else:
            s = Score(None, None, None, None, None, "zusätzliche Einheit, nicht geplant")
        candidates = [
            {
                "planned_id": q.id,
                "title": q.title,
                "kind": q.kind,
                "score": scores[(a.id, q.id)].total,
            }
            for q in sessions
            if scores[(a.id, q.id)].sport > 0  # nur Einheiten mit passender Sportart
        ]
        rest_ref = planned[0] if not sessions else None
        row = existing.get(a.id) if a.id in fixed else None
        values = dict(
            planned_id=p.id
            if p
            else (rest_ref.id if rest_ref and p is None and not sessions else None),
            score=s.total,
            sport_pts=s.sport,
            duration_pts=s.duration,
            load_pts=s.load,
            intensity_pts=s.intensity,
            planned_title=p.title if p else None,
            planned_kind=p.kind if p else ("rest" if not sessions else None),
            planned_hours=p.hours if p else None,
            planned_tss=p.tss if p else None,
            note=s.note,
            candidates=json.dumps(candidates, ensure_ascii=False),
            needs_confirmation=a.id in unclear and a.id not in fixed,
            manual=a.id in fixed,
        )
        if row is not None:
            for key, value in values.items():
                setattr(row, key, value)
        else:
            db.add(PlanCompliance(activity_id=a.id, **values))
        count += 1
    db.flush()
    return count


def assign(db: Session, activity: Activity, planned_id: int | None) -> None:
    """Legt die Zuordnung einer Aktivität von Hand fest (``None``: zusätzliche Einheit)
    und bewertet den Tag neu."""
    day = activity.start_time.date()
    c = db.get(PlanCompliance, activity.id)
    if c is None:
        c = PlanCompliance(activity_id=activity.id)
        db.add(c)
    c.manual = True
    c.planned_id = planned_id
    c.needs_confirmation = False
    # Eine Einheit gehört nur zu einer Aktivität: andere Handzuordnungen darauf lösen
    if planned_id is not None:
        for other in db.scalars(
            select(PlanCompliance).where(
                PlanCompliance.planned_id == planned_id,
                PlanCompliance.activity_id != activity.id,
                PlanCompliance.manual.is_(True),
            )
        ):
            other.manual = False
    db.flush()
    evaluate_day(db, day)


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
        "manual": bool(c.manual),
        "needs_confirmation": bool(c.needs_confirmation),
        "candidates": json.loads(c.candidates) if c.candidates else [],
    }


def rating(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 8:
        return "gut"
    if score >= 5:
        return "teilweise"
    return "abweichend"
