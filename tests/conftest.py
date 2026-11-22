import pytest

from trainingsplan.config import get_settings
from trainingsplan.storage.db import get_engine


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Jeder Test bekommt einen eigenen Datenordner und eine eigene Datenbank."""
    monkeypatch.setenv("TP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("TP_DATABASE_URL", raising=False)
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()
