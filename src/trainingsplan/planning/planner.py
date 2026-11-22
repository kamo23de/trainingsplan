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

CTL_DAYS = 42
ATL_DAYS = 7
RECOVERY_EVERY = 4  # jede 4. Woche Entlastung
ULTRA_KM = 300

# Belastung pro Stunde je Einheitstyp (TSS/h, entspricht IF² · 100)
TSS_PER_HOUR = {
    "rest": 0,
    "recovery": 30,
    "openers": 45,
    "endurance": 50,
    "long": 52,
    "tempo": 62,
    "sweetspot": 72,
    "threshold": 78,
    "vo2": 80,
}


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


@dataclass
class PlanWeek:
    start: date
    phase: Phase
    target_tss: float
    planned_tss: float = 0
    planned_hours: float = 0
    next_main_event: str | None = None
    weeks_to_event: int | None = None


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


def _watts(ftp: int | None, lo: float, hi: float) -> str:
    if not ftp:
        return f"{round(lo * 100)}–{round(hi * 100)} % FTP"
    return f"{round(lo * 100)}–{round(hi * 100)} % FTP ({round(lo * ftp)}–{round(hi * ftp)} W)"


def _cap(ftp: int | None, hi: float) -> str:
    return f"{round(hi * 100)} % FTP" + (f" ({round(hi * ftp)} W)" if ftp else "")


def _fmt_h(hours: float) -> str:
    h, m = int(hours), round((hours - int(hours)) * 60)
    return f"{h}:{m:02d} h" if h else f"{m} min"


