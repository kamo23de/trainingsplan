# Trainingsplan

Individuelle Trainingsplanung auf Basis der eigenen Trainingshistorie aus Garmin Connect.
Schwerpunkt Radfahren (Leistungsmesser), eBike-Fahrten werden über die Herzfrequenz bewertet.

**Stufe 1 (aktuell):** Dashboard für die Rückschau auf die letzten 4 Jahre.
**Später:** Ziele erfassen und eine Planungsvorausschau erzeugen.

## Architektur

```
Garmin-Export (ZIP, einmalig)  ─┐
                                ├─▶ sources ─▶ ingest (FIT parsen) ─▶ storage (DB)
Garmin Personal API (laufend) ──┘                                         │
                                                                          ▼
                                     web (Dashboard)  ◀──  analytics (TSS, CTL/ATL/TSB, Zonen)
                                                                          ▲
                                                           goals (Ziele, FTP-Historie)
```

| Ordner | Aufgabe |
|---|---|
| `sources/` | Datenquellen: Garmin-Export (Historie) und Personal API (laufende Synchronisierung) |
| `ingest/` | FIT-Dateien parsen und als Aktivitäten speichern |
| `storage/` | Datenmodell (SQLAlchemy), lokal SQLite, später PostgreSQL |
| `analytics/` | Belastung (Power-TSS bzw. hrTSS), Fitness/Ermüdung/Form, Zonen |
| `goals/` | Ziele und Leistungsschwellen mit Gültigkeitszeitraum |
| `web/` | FastAPI-App mit Dashboard (Jinja2-Templates, kein Node.js nötig) |

Grundsätze:
- **Rohdaten bleiben unverändert** in `data/raw/`, die Datenbank lässt sich jederzeit neu daraus aufbauen.
- **FTP, Schwellenpuls und Ziele haben einen Zeitverlauf**, damit historische Werte korrekt berechnet werden.
- **Serverfähig:** alle Einstellungen über Umgebungsvariablen (`TP_…`), siehe `.env.example`.
- **Geheimnisse nie im Repo:** Der Garmin-Key liegt lokal im macOS-Schlüsselbund.

## Einrichtung auf dem Mac

Einmalig installieren:

```sh
xcode-select --install          # git und Compiler
# Homebrew: Installationsbefehl von https://brew.sh
brew install uv gh              # Python-Werkzeug und GitHub CLI
gh auth login                   # bei GitHub anmelden
```

Projekt holen und starten:

```sh
gh repo clone kamo23de/trainingsplan
cd trainingsplan
uv sync                         # lädt Python 3.13 und alle Abhängigkeiten
uv run trainingsplan init-db    # legt data/ und die Datenbank an
uv run trainingsplan serve      # Dashboard unter http://127.0.0.1:8000
```

Tests und Code-Prüfung:

```sh
uv run pytest
uv run ruff check .
```

## Garmin anbinden

**Historie (einmalig):** Im Garmin-Konto den Datenexport anfordern. Das ZIP nach
`data/garmin-export/` legen (gern entpackt), dann prüfen:

```sh
uv run trainingsplan scan-export
```

**Laufende Synchronisierung:** In Garmin Connect Web einen *Personal API Key* erstellen
(Laufzeit am besten 1 Jahr; der Key wird nur einmal angezeigt). Dann:

```sh
uv run trainingsplan garmin-key     # Key im Schlüsselbund speichern
uv run trainingsplan garmin-check   # Verbindung testen
```

## Nächste Schritte

1. FIT-Parser in `ingest/` (Garmin FIT SDK) und Import des Garmin-Exports
2. FTP-/Schwellenpuls-Historie erfassen, TSS für alle Aktivitäten berechnen
3. Dashboard: Wochenumfänge, lange Fahrten, Fitness/Ermüdung/Form (CTL/ATL/TSB)
4. Synchronisierung über die Personal API
5. Ziele erfassen und Planungsvorausschau
