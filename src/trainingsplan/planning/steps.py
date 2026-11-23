"""Strukturierte Schritte einer geplanten Einheit – Grundlage für den Garmin-Export.

Die Schritte folgen denselben Regeln wie die Texte in ``workouts.describe``
(gleiche Varianten, gleiche Wiederholungszahlen). Leistungsziele sind in Prozent
der FTP angegeben; das Garmin-Gerät rechnet sie mit seiner eigenen FTP in Watt um.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Step:
    name: str
    seconds: int | None  # None: Ende per Rundentaste
    intensity: str = "active"  # active | rest | warmup | cooldown | recovery
    low: int | None = None  # % FTP
    high: int | None = None
    notes: str | None = None


@dataclass
class Repeat:
    times: int
    steps: list[Step] = field(default_factory=list)


Item = Step | Repeat


def _m(minutes: float) -> int:
    return int(round(minutes * 60))


def _frame(
    total_min: int, warmup: int, middle: list[Item], cool_low=50, cool_high=65
) -> list[Item]:
    """Einfahren, Hauptteil, Rest der Zeit als Ausfahren (mindestens 5 min)."""
    used = warmup * 60 + sum(_duration(i) for i in middle)
    cooldown = max(300, total_min * 60 - used)
    return [
        Step("Einfahren", warmup * 60, "warmup", 50, 70),
        *middle,
        Step("Ausfahren", cooldown, "cooldown", cool_low, cool_high),
    ]


def _duration(item: Item) -> int:
    if isinstance(item, Repeat):
        return item.times * sum(_duration(s) for s in item.steps)
    return item.seconds or 0


def _intervals(
    n: int, work_min: float, lo: int, hi: int, rest_min: float, name: str, notes: str | None = None
) -> Repeat:
    return Repeat(
        n,
        [
            Step(name, _m(work_min), "active", lo, hi, notes),
            Step("locker", _m(rest_min), "recovery", 45, 60),
        ],
    )


# Übungen der Rumpfprogramme (Name, Dosierung) – wie in static/exercises.js
CORE_PROGRAMS = {
    "core-a": (
        3,
        [
            ("Unterarmstütz", "45 s"),
            ("Seitstütz", "30 s je Seite"),
            ("Dead Bug", "10× je Seite"),
            ("Bird Dog", "10× je Seite"),
            ("Glute Bridge", "15×"),
        ],
    ),
    "core-b": (
        3,
        [
            ("Hollow Hold", "30 s"),
            ("Seitstütz Hüftheben", "10× je Seite"),
            ("Superman", "12×"),
            ("Pallof-Press", "10× je Seite"),
            ("Glute Bridge einbeinig", "10× je Seite"),
        ],
    ),
    "core-c": (
        3,
        [
            ("Stütz Schulter antippen", "16×"),
            ("Y-T-W", "je 8×"),
            ("Nacken-Isometrie", "4×10 s je Richtung"),
            ("Bird Dog", "10× je Seite"),
            ("Hüftbeuger dehnen", "45 s je Seite"),
        ],
    ),
    "mobility": (
        1,
        [
            ("Katze-Kuh", "10×"),
            ("Hüftbeuger dehnen", "45 s je Seite"),
            ("BWS-Rotation", "10× je Seite"),
            ("Dead Bug", "2 × 8"),
            ("Glute Bridge", "2 × 12"),
        ],
    ),
}


def workout_steps(
    kind: str, hours: float, variant: int = 0, level: int = 0, program: str | None = None
) -> list[Item]:
    minutes = round(hours * 60)
    main = max(10, minutes - 30)
    v = variant % 3

    if kind == "recovery":
        return [Step("Locker rollen", minutes * 60, "active", 40, 55)]
    if kind == "openers":
        return _frame(
            minutes,
            10,
            [
                Repeat(
                    3,
                    [
                        Step("zügig", 60, "active", 100, 110),
                        Step("locker", 180, "recovery", 50, 65),
                    ],
                )
            ],
        )
    if kind == "endurance":
        if v == 1:
            return _frame(
                minutes,
                10,
                [
                    Repeat(
                        6,
                        [
                            Step("Trittfrequenz 105-115", 60, "active", 56, 75, "105–115 U/min"),
                            Step("Grundlage", 180, "active", 56, 75),
                        ],
                    )
                ],
                56,
                75,
            )
        if v == 2:
            return _frame(
                minutes,
                15,
                [_intervals(4, 5, 75, 85, 5, "Kraftausdauer", "60–70 U/min im Sitzen")],
                56,
                75,
            )
        return [Step("Grundlage Z2", minutes * 60, "active", 56, 75)]
    if kind == "long":
        if v == 1 and hours >= 3:
            z2 = int(minutes * 2 / 3)
            return [
                Step("Grundlage Z2", z2 * 60, "active", 56, 72),
                _intervals(3, 15, 76, 85, 5, "Tempo"),
                Step("Grundlage Z2", max(300, (minutes - z2 - 60) * 60), "active", 56, 72),
            ]
        return [Step("Lange Ausfahrt Z2", minutes * 60, "active", 56, 72)]
    if kind == "tempo":
        if v == 1:
            return _frame(
                minutes, 15, [Step("Tempo am Stück", min(40, main) * 60, "active", 76, 85)]
            )
        if v == 2:
            return _frame(
                minutes, 15, [_intervals(3, 12, 76, 88, 5, "Tempo", "alle 3 min 10 s Antritt")]
            )
        n = max(2, min(3, main // 25))
        work = max(10, min(20, main // n - 5))
        return _frame(minutes, 15, [_intervals(n, work, 76, 88, 5, "Tempo")])
    if kind == "sweetspot":
        if v == 1 and main >= 45:
            work = 20 if main >= 50 else 15
            return _frame(minutes, 15, [_intervals(2, work, 88, 93, 5, "Sweet Spot")])
        if v == 2:
            block = [
                Step("Sweet Spot", 120, "active", 88, 93),
                Step("über FTP", 60, "active", 100, 105),
            ] * 3
            return _frame(
                minutes, 15, [Repeat(3, [*block, Step("locker", 240, "recovery", 45, 60)])]
            )
        n = max(2, min(4, main // 17))
        work = 12 if minutes < 90 else 15
        return _frame(minutes, 15, [_intervals(n, work, 88, 93, 4, "Sweet Spot")])
    if kind == "threshold":
        if v == 1:
            n = max(2, min(4, main // 15))
            return _frame(minutes, 15, [_intervals(n, 10, 95, 102, 5, "Schwelle")])
        if v == 2 and main >= 40:
            return _frame(minutes, 15, [_intervals(2, 15, 93, 100, 6, "Schwelle")])
        n = max(3, min(5, main // 13))
        return _frame(minutes, 15, [_intervals(n, 8, 95, 105, 4, "Schwelle")])
    if kind == "vo2":
        if v == 1:
            return _frame(minutes, 15, [_intervals(6, 3, 110, 120, 3, "VO2max")])
        if v == 2:
            block = [
                Step("30 s hart", 30, "active", 120, 130),
                Step("30 s locker", 30, "recovery", 40, 55),
            ] * 8
            return _frame(
                minutes, 15, [Repeat(3, [*block, Step("Satzpause", 300, "recovery", 45, 60)])]
            )
        n = max(4, min(6, main // 8))
        return _frame(minutes, 15, [_intervals(n, 4, 106, 120, 4, "VO2max")])

    # Ergänzungstraining: ohne Leistungsziel
    if kind == "row":
        if v == 1:
            reps = max(3, min(5, (minutes - 15) // 8))
            rest = max(300, minutes * 60 - 600 - reps * 480)
            return [
                Step("Einrudern", 600, "warmup", notes="Schlagzahl 18–20"),
                Repeat(
                    reps,
                    [
                        Step("zügig", 360, "active", notes="Schlagzahl 22–24"),
                        Step("locker", 120, "recovery"),
                    ],
                ),
                Step("Ausrudern", rest, "cooldown"),
            ]
        if v == 2:
            rest = max(300, minutes * 60 - 600 - 5 * 300)
            return [
                Step("Einrudern", 600, "warmup"),
                Repeat(
                    5,
                    [
                        Step("Technik Beinstoß", 180, "active", notes="Schlagzahl 18–20"),
                        Step("frei", 120, "recovery"),
                    ],
                ),
                Step("Ausrudern", rest, "cooldown"),
            ]
        return [Step("Rudern Grundlage", minutes * 60, "active", notes="Schlagzahl 18–22")]
    if kind == "run":
        if level < 4:
            return [
                Repeat(
                    max(4, minutes // 5),
                    [
                        Step("laufen", 240, "active", notes="sehr locker"),
                        Step("gehen", 60, "recovery"),
                    ],
                )
            ]
        if level >= 6 and v == 2:
            return [
                Step("locker laufen", max(600, (minutes - 6) * 60), "active"),
                Repeat(4, [Step("Steigerung", 20, "active"), Step("gehen", 60, "recovery")]),
            ]
        return [Step("locker laufen", minutes * 60, "active", notes="Unterhaltung möglich")]
    if kind == "core":
        rounds, items = CORE_PROGRAMS.get(program or "core-a", CORE_PROGRAMS["core-a"])
        steps = [Step(name, None, "active", notes=dose) for name, dose in items]
        return [Repeat(rounds, steps)] if rounds > 1 else steps
    return []


def flatten_count(items: list[Item]) -> int:
    """Anzahl FIT-Schritte (Wiederholungen zählen als eigener Schritt)."""
    return sum(len(i.steps) + 1 if isinstance(i, Repeat) else 1 for i in items)


def total_seconds(items: list[Item]) -> int:
    return sum(_duration(i) for i in items)
