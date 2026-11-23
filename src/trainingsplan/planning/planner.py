"""Trainingsplanung: periodisierter Plan auf Basis der aktuellen Fitness.

Vorgehen
--------
1. **Phasen rückwärts von jedem Hauptevent:** Tapering → spezifische Phase →
   Aufbau → Grundlage. Nach einem Hauptevent folgt Regeneration.
2. **Belastungsrhythmus 3:1:** nach drei Belastungswochen eine Entlastungswoche.
3. **Wochenbelastung (TSS) aus der Fitness:** Um die Fitness (CTL) in einer Woche um
   ``r`` Punkte zu steigern, braucht es im Mittel ``CTL + 6·r`` TSS pro Tag
   (Zeitkonstante 42 Tage). Die Steigerung ``r`` hängt von der Phase ab.
4. **Begrenzung durch die verfügbare Zeit** je Wochentag.
5. **Verteilung auf die Tage:** längste verfügbare Einheit wird die lange Fahrt,
   unter der Woche Qualitätseinheiten je nach Phase, der Rest Grundlage.
6. **Nebenevents** ersetzen die Einheit des Tages; davor wird kurz entlastet,
   danach erholt.
7. **Prognose:** Fitness, Ermüdung und Form werden Tag für Tag fortgeschrieben.

Der Plan ist eine reine Funktion seiner Eingaben und wird bei jeder Änderung
(neue Aktivität, Event, Verfügbarkeit) neu berechnet.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from enum import StrEnum

from trainingsplan.planning.workouts import (
    BIKE_KINDS,
    TSS_PER_HOUR,
    core_program,
    describe,
)

CTL_DAYS = 42
ATL_DAYS = 7
RECOVERY_EVERY = 4  # jede 4. Woche Entlastung
ULTRA_KM = 300
KEY_EVENT_KM = 150  # Nebenevents ab dieser Distanz verschieben eine Entlastungswoche


class Phase(StrEnum):
    BASE = "Grundlage"
    BUILD = "Aufbau"
    SPECIFIC = "Spezifisch"
    TAPER = "Tapering"
    EVENT = "Event"
    RECOVERY = "Regeneration"
    DELOAD = "Entlastung"


# CTL-Steigerung pro Woche (Punkte) in Belastungswochen
RAMP = {Phase.BASE: 3.0, Phase.BUILD: 4.0, Phase.SPECIFIC: 2.0}
# Wochenbelastung relativ zur Erhaltung (7 · CTL) in den übrigen Phasen
LOAD_FACTOR = {Phase.DELOAD: 0.6, Phase.RECOVERY: 0.45}


@dataclass
class PlanEvent:
    id: int | None
    title: str
    start: date
    days: int
    main: bool
    distance_km: float | None = None
    elevation_m: float | None = None

    @property
    def end(self) -> date:
        return self.start + timedelta(days=max(1, self.days) - 1)

    @property
    def is_ultra(self) -> bool:
        return (self.distance_km or 0) >= ULTRA_KM or self.days > 1

    def covers(self, day: date) -> bool:
        return self.start <= day <= self.end

    def estimated_tss_per_day(self) -> float:
        """Belastung je Eventtag, geschätzt aus der Distanz."""
        km_per_day = (self.distance_km or 100) / max(1, self.days)
        hours = km_per_day / 25
        intensity = 0.72 if km_per_day <= 150 else 0.66 if km_per_day <= 300 else 0.6
        return round(hours * intensity**2 * 100)


@dataclass
class Workout:
    day: date
    kind: str  # Schlüssel aus TSS_PER_HOUR oder "event"
    title: str
    hours: float
    tss: float
    description: str
    event_id: int | None = None
    program: str | None = None  # Übungsprogramm bei Rumpf-Einheiten (core-a/b/c, mobility)
    variant: int = 0  # Ausprägung der Einheit (für Beschreibung und Garmin-Export)
    level: int = 0  # beim Laufen: Zahl der bisher geplanten Läufe


@dataclass
class PlanWeek:
    start: date
    phase: Phase
    target_tss: float
    planned_tss: float = 0
    planned_hours: float = 0
    next_main_event: str | None = None
    weeks_to_event: int | None = None
    base_phase: Phase | None = None  # Phase ohne Entlastung, für die Übersicht
    note: str | None = None


@dataclass
class Plan:
    start: date
    end: date
    weeks: list[PlanWeek] = field(default_factory=list)
    workouts: list[Workout] = field(default_factory=list)
    projection: list[dict] = field(default_factory=list)
    message: str | None = None

    def to_dict(self) -> dict:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "message": self.message,
            "weeks": [
                {
                    **asdict(w),
                    "start": w.start.isoformat(),
                    "phase": str(w.phase),
                    "base_phase": str(w.base_phase or w.phase),
                    "target_tss": round(w.target_tss),
                    "planned_tss": round(w.planned_tss),
                    "planned_hours": round(w.planned_hours, 1),
                }
                for w in self.weeks
            ],
            "workouts": [{**asdict(w), "day": w.day.isoformat()} for w in self.workouts],
            "projection": self.projection,
        }


# ---------------------------------------------------------------------------------
# Phasen
# ---------------------------------------------------------------------------------


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_phase(week_start: date, main_events: list[PlanEvent]) -> tuple[Phase, PlanEvent | None]:
    """Phase einer Woche aus Sicht der Hauptevents (ohne 3:1-Entlastung)."""
    week_end = week_start + timedelta(days=6)
    for ev in main_events:
        if ev.start <= week_end and ev.end >= week_start:
            return Phase.EVENT, ev

    # Regeneration nach einem Hauptevent
    for ev in main_events:
        recovery_weeks = 2 if ev.is_ultra else 1
        after = (week_start - _monday(ev.end)).days // 7
        if 1 <= after <= recovery_weeks:
            return Phase.RECOVERY, ev

    upcoming = [ev for ev in main_events if ev.start > week_end]
    if not upcoming:
        return Phase.BASE, None
    ev = upcoming[0]
    weeks_to = (_monday(ev.start) - week_start).days // 7  # 1 = Woche direkt davor
    taper = 2 if ev.is_ultra else 1
    if weeks_to <= taper:
        return Phase.TAPER, ev
    if weeks_to <= taper + 3:
        return Phase.SPECIFIC, ev
    if weeks_to <= taper + 3 + 6:
        return Phase.BUILD, ev
    return Phase.BASE, ev


# ---------------------------------------------------------------------------------
# Einheiten
# ---------------------------------------------------------------------------------


def _event_text(ev: PlanEvent, day: date, km: float) -> str:
    parts = ["Hauptevent" if ev.main else "Nebenevent"]
    if ev.days > 1:
        parts.append(f"Tag {(day - ev.start).days + 1} von {ev.days}")
    if km:
        parts.append(f"ca. {round(km)} km")
    return ", ".join(parts) + ". Gleichmäßig fahren, früh und regelmäßig verpflegen."


def _round_hours(h: float) -> float:
    return round(h * 4) / 4  # auf 15 min


def _make(
    day: date,
    kind: str,
    hours: float,
    ftp: int | None,
    variant: int = 0,
    lthr: int | None = None,
    level: int = 0,
) -> Workout:
    hours = _round_hours(hours)
    if kind == "rest" or hours <= 0:
        title, text = describe("rest", 0, ftp)
        return Workout(day, "rest", title, 0, 0, text)
    title, text = describe(kind, hours, ftp, variant, lthr, level)
    program = core_program(variant) if kind == "core" else None
    return Workout(
        day,
        kind,
        title,
        hours,
        round(hours * TSS_PER_HOUR[kind]),
        text,
        program=program,
        variant=variant,
        level=level,
    )


def quality_sessions(phase: Phase, ultra: bool) -> list[str]:
    """Qualitätseinheiten unter der Woche, je Phase und Eventtyp."""
    if phase == Phase.BASE:
        return ["tempo"]
    if phase == Phase.BUILD:
        return ["sweetspot", "threshold"] if ultra else ["threshold", "vo2"]
    if phase == Phase.SPECIFIC:
        return ["sweetspot"] if ultra else ["threshold", "vo2"]
    return []


# Ergänzungstraining: wie oft Rumpf-Stabi je Phase
CORE_PER_WEEK = {
    Phase.BASE: 2,
    Phase.BUILD: 2,
    Phase.SPECIFIC: 1,
    Phase.DELOAD: 2,
    Phase.TAPER: 1,
    Phase.EVENT: 0,
    Phase.RECOVERY: 1,
}
CORE_HOURS = 0.25
RUN_START_HOURS, RUN_MAX_HOURS = 0.5, 0.75
ROW_MAX_HOURS = 1.0
DEFAULT_OPTIONS = {"row": True, "run": True, "core": True}


@dataclass
class WeekContext:
    """Was der Planer über die Woche hinaus weiß: Wochennummer für den Wechsel der
    Varianten und die Zahl bisher geplanter Läufe für den langsamen Laufaufbau."""

    index: int = 0
    runs: int = 0
    options: dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_OPTIONS))
    lthr: int | None = None
    base_phase: Phase | None = None  # Phase hinter einer Entlastungswoche


def cross_training(phase: Phase, ctx: WeekContext) -> str | None:
    """Welche Ergänzungseinheit ersetzt in dieser Woche eine Grundlage unter der Woche?

    - Grundlage: jede Woche, Rudern und Laufen im Wechsel
    - Aufbau: jede zweite Woche, bevorzugt Laufen (Knochenreiz bleibt erhalten)
    - Entlastung und Regeneration: Rudern (gelenkschonend, entlastet den Sattel)
    - Spezifisch, Tapering, Event: nur Rad – jetzt zählt die Spezifität
    """
    row, run = ctx.options.get("row"), ctx.options.get("run")
    if phase == Phase.BASE:
        if row and run:
            return "run" if ctx.index % 2 == 0 else "row"
        return "run" if run else "row" if row else None
    if phase == Phase.BUILD and ctx.index % 2 == 0:
        return "run" if run else "row" if row else None
    if phase == Phase.DELOAD and ctx.base_phase == Phase.SPECIFIC:
        return None
    if phase in (Phase.DELOAD, Phase.RECOVERY):
        return "row" if row else "run" if run and phase == Phase.DELOAD else None
    return None


def variant_for(kind: str, phase: Phase, ctx: WeekContext, day: date, used: set[str]) -> int:
    """Wählt die Variante einer Einheit, damit sich die Wochen unterscheiden.

    Pro Woche gibt es höchstens eine besondere Grundlage (Trittfrequenz oder
    Kraftausdauer); in leichten Phasen bleibt alles schlicht. Die lange Fahrt
    wechselt in der Grundlage zwischen ruhig und mit Tempo-Abschnitt, vor dem
    Event wird sie zum Ausrüstungs- und Verpflegungstest.
    """
    if phase in (Phase.TAPER, Phase.EVENT, Phase.RECOVERY, Phase.DELOAD):
        return 0
    if kind == "endurance":
        return 0 if "endurance" in used else ctx.index % 3
    if kind == "long":
        if phase == Phase.SPECIFIC:
            return 2 if day.weekday() == 5 else 0
        if phase == Phase.BASE:
            return ctx.index % 2
        return ctx.index % 3
    return ctx.index


def distribute_week(
    week_days: list[date],
    target_tss: float,
    phase: Phase,
    availability: dict[int, float],
    ftp: int | None,
    ultra: bool,
    fixed: dict[date, Workout],
    ctx: WeekContext | None = None,
) -> list[Workout]:
    """Verteilt das Wochenziel auf die Tage. ``fixed`` enthält bereits feste Tage
    (Events, Vorbelastung, Erholung). Ergebnis: eine Haupteinheit je Tag plus
    eventuelle Zusatzeinheiten (Rumpf-Stabi)."""
    ctx = ctx or WeekContext()
    free = [d for d in week_days if d not in fixed and availability.get(d.weekday(), 0) > 0]
    remaining = target_tss - sum(w.tss for w in fixed.values())
    plan: dict[date, Workout] = dict(fixed)

    # Leichte Phasen: nur Grundlage/locker, Tapering mit Vorbelastung
    easy = phase in (Phase.DELOAD, Phase.RECOVERY, Phase.TAPER, Phase.EVENT)

    # Einheitstyp je freiem Tag
    kinds: dict[date, str] = {}
    if free:
        by_hours = sorted(free, key=lambda d: (-availability[d.weekday()], d))
        weekend = [d for d in free if d.weekday() >= 5]
        # Lange Fahrt nur am Wochenende; ist es durch Events belegt, entfällt sie
        long_day = None
        if weekend:
            long_day = max(weekend, key=lambda d: availability[d.weekday()])
            kinds[long_day] = "endurance" if easy else "long"
        # Spezifische Phase für Ultras: zweiter langer Tag (Back-to-back)
        if phase == Phase.SPECIFIC and ultra:
            for d in weekend:
                if d != long_day:
                    kinds[d] = "long"
        weekdays = [d for d in by_hours if d not in kinds]
        qualities = [] if easy else quality_sessions(phase, ultra)
        for d in sorted(weekdays):
            kinds[d] = (
                qualities.pop(0)
                if qualities
                else ("recovery" if phase == Phase.RECOVERY else "endurance")
            )
        # Eine Grundlage unter der Woche wird zu Rudern oder Laufen
        cross = cross_training(phase, ctx)
        easy_weekdays = [
            d for d in sorted(free) if d.weekday() < 5 and kinds.get(d) in ("endurance", "recovery")
        ]
        if cross and easy_weekdays:
            kinds[easy_weekdays[0]] = cross

    # Dauer: verfügbare Zeit, skaliert auf das Wochenziel
    full = {d: availability[d.weekday()] for d in free}
    capacity = sum(full[d] * TSS_PER_HOUR[kinds[d]] for d in free)
    scale = min(1.0, max(0.0, remaining) / capacity) if capacity else 0
    special_used: set[str] = set()
    for d in sorted(free):
        kind = kinds[d]
        hours = full[d] * scale
        if kind == "run":
            hours = min(
                full[d],
                max(RUN_START_HOURS, min(hours, RUN_START_HOURS + 0.05 * ctx.runs, RUN_MAX_HOURS)),
            )
        elif kind == "row":
            hours = min(full[d], max(0.5, min(hours, ROW_MAX_HOURS)))
        min_hours = 0.75 if kind in ("tempo", "sweetspot", "threshold", "vo2") else 0.5
        if hours < min_hours:
            # zu kurz für die geplante Einheit: lockere Einheit oder Ruhetag
            hours = min_hours if scale > 0.25 and full[d] >= min_hours else 0
            kind = "endurance" if hours else "rest"
        plan[d] = _make(
            d, kind, hours, ftp, variant_for(kind, phase, ctx, d, special_used), ctx.lthr, ctx.runs
        )
        if kind == "endurance" and plan[d].title != "Grundlage":
            special_used.add("endurance")
        if kind == "run":
            ctx.runs += 1

    # Rumpf-Stabi als Zusatzeinheit an lockeren Tagen mit Zeit dafür
    extras: list[Workout] = []
    if ctx.options.get("core"):
        wanted = CORE_PER_WEEK.get(phase, 0)
        preference = {
            "recovery": 0,
            "row": 1,
            "endurance": 2,
            "run": 3,
            "tempo": 4,
            "sweetspot": 5,
            "threshold": 6,
            "vo2": 7,
        }
        # unter der Woche vor dem Wochenende, lockere und kurze Tage zuerst
        candidates = sorted(
            (d for d in free if plan[d].kind in preference),
            key=lambda d: (d.weekday() >= 5, preference[plan[d].kind], plan[d].hours),
        )
        # mit mindestens einem Tag Abstand, damit der Rumpf sich erholen kann
        chosen: list[date] = []
        for d in candidates:
            if len(chosen) < wanted and all(abs((d - c).days) > 1 for c in chosen):
                chosen.append(d)
        if len(chosen) < wanted:
            chosen += [d for d in candidates if d not in chosen][: wanted - len(chosen)]
        for k, d in enumerate(sorted(chosen)):
            main = plan[d]
            room = full[d] - main.hours
            if room < CORE_HOURS:
                if main.hours - CORE_HOURS < 0.5 or main.kind not in BIKE_KINDS | {"row"}:
                    continue
                plan[d] = _make(
                    d, main.kind, main.hours - CORE_HOURS, ftp, ctx.index, ctx.lthr, ctx.runs
                )
            # A/B/C im Wechsel; in leichten Phasen zuerst Mobilität
            core_variant = 3 if easy and k == 0 else (ctx.index * 2 + k) % 3
            extras.append(_make(d, "core", CORE_HOURS, ftp, core_variant))

    for d in week_days:
        plan.setdefault(d, _make(d, "rest", 0, ftp))
    return [plan[d] for d in week_days] + extras


# ---------------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------------


def build_plan(
    today: date,
    ctl: float,
    atl: float,
    ftp: int | None,
    events: list[PlanEvent],
    availability: dict[int, float],
    actual_tss_this_week: dict[date, float] | None = None,
    options: dict[str, bool] | None = None,
    lthr: int | None = None,
) -> Plan:
    """Erstellt den Plan ab ``today`` bis zwei Wochen nach dem letzten Hauptevent.
    ``options`` schaltet Ergänzungstraining (row, run, core) ein oder aus."""
    events = sorted([e for e in events if e.end >= today], key=lambda e: e.start)
    main = [e for e in events if e.main][:3]
    side = [e for e in events if not e.main]
    if not main:
        return Plan(
            today, today, message="Lege mindestens ein Hauptevent an, um einen Plan zu erstellen."
        )

    end = _monday(main[-1].end) + timedelta(days=20)  # inkl. Regeneration danach
    plan = Plan(start=today, end=end)
    actual_tss_this_week = actual_tss_this_week or {}

    week_start = _monday(today)
    ctx = WeekContext(options={**DEFAULT_OPTIONS, **(options or {})}, lthr=lthr)
    loading_weeks = 0
    sim_ctl, sim_atl = ctl, atl
    projection: list[dict] = []

    while week_start <= end:
        days = [week_start + timedelta(days=i) for i in range(7)]
        phase, ref_event = week_phase(week_start, main)

        # 3:1-Rhythmus in Belastungsphasen. Fällt die Entlastung auf eine Woche mit
        # einem längeren Nebenevent, wird sie um eine Woche verschoben: das Event ist
        # dann die Schlüsseleinheit, die Entlastung folgt direkt danach.
        base_phase = phase
        note = None
        key_event = next(
            (
                e
                for e in side
                if (e.distance_km or 0) >= KEY_EVENT_KM
                and week_start <= e.start <= week_start + timedelta(days=6)
            ),
            None,
        )
        if phase in RAMP:
            due = loading_weeks >= RECOVERY_EVERY - 1
            if due and key_event and loading_weeks < RECOVERY_EVERY:
                loading_weeks += 1
                note = f"Entlastung wegen {key_event.title} auf die Folgewoche verschoben"
            elif due:
                phase, loading_weeks = Phase.DELOAD, 0
                if plan.weeks and plan.weeks[-1].note and "verschoben" in plan.weeks[-1].note:
                    note = "Verschobene Entlastung nach dem Nebenevent"
            else:
                loading_weeks += 1
        elif phase in (Phase.TAPER, Phase.EVENT, Phase.RECOVERY):
            loading_weeks = 0

        # Wochenziel aus der Fitness zu Wochenbeginn
        maintenance = 7 * sim_ctl
        if phase in RAMP:
            target = 7 * (sim_ctl + 6 * RAMP[phase])
        elif phase == Phase.TAPER and ref_event:
            weeks_to = (_monday(ref_event.start) - week_start).days // 7
            target = maintenance * (0.6 if weeks_to <= 1 else 0.8)
        elif phase == Phase.EVENT:
            target = 0  # ergibt sich aus Event und lockeren Tagen
        elif phase == Phase.RECOVERY and ref_event:
            # Nach einem Hauptevent bewusst niedrig – unabhängig von der hohen
            # Ermüdung, die das Event selbst in CTL/ATL hinterlässt
            weeks_after = (week_start - _monday(ref_event.end)).days // 7
            target = (
                min(maintenance * 0.3, 180)
                if weeks_after == 1
                else min(maintenance * LOAD_FACTOR[Phase.RECOVERY], 350)
            )
        else:
            target = maintenance * LOAD_FACTOR.get(phase, 0.6)
        capacity = sum(
            h * TSS_PER_HOUR["long" if wd >= 5 else "sweetspot"] for wd, h in availability.items()
        )
        target = min(target, capacity)

        # Feste Tage: Events, Tage davor und danach
        fixed: dict[date, Workout] = {}
        for ev in [*main, *side]:
            for d in days:
                if ev.covers(d):
                    km = (ev.distance_km or 0) / max(1, ev.days)
                    fixed[d] = Workout(
                        d,
                        "event",
                        ev.title,
                        round(km / 25, 1),
                        ev.estimated_tss_per_day(),
                        _event_text(ev, d, km),
                        ev.id,
                    )
            before = ev.start - timedelta(days=1)
            if before in days and before not in fixed:
                fixed[before] = _make(
                    before,
                    "openers" if availability.get(before.weekday(), 0) or ev.main else "rest",
                    0.75,
                    ftp,
                )
            if ev.main or ev.is_ultra:
                before2 = ev.start - timedelta(days=2)
                if before2 in days and before2 not in fixed:
                    fixed[before2] = _make(before2, "rest", 0, ftp)
            rest_after = 2 if ev.is_ultra else 1
            for i in range(1, rest_after + 1):
                after = ev.end + timedelta(days=i)
                if after in days and after not in fixed:
                    fixed[after] = _make(
                        after, "rest" if i == 1 else "recovery", 0 if i == 1 else 0.75, ftp
                    )

        # Vergangene Tage dieser Woche: tatsächliche Belastung zählt ins Wochenziel
        past = [d for d in days if d < today]
        for d in past:
            fixed[d] = Workout(d, "done", "absolviert", 0, actual_tss_this_week.get(d, 0), "")

        if phase == Phase.EVENT:
            # Eventwoche: Eventtage fest, übrige Tage locker (ca. ein Drittel der Erhaltung)
            target = sum(w.tss for w in fixed.values()) + maintenance * 0.35

        ultra = bool(ref_event and ref_event.is_ultra)
        ctx.index = len(plan.weeks)
        ctx.base_phase = base_phase
        week_workouts = distribute_week(days, target, phase, availability, ftp, ultra, fixed, ctx)
        week_workouts = [w for w in week_workouts if w.day >= today]

        pw = PlanWeek(
            start=week_start,
            phase=phase,
            target_tss=target,
            planned_tss=sum(w.tss for w in week_workouts),
            planned_hours=sum(w.hours for w in week_workouts),
            next_main_event=ref_event.title if ref_event else None,
            weeks_to_event=((_monday(ref_event.start) - week_start).days // 7)
            if ref_event
            else None,
            base_phase=base_phase,
            note=note,
        )
        plan.weeks.append(pw)
        plan.workouts.extend(week_workouts)

        # Prognose fortschreiben
        by_day: dict[date, float] = {}
        for w in week_workouts:
            by_day[w.day] = by_day.get(w.day, 0) + w.tss
        for d in days:
            if d < today:
                continue
            load = by_day.get(d, 0)
            tsb = sim_ctl - sim_atl
            sim_ctl += (load - sim_ctl) / CTL_DAYS
            sim_atl += (load - sim_atl) / ATL_DAYS
            projection.append(
                {
                    "day": d.isoformat(),
                    "tss": load,
                    "ctl": round(sim_ctl, 1),
                    "atl": round(sim_atl, 1),
                    "tsb": round(tsb, 1),
                }
            )
        week_start += timedelta(days=7)

    plan.projection = projection
    return plan
