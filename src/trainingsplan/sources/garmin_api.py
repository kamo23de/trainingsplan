"""Garmin Connect Personal API – Aktivitäten abrufen.

Nutzt Garmins offiziellen Python-Client (``garmin-connect-personal-api-python``).
Der API Key kommt aus unserem Schlüsselbund-Eintrag bzw. ``TP_GARMIN_API_KEY``;
der Client tauscht ihn gegen ein Access Token (24 h gültig) und speichert dieses
zwischen.
"""

import io
import time
import zipfile
from collections.abc import Iterator
from datetime import date
from functools import partial
from typing import Any

from garmin_personal_api import GarminPersonalApiClient, HttpError, PersonalApiAuthenticator

from trainingsplan.credentials import get_garmin_api_key

PAGE_SIZE = 100
PAUSE_S = 0.3  # schont die API bei großen Abrufen
RETRY_DELAYS_S = (2, 10, 30)  # Wartezeiten bei vorübergehenden Serverfehlern
RETRY_STATUS = {429, 500, 502, 503, 504}


class GarminAuthError(RuntimeError):
    pass


def open_client() -> GarminPersonalApiClient:
    api_key = get_garmin_api_key()
    if not api_key:
        raise GarminAuthError(
            "Kein Garmin API Key gefunden. Mit `trainingsplan garmin-key` hinterlegen."
        )
    with PersonalApiAuthenticator() as authenticator:
        token = authenticator.obtain_token(api_key)
    return GarminPersonalApiClient(token.access_token)


def _records(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("activities", "activityList"):
            if isinstance(payload.get(key), list):
                return [r for r in payload[key] if isinstance(r, dict)]
    return []


def iter_activities(client, start_date: date, end_date: date) -> Iterator[dict]:
    """Alle Aktivitäts-Zusammenfassungen im Zeitraum, seitenweise abgerufen."""
    start = 0
    while True:
        page = _records(
            _with_retry(
                partial(
                    client.search_activities,
                    start=start,
                    limit=PAGE_SIZE,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
        )
        yield from page
        if len(page) < PAGE_SIZE:
            return
        start += PAGE_SIZE
        time.sleep(PAUSE_S)


def _with_retry(call):
    """Wiederholt Aufrufe bei vorübergehenden Fehlern (z. B. HTTP 504 Gateway Timeout)."""
    for delay in (*RETRY_DELAYS_S, None):
        try:
            return call()
        except HttpError as exc:
            if exc.status_code not in RETRY_STATUS or delay is None:
                raise
            time.sleep(delay)


def download_fit_files(client, activity_id: int | str) -> list[tuple[str, bytes]]:
    """Lädt die Originaldatei (ZIP) und gibt die enthaltenen FIT-Dateien zurück."""
    content = _with_retry(partial(client.download_activity, activity_id))
    time.sleep(PAUSE_S)
    if content[:4] != b"PK\x03\x04":  # kein ZIP, vermutlich direkt FIT
        return [(f"{activity_id}.fit", content)]
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return [
            (info.filename, archive.read(info))
            for info in archive.infolist()
            if info.filename.lower().endswith(".fit")
        ]
