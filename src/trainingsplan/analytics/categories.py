"""Einordnung von Aktivitäten in Kategorien für Rückblick und Kalender.

Grundlage sind die FIT-Felder ``sport`` und ``sub_sport`` von Garmin. Indoor-Rudern
zeichnen Garmin-Geräte je nach Modell als ``rowing`` oder als ``fitness_equipment``
mit ``sub_sport = indoor_rowing`` auf; Krafttraining als ``training`` bzw.
``fitness_equipment`` mit ``strength_training``.
"""

BIKE = "Rad"
EBIKE = "eBike"
OTHER = "Sonstige"
RUN = "Laufen"
ROW = "Rudern"
STRENGTH = "Kraft"

# Feste Reihenfolge = feste Farbe je Kategorie (Farbslot 1–6)
CATEGORIES = [BIKE, EBIKE, OTHER, RUN, ROW, STRENGTH]

RUN_SPORTS = {"running"}
ROW_SPORTS = {"rowing"}
ROW_SUB_SPORTS = {"indoor_rowing"}
STRENGTH_SPORTS = {"training"}
STRENGTH_SUB_SPORTS = {"strength_training", "pilates", "yoga", "flexibility_training"}


def category_of(sport: str | None, sub_sport: str | None, is_ebike: bool) -> str:
    if is_ebike:
        return EBIKE
    if sport == "cycling":
        return BIKE
    if sport in RUN_SPORTS:
        return RUN
    if sport in ROW_SPORTS or sub_sport in ROW_SUB_SPORTS:
        return ROW
    if sport in STRENGTH_SPORTS or sub_sport in STRENGTH_SUB_SPORTS:
        return STRENGTH
    return OTHER