def describe(kind: str, hours: float, ftp: int | None) -> tuple[str, str]:
    """Titel und Beschreibung einer Einheit mit konkreten Vorgaben."""
    minutes = hours * 60
    if kind == "recovery":
        return "Locker rollen", (
            f"{_fmt_h(hours)} sehr locker in Z1, unter {_cap(ftp, 0.55)}. "
            "Hohe Trittfrequenz, kein Druck – dient nur der Durchblutung."
        )
    if kind == "openers":
        return "Vorbelastung", (
            f"{_fmt_h(hours)} locker in Z2 ({_watts(ftp, 0.56, 0.7)}), darin "
            f"3 × 1 min zügig bei {_watts(ftp, 1.0, 1.1)} mit je 3 min Pause. "
            "Hält die Beine wach vor dem Event."
        )
    if kind == "endurance":
        return "Grundlage", (
            f"{_fmt_h(hours)} gleichmäßig in Z2, {_watts(ftp, 0.56, 0.75)}. "
            "Trittfrequenz 85–95, ruhige Atmung."
        )
    if kind == "long":
        carbs = "60–90 g Kohlenhydrate pro Stunde" if hours >= 3 else "regelmäßig trinken und essen"
        return "Lange Ausfahrt", (
            f"{_fmt_h(hours)} in Z2, {_watts(ftp, 0.56, 0.72)}. An Anstiegen nicht über "
            f"{_cap(ftp, 0.85)}. Verpflegung üben: {carbs}."
        )
    if kind == "tempo":
        n = max(2, min(3, int((minutes - 30) // 25)))
        work = max(10, min(20, int((minutes - 30) / n - 5)))
        return "Tempo", (
            f"{_fmt_h(hours)} gesamt: 15 min einfahren, {n} × {work} min Tempo bei "
            f"{_watts(ftp, 0.76, 0.88)} mit 5 min locker dazwischen, Rest Z2."
        )
    if kind == "sweetspot":
        n = max(2, min(4, int((minutes - 30) // 17)))
        work = 12 if minutes < 90 else 15
        return "Sweet Spot", (
            f"{_fmt_h(hours)} gesamt: 15 min einfahren, {n} × {work} min bei "
            f"{_watts(ftp, 0.88, 0.93)} mit 4 min locker dazwischen, Rest Z2."
        )
    if kind == "threshold":
        n = max(3, min(5, int((minutes - 30) // 13)))
        return "Schwelle", (
            f"{_fmt_h(hours)} gesamt: 15 min einfahren, {n} × 8 min bei "
            f"{_watts(ftp, 0.95, 1.05)} mit 4 min locker dazwischen, Rest Z2."
        )
    if kind == "vo2":
        n = max(4, min(6, int((minutes - 30) // 8)))
        return "VO2max", (
            f"{_fmt_h(hours)} gesamt: 15 min einfahren, {n} × 4 min bei "
            f"{_watts(ftp, 1.06, 1.2)} mit 4 min locker dazwischen, Rest Z2."
        )
    return "Ruhetag", "Kein Training. Erholung ist Teil des Plans."


def _event_text(ev: PlanEvent, day: date, km: float) -> str:
    parts = ["Hauptevent" if ev.main else "Nebenevent"]
    if ev.days > 1:
        parts.append(f"Tag {(day - ev.start).days + 1} von {ev.days}")
    if km:
        parts.append(f"ca. {round(km)} km")
    return ", ".join(parts) + ". Gleichmäßig fahren, früh und regelmäßig verpflegen."


def _round_hours(h: float) -> float:
    return round(h * 4) / 4  # auf 15 min


def _make(day: date, kind: str, hours: float, ftp: int | None) -> Workout:
    hours = _round_hours(hours)
    if kind == "rest" or hours <= 0:
        title, text = describe("rest", 0, ftp)
        return Workout(day, "rest", title, 0, 0, text)
    title, text = describe(kind, hours, ftp)
    return Workout(day, kind, title, hours, round(hours * TSS_PER_HOUR[kind]), text)


def quality_sessions(phase: Phase, ultra: bool) -> list[str]:
    """Qualitätseinheiten unter der Woche, je Phase und Eventtyp."""
    if phase == Phase.BASE:
        return ["tempo"]
    if phase == Phase.BUILD:
        return ["sweetspot", "threshold"] if ultra else ["threshold", "vo2"]
    if phase == Phase.SPECIFIC:
        return ["sweetspot"] if ultra else ["threshold", "vo2"]
    return []


def distribute_week(
    week_days: list[date],
    target_tss: float,
    phase: Phase,
    availability: dict[int, float],
    ftp: int | None,
    ultra: bool,
    fixed: dict[date, Workout],
) -> list[Workout]:
    """Verteilt das Wochenziel auf die Tage. ``fixed`` enthält bereits feste Tage
    (Events, Vorbelastung, Erholung)."""
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

    # Dauer: verfügbare Zeit, skaliert auf das Wochenziel
    full = {d: availability[d.weekday()] for d in free}
    capacity = sum(full[d] * TSS_PER_HOUR[kinds[d]] for d in free)
    scale = min(1.0, max(0.0, remaining) / capacity) if capacity else 0
    for d in free:
        hours = full[d] * scale
        min_hours = 0.75 if kinds[d] in ("tempo", "sweetspot", "threshold", "vo2") else 0.5
        if hours < min_hours:
            # zu kurz für die geplante Einheit: lockere Einheit oder Ruhetag
            hours = min_hours if scale > 0.25 and full[d] >= min_hours else 0
            kind = "endurance" if hours else "rest"
        else:
            kind = kinds[d]
        plan[d] = _make(d, kind, hours, ftp)

    # Tapering: Vorbelastung am letzten Tag vor dem Hauptevent wird separat gesetzt
    for d in week_days:
        plan.setdefault(d, _make(d, "rest", 0, ftp))
    return [plan[d] for d in week_days]


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
) -> Plan:
    """Erstellt den Plan ab ``today`` bis zwei Wochen nach dem letzten Hauptevent."""
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
    loading_weeks = 0
    sim_ctl, sim_atl = ctl, atl
    projection: list[dict] = []

    while week_start <= end:
        days = [week_start + timedelta(days=i) for i in range(7)]
        phase, ref_event = week_phase(week_start, main)

        # 3:1-Rhythmus in Belastungsphasen
        if phase in RAMP:
            if loading_weeks >= RECOVERY_EVERY - 1:
                phase, loading_weeks = Phase.DELOAD, 0
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
        week_workouts = distribute_week(days, target, phase, availability, ftp, ultra, fixed)
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
        )
        plan.weeks.append(pw)
        plan.workouts.extend(week_workouts)

        # Prognose fortschreiben
        by_day = {w.day: w.tss for w in week_workouts}
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
