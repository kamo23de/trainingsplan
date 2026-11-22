"""Garmin Connect Personal API – laufende Synchronisierung neuer Aktivitäten.

Ablauf laut Garmin-Dokumentation:
1. Personal API Key in Garmin Connect Web erstellen (wird nur einmal angezeigt).
2. Key gegen ein Access Token tauschen (gültig 24 h, keine Refresh Tokens).
3. Mit dem Token die Connect-APIs abfragen.

Die konkreten Endpunkte für Aktivitäten und FIT-Downloads werden im nächsten
Schritt anhand der Swagger-Dokumentation der Personal API ergänzt.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from trainingsplan.credentials import get_garmin_api_key

TOKEN_URL = (
    "https://personal.connectapi.garmin.com/personalapitoken-service/"
    "personal-api/personal-api-key/token"
)


class GarminAuthError(RuntimeError):
    pass


@dataclass
class AccessToken:
    value: str
    expires_at: datetime

    @property
    def is_valid(self) -> bool:
        return datetime.now(UTC) < self.expires_at - timedelta(minutes=5)


class GarminPersonalClient:
    def __init__(self, api_key: str | None = None, http: httpx.Client | None = None) -> None:
        self._api_key = api_key or get_garmin_api_key()
        if not self._api_key:
            raise GarminAuthError(
                "Kein Garmin API Key gefunden. Mit `trainingsplan garmin-key` hinterlegen."
            )
        self._http = http or httpx.Client(timeout=30)
        self._token: AccessToken | None = None

    def access_token(self) -> str:
        if self._token is None or not self._token.is_valid:
            self._token = self._fetch_token()
        return self._token.value

    def _fetch_token(self) -> AccessToken:
        response = self._http.post(TOKEN_URL, headers={"Authorization": f"ApiKey {self._api_key}"})
        if response.status_code in (401, 403):
            raise GarminAuthError("Garmin hat den API Key abgelehnt (abgelaufen oder gelöscht?)")
        response.raise_for_status()
        payload = response.json()
        expires_in = int(payload.get("expires_in", 24 * 3600))
        return AccessToken(
            value=payload["access_token"],
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        )

    def list_activities(self, since: datetime) -> list[dict]:
        """TODO: Aktivitätsliste ab ``since`` abrufen (Endpunkt aus Swagger-Doku)."""
        raise NotImplementedError

    def download_fit(self, activity_id: str) -> bytes:
        """TODO: FIT-Datei einer Aktivität herunterladen."""
        raise NotImplementedError
