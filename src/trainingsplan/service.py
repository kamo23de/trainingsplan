"""Hintergrunddienste auf dem Mac (launchd).

Zwei LaunchAgents im Benutzerkonto:

- ``de.trainingsplan.server`` startet die App beim Anmelden und nach einem Absturz neu.
- ``de.trainingsplan.sync`` ruft regelmäßig (Standard: stündlich) neue Aktivitäten
  von Garmin ab und friert dabei die Tagesplanung für den Passungs-Score ein.

Beide laufen nur, solange du angemeldet bist und der Mac nicht schläft. launchd
startet einen Dienst nie doppelt: Läuft ein Abruf noch, wird der nächste
übersprungen. Ausgaben landen in ``~/Library/Logs/trainingsplan/``.
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

SERVER_LABEL = "de.trainingsplan.server"
SYNC_LABEL = "de.trainingsplan.sync"
LABELS = (SERVER_LABEL, SYNC_LABEL)

PROJECT_DIR = Path(__file__).resolve().parents[2]
AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
LOG_DIR = Path.home() / "Library" / "Logs" / "trainingsplan"

Runner = Callable[[list[str]], subprocess.CompletedProcess]


class ServiceError(RuntimeError):
    pass


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def find_uv() -> str:
    candidates = [
        shutil.which("uv"),
        "/opt/homebrew/bin/uv",
        str(Path.home() / ".local/bin/uv"),
        "/usr/local/bin/uv",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise ServiceError("uv nicht gefunden. Installieren mit: brew install uv")


@dataclass
class ServiceConfig:
    uv: str
    project: Path = PROJECT_DIR
    port: int = 8000
    interval_minutes: int = 60
    log_dir: Path = LOG_DIR

    def environment(self) -> dict[str, str]:
        # launchd startet mit minimalem PATH; Homebrew und uv ergänzen
        path = os.pathsep.join(
            [
                str(Path(self.uv).parent),
                "/opt/homebrew/bin",
                "/usr/local/bin",
                "/usr/bin",
                "/bin",
                "/usr/sbin",
                "/sbin",
            ]
        )
        env = {"PATH": path, "LANG": "de_DE.UTF-8", "PYTHONUNBUFFERED": "1"}
        # Eigene Einstellungen aus der Shell übernehmen (z. B. TP_DATA_DIR)
        env.update({k: v for k, v in os.environ.items() if k.startswith("TP_")})
        return env


def server_plist(cfg: ServiceConfig) -> dict:
    return {
        "Label": SERVER_LABEL,
        "ProgramArguments": [
            cfg.uv,
            "run",
            "--project",
            str(cfg.project),
            "trainingsplan",
            "serve",
            "--no-reload",
            "--host",
            "127.0.0.1",
            "--port",
            str(cfg.port),
        ],
        "WorkingDirectory": str(cfg.project),
        "EnvironmentVariables": cfg.environment(),
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},  # nach Absturz neu starten
        "ThrottleInterval": 30,
        "ProcessType": "Background",
        "StandardOutPath": str(cfg.log_dir / "server.log"),
        "StandardErrorPath": str(cfg.log_dir / "server.log"),
    }


def sync_plist(cfg: ServiceConfig) -> dict:
    return {
        "Label": SYNC_LABEL,
        "ProgramArguments": [
            cfg.uv,
            "run",
            "--project",
            str(cfg.project),
            "trainingsplan",
            "sync",
            "--quiet",
        ],
        "WorkingDirectory": str(cfg.project),
        "EnvironmentVariables": cfg.environment(),
        "RunAtLoad": True,  # auch direkt nach dem Anmelden bzw. Aufwachen
        "StartInterval": cfg.interval_minutes * 60,
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "StandardOutPath": str(cfg.log_dir / "sync.log"),
        "StandardErrorPath": str(cfg.log_dir / "sync.log"),
    }


def _domain() -> str:
    return f"gui/{os.getuid()}"


def _check_platform() -> None:
    if sys.platform != "darwin":
        raise ServiceError(
            "Hintergrunddienste gibt es hier nur für macOS. Auf einem Linux-Server stattdessen "
            "einen systemd-Timer oder cron verwenden, z. B.: "
            "0 * * * * cd /pfad/trainingsplan && uv run trainingsplan sync --quiet"
        )


def install(
    cfg: ServiceConfig, with_server: bool = True, agents_dir: Path = AGENTS_DIR, run: Runner = _run
) -> list[Path]:
    """Schreibt die LaunchAgents und lädt sie. Bereits geladene werden ersetzt."""
    agents_dir.mkdir(parents=True, exist_ok=True)
    cfg.log_dir.mkdir(parents=True, exist_ok=True)
    plists = [(SYNC_LABEL, sync_plist(cfg))]
    if with_server:
        plists.insert(0, (SERVER_LABEL, server_plist(cfg)))
    written = []
    for label, data in plists:
        path = agents_dir / f"{label}.plist"
        run(["launchctl", "bootout", f"{_domain()}/{label}"])  # alte Version entladen
        with path.open("wb") as f:
            plistlib.dump(data, f)
        result = run(["launchctl", "bootstrap", _domain(), str(path)])
        if result.returncode != 0:
            raise ServiceError(f"{label} konnte nicht geladen werden: {result.stderr.strip()}")
        written.append(path)
    if not with_server:  # nur Abruf gewünscht: evtl. vorhandenen Server-Dienst entfernen
        uninstall(labels=(SERVER_LABEL,), agents_dir=agents_dir, run=run)
    return written


def uninstall(
    labels: tuple[str, ...] = LABELS, agents_dir: Path = AGENTS_DIR, run: Runner = _run
) -> list[Path]:
    removed = []
    for label in labels:
        run(["launchctl", "bootout", f"{_domain()}/{label}"])
        path = agents_dir / f"{label}.plist"
        if path.exists():
            path.unlink()
            removed.append(path)
    return removed


@dataclass
class Status:
    label: str
    installed: bool
    loaded: bool
    running: bool
    last_exit: str | None


def status(agents_dir: Path = AGENTS_DIR, run: Runner = _run) -> list[Status]:
    out = []
    for label in LABELS:
        installed = (agents_dir / f"{label}.plist").exists()
        result = run(["launchctl", "print", f"{_domain()}/{label}"])
        loaded = result.returncode == 0
        running = loaded and "state = running" in result.stdout
        last_exit = None
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("last exit code ="):
                last_exit = line.split("=", 1)[1].strip()
        out.append(Status(label, installed, loaded, running, last_exit))
    return out


def tail(path: Path, lines: int = 20) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(errors="replace").splitlines()[-lines:]
