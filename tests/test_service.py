import plistlib
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from trainingsplan import service
from trainingsplan.cli import app


class FakeLaunchctl:
    def __init__(self, print_output=""):
        self.calls = []
        self.print_output = print_output

    def __call__(self, cmd):
        self.calls.append(cmd)
        out = self.print_output if cmd[1] == "print" else ""
        code = 0 if cmd[1] != "print" or self.print_output else 113
        return subprocess.CompletedProcess(cmd, code, stdout=out, stderr="")


def _cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("TP_DATA_DIR", "/Users/test/trainingsplan/data")
    return service.ServiceConfig(
        uv="/opt/homebrew/bin/uv",
        project=Path("/Users/test/trainingsplan"),
        interval_minutes=60,
        log_dir=tmp_path / "logs",
    )


def test_server_plist_runs_locally_and_restarts(tmp_path, monkeypatch):
    p = service.server_plist(_cfg(tmp_path, monkeypatch))
    args = p["ProgramArguments"]
    assert args[:4] == ["/opt/homebrew/bin/uv", "run", "--project", "/Users/test/trainingsplan"]
    assert "--no-reload" in args and args[args.index("--host") + 1] == "127.0.0.1"
    assert p["RunAtLoad"] and p["KeepAlive"] == {"SuccessfulExit": False}
    assert p["WorkingDirectory"] == "/Users/test/trainingsplan"
    assert p["EnvironmentVariables"]["TP_DATA_DIR"] == "/Users/test/trainingsplan/data"
    assert "/opt/homebrew/bin" in p["EnvironmentVariables"]["PATH"]


def test_sync_plist_runs_hourly_and_quietly(tmp_path, monkeypatch):
    p = service.sync_plist(_cfg(tmp_path, monkeypatch))
    assert p["StartInterval"] == 3600
    assert p["ProgramArguments"][-2:] == ["sync", "--quiet"]
    assert p["StandardOutPath"].endswith("sync.log")


def test_install_writes_valid_plists_and_loads_them(tmp_path, monkeypatch):
    fake = FakeLaunchctl()
    agents = tmp_path / "LaunchAgents"
    written = service.install(_cfg(tmp_path, monkeypatch), agents_dir=agents, run=fake)
    assert [p.name for p in written] == [
        "de.trainingsplan.server.plist",
        "de.trainingsplan.sync.plist",
    ]
    for path in written:
        with path.open("rb") as f:
            assert plistlib.load(f)["Label"] in service.LABELS
    bootstraps = [c for c in fake.calls if c[1] == "bootstrap"]
    assert len(bootstraps) == 2 and bootstraps[0][2].startswith("gui/")


def test_install_without_server_removes_server_agent(tmp_path, monkeypatch):
    fake = FakeLaunchctl()
    agents = tmp_path / "LaunchAgents"
    service.install(_cfg(tmp_path, monkeypatch), agents_dir=agents, run=fake)
    service.install(_cfg(tmp_path, monkeypatch), with_server=False, agents_dir=agents, run=fake)
    assert sorted(p.name for p in agents.iterdir()) == ["de.trainingsplan.sync.plist"]


def test_uninstall_and_status(tmp_path, monkeypatch):
    agents = tmp_path / "LaunchAgents"
    service.install(_cfg(tmp_path, monkeypatch), agents_dir=agents, run=FakeLaunchctl())
    running = FakeLaunchctl("state = running\n\tlast exit code = 0\n")
    assert all(s.running and s.installed for s in service.status(agents_dir=agents, run=running))
    removed = service.uninstall(agents_dir=agents, run=FakeLaunchctl())
    assert len(removed) == 2 and not list(agents.iterdir())
    assert not any(
        s.installed or s.loaded for s in service.status(agents_dir=agents, run=FakeLaunchctl())
    )


def test_quiet_sync_prints_one_timestamped_error_line(monkeypatch):
    monkeypatch.setattr("trainingsplan.credentials.get_garmin_api_key", lambda: None)
    monkeypatch.setattr("trainingsplan.sources.garmin_api.get_garmin_api_key", lambda: None)
    result = CliRunner().invoke(app, ["sync", "--quiet"])
    assert result.exit_code == 1
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) == 1 and "Fehler: Kein Garmin API Key" in lines[0]
    assert lines[0][:4].isdigit()  # beginnt mit Datum
