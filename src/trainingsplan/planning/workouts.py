"""Beschreibungen der Trainingseinheiten mit konkreten Vorgaben.

Damit der Plan abwechslungsreich bleibt, gibt es je Einheitstyp mehrere
Varianten; der Planer wählt sie wochenweise im Wechsel. Neben dem Rad gibt es
Ergänzungstraining: Indoor-Rudern, Laufen und Rumpfstabilität.
"""

from __future__ import annotations

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
    "row": 55,
    "run": 60,
    "core": 25,
}

BIKE_KINDS = {"recovery", "openers", "endurance", "long", "tempo", "sweetspot", "threshold", "vo2"}
CROSS_KINDS = {"row", "run", "core"}
SPORT = {"row": "Rudern", "run": "Laufen", "core": "Rumpf"}


def watts(ftp: int | None, lo: float, hi: float) -> str:
    if not ftp:
        return f"{round(lo * 100)}–{round(hi * 100)} % FTP"
    return f"{round(lo * 100)}–{round(hi * 100)} % FTP ({round(lo * ftp)}–{round(hi * ftp)} W)"


def cap(ftp: int | None, hi: float) -> str:
    return f"{round(hi * 100)} % FTP" + (f" ({round(hi * ftp)} W)" if ftp else "")


def fmt_h(hours: float) -> str:
    h, m = int(hours), round((hours - int(hours)) * 60)
    return f"{h}:{m:02d} h" if h else f"{m} min"


def core_program(variant: int) -> str:
    """Schlüssel des Übungsprogramms; passt zu den Texten in ``describe``."""
    if variant % 4 == 3:
        return "mobility"
    return ("core-a", "core-b", "core-c")[variant % 3]


