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

## Seiten

- **Start** (`/`): Auswahl zwischen Rückblick und Planung mit den wichtigsten Eckdaten
- **Rückblick** (`/rueckblick`): Dashboard der Trainingshistorie
- **Planung** (`/planung`): Events, verfügbare Zeit, Prognose und Kalender

## Trainingsplanung

Bis zu drei **Hauptevents** bestimmen die Periodisierung, rückwärts gerechnet:
Grundlage → Aufbau → Spezifisch → Tapering → Event → Regeneration, mit einer
Entlastungswoche nach je drei Belastungswochen. **Nebenevents** (z. B. Brevets) werden als
Aufbauevents eingebaut – mit Vorbelastung bzw. Ruhe davor und Erholung danach.

Die Wochenbelastung ergibt sich aus der aktuellen Fitness (CTL) und der gewünschten
Steigerung je Phase, begrenzt durch die verfügbare Zeit je Wochentag. Jede Einheit hat
konkrete Vorgaben mit Wattbereichen auf Basis der aktuellen FTP.

Der Plan wird nicht gespeichert, sondern bei jedem Aufruf neu berechnet. Neue Aktivitäten,
geänderte Events oder Verfügbarkeiten wirken sich daher sofort aus.

## Dashboard

`uv run trainingsplan serve` und http://127.0.0.1:8000 öffnen. Zeitraum wählbar
(3 Monate bis alles); enthält:

- Kennzahlen: Aktivitäten, Trainingszeit, Raddistanz, Höhenmeter, Ø Radstunden pro Woche,
  Fahrten ab 4 h, längste Fahrt sowie Fitness/Ermüdung/Form von heute
- Fitness (CTL, 42 Tage) und Ermüdung (ATL, 7 Tage), darunter die Form (TSB)
- Wochenumfang in Stunden, getrennt nach Rad, eBike und Sonstigem
- Raddistanz im Jahresvergleich (kumuliert)
- FTP-Verlauf laut Gerät und manuell erfasst
- Lange Fahrten und letzte Aktivitäten als Tabelle

Zum Ausprobieren ohne echte Daten gibt es Demo-Daten in einem eigenen Ordner:

```sh
TP_DATA_DIR=./demo-data uv run python scripts/seed_demo.py
TP_DATA_DIR=./demo-data uv run trainingsplan serve
```

## Garmin anbinden

Beide Wege liefern die Original-FIT-Dateien und landen im selben Import. Dieselbe Fahrt
wird dabei nur einmal gespeichert (Erkennung über Dateiinhalt und Startzeit).

**Zugang einrichten:** In Garmin Connect Web einen *Personal API Key* erstellen
(Laufzeit am besten 1 Jahr; der Key wird nur einmal angezeigt). Dann:

```sh
uv run trainingsplan garmin-key     # Key im Schlüsselbund speichern
uv run trainingsplan garmin-check   # Verbindung testen
```

**Historie und laufende Aktualisierung über die API:**

```sh
uv run trainingsplan sync                     # ab letzter Aktivität (beim ersten Mal: 4 Jahre)
uv run trainingsplan sync --since 2023-01-01  # gezielt ab einem Datum
```

**Alternative für die Historie – Garmin-Datenexport:** Falls die API nicht weit genug
zurückreicht, im Garmin-Konto den Datenexport anfordern und das ZIP importieren:

```sh
uv run trainingsplan import-export ~/Downloads/<export>.zip
```

## Leistungsschwellen

FTP und Schwellenpuls werden zunächst aus den FIT-Dateien übernommen (Werte, die zum
Zeitpunkt der Fahrt auf dem Gerät eingestellt waren). Eigene Werte haben Vorrang und
gelten ab dem angegebenen Datum bis zum nächsten Eintrag:

```sh
uv run trainingsplan threshold-add 2024-03-01 --ftp 265 --lthr 166 --note "FTP-Test"
uv run trainingsplan recompute                 # Belastung aller Fahrten neu berechnen
```

Die Datenbank lässt sich jederzeit neu aufbauen, die Rohdateien in `data/raw/` bleiben
erhalten: `uv run trainingsplan init-db --reset` und anschließend
`uv run trainingsplan import-export data/raw`.

## Nächste Schritte

1. ~~FIT-Import aus Garmin-Export und Personal API, TSS pro Aktivität~~
2. ~~Dashboard: Wochenumfänge, lange Fahrten, Fitness/Ermüdung/Form (CTL/ATL/TSB)~~
3. Gesundheitsdaten (HRV, Schlaf) über die Personal API
4. ~~Ziele erfassen und Planungsvorausschau~~
5. Geplante und absolvierte Einheiten abgleichen, Plan an Abweichungen anpassen
