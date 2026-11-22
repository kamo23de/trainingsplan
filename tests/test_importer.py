import io
import zipfile
from datetime import UTC, date, datetime

import pytest
from fitfactory import make_fit, make_non_activity_fit
from sqlalchemy import select
from typer.testing import CliRunner

from trainingsplan.cli import app
from trainingsplan.config import get_settings
from trainingsplan.ingest.importer import Outcome, apply_load, import_fit
from trainingsplan.storage.db import get_sessionmaker, init_db
from trainingsplan.storage.models import Activity, AthleteThreshold, LoadBasis


@pytest.fixture
def db():
    init_db()
    with get_sessionmaker()() as session:
        yield session


def _import(db, data, source_id="a", cutoff=None):
    return import_fit(db, get_settings(), data, source="test", source_id=source_id, cutoff=cutoff)


def test_import_stores_activity_raw_file_and_tss(db):
    assert _import(db, make_fit()) == Outcome.IMPORTED
    activity = db.scalars(select(Activity)).one()
    assert activity.load_basis == LoadBasis.POWER
    # 2 h bei IF 0,8 (200 W NP / 250 W FTP aus der Datei) = 128 TSS
    assert activity.tss == pytest.approx(128.0)
    assert (get_settings().data_dir / activity.raw_file).exists()


def test_same_file_twice_is_duplicate(db):
    data = make_fit()
    _import(db, data)
    assert _import(db, data, source_id="b") == Outcome.DUPLICATE


def test_same_start_from_other_source_is_duplicate(db):
    _import(db, make_fit(serial=1))
    assert _import(db, make_fit(serial=2), source_id="b") == Outcome.DUPLICATE


def test_activity_before_cutoff_is_skipped(db):
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    assert _import(db, make_fit(), cutoff=cutoff) == Outcome.TOO_OLD


def test_non_activity_is_skipped(db):
    assert _import(db, make_non_activity_fit()) == Outcome.NOT_ACTIVITY


def test_ebike_uses_heart_rate(db):
    _import(db, make_fit(sub_sport="e_bike_fitness", normalized_power=None, avg_hr=132))
    assert db.scalars(select(Activity)).one().load_basis == LoadBasis.HEART_RATE


def test_manual_threshold_overrides_file_value(db):
    _import(db, make_fit())
    db.add(AthleteThreshold(valid_from=date(2025, 1, 1), ftp_w=200))
    activity = db.scalars(select(Activity)).one()
    apply_load(db, activity)
    # IF = 200/200 = 1,0 → 2 h = 200 TSS
    assert activity.tss == pytest.approx(200.0)


def test_import_export_command_reads_nested_zip(tmp_path):
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        z.writestr("ride.fit", make_fit())
    export = tmp_path / "export"
    export.mkdir()
    with zipfile.ZipFile(export / "garmin.zip", "w") as z:
        z.writestr("uploaded/files.zip", inner.getvalue())
        z.writestr("monitor.fit", make_non_activity_fit())

    result = CliRunner().invoke(app, ["import-export", str(export)])
    assert result.exit_code == 0, result.output
    assert "1 importiert" in result.output
    assert "1 keine Aktivität" in result.output


def test_import_export_accepts_zip_file_directly(tmp_path):
    archive = tmp_path / "export.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("a/ride.fit", make_fit())
    result = CliRunner().invoke(app, ["import-export", str(archive)])
    assert result.exit_code == 0, result.output
    assert "1 importiert" in result.output