def describe(
    kind: str,
    hours: float,
    ftp: int | None,
    variant: int = 0,
    lthr: int | None = None,
    level: int = 0,
) -> tuple[str, str]:
    """Titel und Beschreibung. ``variant`` wechselt die Ausprägung, ``level`` ist
    beim Laufen die Zahl der bisher geplanten Läufe (für den langsamen Aufbau)."""
    minutes = round(hours * 60)
    main = max(10, minutes - 30)  # Zeit nach 15 min Ein- und 15 min Ausfahren
    v = variant % 3

    if kind == "recovery":
        return "Locker rollen", (
            f"{fmt_h(hours)} sehr locker in Z1, unter {cap(ftp, 0.55)}. "
            "Hohe Trittfrequenz, kein Druck – dient nur der Durchblutung."
        )
    if kind == "openers":
        return "Vorbelastung", (
            f"{fmt_h(hours)} locker in Z2 ({watts(ftp, 0.56, 0.7)}), darin "
            f"3 × 1 min zügig bei {watts(ftp, 1.0, 1.1)} mit je 3 min Pause. "
            "Hält die Beine wach vor dem Event."
        )
    if kind == "endurance":
        if v == 1:
            return "Grundlage mit Trittfrequenz", (
                f"{fmt_h(hours)} in Z2, {watts(ftp, 0.56, 0.75)}. Darin 6 × 1 min mit "
                "105–115 U/min bei gleicher Leistung, je 3 min normal dazwischen. "
                "Schult einen runden Tritt – auf langen Strecken spart das Kraft."
            )
        if v == 2:
            return "Grundlage mit Kraftausdauer", (
                f"{fmt_h(hours)} in Z2, {watts(ftp, 0.56, 0.75)}. Darin 4 × 5 min mit "
                f"60–70 U/min im Sitzen bei {watts(ftp, 0.75, 0.85)}, 5 min locker "
                "dazwischen – am besten an einem langen Anstieg oder auf dem Rollentrainer."
            )
        return "Grundlage", (
            f"{fmt_h(hours)} gleichmäßig in Z2, {watts(ftp, 0.56, 0.75)}. "
            "Trittfrequenz 85–95, ruhige Atmung."
        )
    if kind == "long":
        carbs = "60–90 g Kohlenhydrate pro Stunde" if hours >= 3 else "regelmäßig trinken und essen"
        if v == 1 and hours >= 3:
            return "Lange Ausfahrt mit Tempo", (
                f"{fmt_h(hours)} in Z2, {watts(ftp, 0.56, 0.72)}. Im letzten Drittel "
                f"3 × 15 min Tempo bei {watts(ftp, 0.76, 0.85)} – trainiert, auch "
                f"ermüdet noch Druck zu machen. Verpflegung: {carbs}."
            )
        if v == 2 and hours >= 3:
            return "Lange Ausfahrt – Event-Test", (
                f"{fmt_h(hours)} in Z2, {watts(ftp, 0.56, 0.72)}, an Anstiegen nicht über "
                f"{cap(ftp, 0.85)}. Fahre mit Ausrüstung, Taschen und Verpflegung wie "
                "beim Event, wechsle regelmäßig die Griffposition und iss nach Plan "
                f"({carbs})."
            )
        return "Lange Ausfahrt", (
            f"{fmt_h(hours)} in Z2, {watts(ftp, 0.56, 0.72)}. An Anstiegen nicht über "
            f"{cap(ftp, 0.85)}. Verpflegung üben: {carbs}."
        )
    if kind == "tempo":
        if v == 1:
            block = min(40, main)
            return "Tempo am Stück", (
                f"{fmt_h(hours)} gesamt: 15 min einfahren, {block} min am Stück bei "
                f"{watts(ftp, 0.76, 0.85)}, Rest Z2. Gleichmäßig wie auf einer langen Etappe."
            )
        if v == 2:
            return "Tempo mit Antritten", (
                f"{fmt_h(hours)} gesamt: 15 min einfahren, 3 × 12 min Tempo bei "
                f"{watts(ftp, 0.76, 0.88)}, darin alle 3 min 10 s kräftiger Antritt, "
                "5 min locker zwischen den Blöcken, Rest Z2."
            )
        n = max(2, min(3, main // 25))
        work = max(10, min(20, main // n - 5))
        return "Tempo", (
            f"{fmt_h(hours)} gesamt: 15 min einfahren, {n} × {work} min Tempo bei "
            f"{watts(ftp, 0.76, 0.88)} mit 5 min locker dazwischen, Rest Z2."
        )
    if kind == "sweetspot":
        if v == 1 and main >= 45:
            work = 20 if main >= 50 else 15
            return "Sweet Spot lang", (
                f"{fmt_h(hours)} gesamt: 15 min einfahren, 2 × {work} min bei "
                f"{watts(ftp, 0.88, 0.93)} mit 5 min locker dazwischen, Rest Z2."
            )
        if v == 2:
            return "Sweet Spot Over-Under", (
                f"{fmt_h(hours)} gesamt: 15 min einfahren, 3 Blöcke à 9 min im Wechsel "
                f"2 min bei {watts(ftp, 0.88, 0.93)} und 1 min bei "
                f"{watts(ftp, 1.0, 1.05)}, 4 min locker zwischen den Blöcken, Rest Z2."
            )
        n = max(2, min(4, main // 17))
        work = 12 if minutes < 90 else 15
        return "Sweet Spot", (
            f"{fmt_h(hours)} gesamt: 15 min einfahren, {n} × {work} min bei "
            f"{watts(ftp, 0.88, 0.93)} mit 4 min locker dazwischen, Rest Z2."
        )
    if kind == "threshold":
        if v == 1:
            n = max(2, min(4, main // 15))
            return "Schwelle 10er", (
                f"{fmt_h(hours)} gesamt: 15 min einfahren, {n} × 10 min bei "
                f"{watts(ftp, 0.95, 1.02)} mit 5 min locker dazwischen, Rest Z2."
            )
        if v == 2 and main >= 40:
            return "Schwelle lang", (
                f"{fmt_h(hours)} gesamt: 15 min einfahren, 2 × 15 min bei "
                f"{watts(ftp, 0.93, 1.0)} mit 6 min locker dazwischen, Rest Z2."
            )
        n = max(3, min(5, main // 13))
        return "Schwelle", (
            f"{fmt_h(hours)} gesamt: 15 min einfahren, {n} × 8 min bei "
            f"{watts(ftp, 0.95, 1.05)} mit 4 min locker dazwischen, Rest Z2."
        )
    if kind == "vo2":
        if v == 1:
            return "VO2max 3er", (
                f"{fmt_h(hours)} gesamt: 15 min einfahren, 6 × 3 min bei "
                f"{watts(ftp, 1.1, 1.2)} mit 3 min locker dazwischen, Rest Z2."
            )
        if v == 2:
            return "VO2max 30/30", (
                f"{fmt_h(hours)} gesamt: 15 min einfahren, 3 Sätze à 8 × (30 s bei "
                f"{watts(ftp, 1.2, 1.3)} / 30 s locker), 5 min zwischen den Sätzen, Rest Z2."
            )
        n = max(4, min(6, main // 8))
        return "VO2max", (
            f"{fmt_h(hours)} gesamt: 15 min einfahren, {n} × 4 min bei "
            f"{watts(ftp, 1.06, 1.2)} mit 4 min locker dazwischen, Rest Z2."
        )

    # --- Ergänzungstraining -------------------------------------------------------
    if kind == "row":
        if v == 1:
            reps = max(3, min(5, (minutes - 15) // 8))
            return "Rudern: Intervalle", (
                f"{minutes} min Indoor-Rudern: 10 min locker einrudern, {reps} × 6 min "
                "zügig mit Schlagzahl 22–24 (Atmung tiefer, aber kontrolliert), je 2 min "
                "locker, zum Schluss ausrudern. Ganzkörperreiz für Herz-Kreislauf, "
                "entlastet Sitzfläche und Knie."
            )
        if v == 2:
            return "Rudern: Technik", (
                f"{minutes} min Indoor-Rudern, locker: 10 min ein, dann 5 × 3 min mit "
                "Fokus auf den Beinstoß (erst Beine, dann Oberkörper, zuletzt Arme), "
                "Schlagzahl 18–20, dazwischen 2 min frei. Rücken lang halten, nicht "
                "einrunden."
            )
        return "Rudern: Grundlage", (
            f"{minutes} min Indoor-Rudern gleichmäßig, Schlagzahl 18–22, Unterhaltung "
            "möglich. Ablauf: Beine – Rumpf – Arme, zurück Arme – Rumpf – Beine. "
            "Gute Abwechslung im Winter, trainiert Rücken und Rumpf mit."
        )
    if kind == "run":
        hr = f" (Puls etwa unter {round(lthr * 0.85) + 5})" if lthr else ""
        if level < 4:
            blocks = max(4, minutes // 5)
            return "Laufen: Lauf-Geh-Wechsel", (
                f"{blocks} × (4 min sehr locker laufen / 1 min gehen), insgesamt "
                f"{minutes} min{hr}. Bewusst langsam beginnen: Sehnen und Knochen "
                "brauchen länger als die Ausdauer. Weicher Untergrund ist ideal."
            )
        if level >= 6 and v == 2:
            return "Laufen mit Steigerungen", (
                f"{minutes} min locker laufen{hr}, am Ende 4 × 20 s Steigerung bis "
                "zügig, dazwischen 1 min gehen. Gibt einen frischen Reiz für Laufstil "
                "und Koordination."
            )
        return "Laufen: locker", (
            f"{minutes} min locker laufen{hr}, Unterhaltung muss möglich sein. "
            "Der Reiz für Knochen und Bindegewebe zählt, nicht das Tempo."
        )
    if kind == "core":
        if variant % 4 == 3:
            return "Mobilität & Rumpf leicht", (
                "15–20 min: Katze-Kuh 10×, Hüftbeuger-Dehnung je Seite 45 s, "
                "Brustwirbelsäule rotieren 10× je Seite, Dead Bug 2 × 8, "
                "Glute Bridge 2 × 12. Sanft – nur bewegen, nicht ermüden."
            )
        if v == 1:
            return "Rumpf B: Rotation & Hüfte", (
                "15–20 min, 3 Runden: Hollow Hold 30 s, Seitstütz mit Hüftheben 10× je "
                "Seite, Superman 12×, Pallof-Press mit Band 10× je Seite, einbeinige "
                "Glute Bridge 10× je Seite. Kurze Pausen, saubere Ausführung."
            )
        if v == 2:
            return "Rumpf C: Ultra-Spezial", (
                "15–20 min für lange Stunden im Sattel, 3 Runden: Unterarmstütz mit "
                "Schulterantippen 16×, Y-T-W für die Schulterblätter je 8×, "
                "Nacken-Isometrie (Kopf gegen die Hand) 4 × 10 s je Richtung, Bird Dog "
                "10× je Seite. Danach die Hüftbeuger dehnen."
            )
        return "Rumpf A: Basis", (
            "15–20 min, 3 Runden: Unterarmstütz 45 s, Seitstütz 30 s je Seite, Dead Bug "
            "10× je Seite, Bird Dog 10× je Seite, Glute Bridge 15×. 30 s Pause "
            "zwischen den Übungen. Ein stabiler Rumpf hält die Position auf dem Rad."
        )
    return "Ruhetag", "Kein Training. Erholung ist Teil des Plans."
