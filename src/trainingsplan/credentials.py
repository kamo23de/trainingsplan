"""Zugriff auf Geheimnisse (Garmin Personal API Key).

Reihenfolge: zuerst Umgebungsvariable ``TP_GARMIN_API_KEY`` (für Server),
sonst der Schlüsselbund des Betriebssystems (lokal auf dem Mac).
"""

import keyring

from trainingsplan.config import get_settings

KEYRING_SERVICE = "trainingsplan"
GARMIN_KEY_NAME = "garmin-personal-api-key"


def get_garmin_api_key() -> str | None:
    settings = get_settings()
    if settings.garmin_api_key:
        return settings.garmin_api_key
    return keyring.get_password(KEYRING_SERVICE, GARMIN_KEY_NAME)


def set_garmin_api_key(value: str) -> None:
    keyring.set_password(KEYRING_SERVICE, GARMIN_KEY_NAME, value)


def delete_garmin_api_key() -> None:
    keyring.delete_password(KEYRING_SERVICE, GARMIN_KEY_NAME)
