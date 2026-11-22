"""Geplante Einheiten als FIT-Workout-Datei für Garmin-Geräte.

Die Datei lässt sich auf Edge-Radcomputer und viele Uhren übertragen, indem sie per
USB in den Ordner ``Garmin/NewFiles`` (bei manchen Geräten ``Garmin/Workouts``)
kopiert wird. Das Gerät übernimmt sie beim Trennen bzw. Neustart als Workout.
Leistungsziele stehen in % FTP – das Gerät rechnet mit seiner eigenen FTP.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

from garmin_fit_sdk import Encoder, Profile

from trainingsplan.planning.steps import Item, Repeat, Step, flatten_count, workout_steps
from trainingsplan.storage.models import PlannedWorkout

MESG = Profile["mesg_num"]
SPORT = {
    "row": ("rowing", "indoor_rowing"),
    "run": ("running", "generic"),
    "core": ("training", "strength_training"),
}
MAX_NAME = 15  # viele Garmin-Geräte zeigen nur kurze Namen vollständig


def _ascii(text: str, limit: int) -> str:
    text = text.replace("×", "x").replace("–", "-").replace("·", "-")
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = text.replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return text[:limit]


def workout_name(p: PlannedWorkout) -> str:
    return _ascii(f"{p.day:%d.%m} {p.title}", MAX_NAME)


def file_name(p: PlannedWorkout) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", _ascii(p.title, 40)).strip("_")
    return f"TP_{p.day:%Y-%m-%d}_{slug or p.kind}.fit"


def _step_mesg(index: int, step: Step) -> dict:
    mesg = {
        "mesg_num": MESG["WORKOUT_STEP"],
        "message_index": index,
        "wkt_step_name": _ascii(step.name, 16),
        "intensity": step.intensity,
    }
    if step.seconds:
        mesg.update(duration_type="time", duration_value=step.seconds * 1000)
    else:
        mesg.update(duration_type="open")
    if step.low is not None and step.high is not None:
        # Werte bis 1000 bedeuten % FTP
        mesg.update(
            target_type="power",
            target_value=0,
            custom_target_value_low=step.low,
            custom_target_value_high=step.high,
        )
    else:
        mesg.update(target_type="open")
    if step.notes:
        mesg["notes"] = _ascii(step.notes, 50)
    return mesg


def _messages(items: list[Item]) -> list[dict]:
    out: list[dict] = []
    for item in items:
        if isinstance(item, Repeat):
            start = len(out)
            for s in item.steps:
                out.append(_step_mesg(len(out), s))
            out.append(
                {
                    "mesg_num": MESG["WORKOUT_STEP"],
                    "message_index": len(out),
                    "duration_type": "repeat_until_steps_cmplt",
                    "duration_value": start,
                    "target_type": "open",
                    "target_value": item.times,
                }
            )
        else:
            out.append(_step_mesg(len(out), item))
    return out


def build_fit(p: PlannedWorkout, created: datetime | None = None) -> bytes:
    items = workout_steps(p.kind, p.hours, p.variant, p.level, p.program)
    if not items:
        raise ValueError(f"Für '{p.title}' gibt es keine strukturierten Schritte")
    sport, sub_sport = SPORT.get(p.kind, ("cycling", "generic"))
    created = created or datetime.now(UTC)
    steps = _messages(items)
    assert len(steps) == flatten_count(items)

    encoder = Encoder()
    encoder.write_mesg(
        {
            "mesg_num": MESG["FILE_ID"],
            "type": "workout",
            "manufacturer": "development",
            "product": 0,
            "serial_number": (p.id or 1) * 1000 + p.day.toordinal() % 1000,
            "time_created": created,
        }
    )
    encoder.write_mesg(
        {
            "mesg_num": MESG["WORKOUT"],
            "wkt_name": workout_name(p),
            "sport": sport,
            "sub_sport": sub_sport,
            "num_valid_steps": len(steps),
        }
    )
    for mesg in steps:
        encoder.write_mesg(mesg)
    return encoder.close()


# --- Übertragung auf ein per USB angeschlossenes Gerät ----------------------------

DEVICE_SUBDIRS = ("Garmin/NewFiles", "GARMIN/NewFiles", "Garmin/NEWFILES", "GARMIN/NEWFILES")


def find_device_dir(
    configured: Path | None = None, volumes: Path = Path("/Volumes")
) -> Path | None:
    """Sucht den NewFiles-Ordner eines als Laufwerk angeschlossenen Garmin-Geräts."""
    if configured:
        return configured if configured.is_dir() else None
    if not volumes.is_dir():
        return None
    for volume in sorted(volumes.iterdir()):
        for sub in DEVICE_SUBDIRS:
            candidate = volume / sub
            if candidate.is_dir():
                return candidate
    return None


def send_to_device(p: PlannedWorkout, device_dir: Path) -> Path:
    target = device_dir / file_name(p)
    target.write_bytes(build_fit(p))
    return target
