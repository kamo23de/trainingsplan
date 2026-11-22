import io
import zipfile
from datetime import date

from fitfactory import make_fit

from trainingsplan.sources import garmin_api


class FakeClient:
    def __init__(self, total: int):
        self.total = total
        self.calls = []

    def search_activities(self, *, start, limit, start_date, end_date):
        self.calls.append(start)
        ids = range(start, min(start + limit, self.total))
        return [{"activityId": i + 1} for i in ids]

    def download_activity(self, activity_id):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr(f"{activity_id}_ACTIVITY.fit", make_fit())
        return buffer.getvalue()


def test_pagination_fetches_all_pages(monkeypatch):
    monkeypatch.setattr(garmin_api, "PAUSE_S", 0)
    client = FakeClient(total=250)
    found = list(garmin_api.iter_activities(client, date(2022, 1, 1), date(2026, 1, 1)))
    assert len(found) == 250
    assert client.calls == [0, 100, 200]


def test_download_extracts_fit_from_zip(monkeypatch):
    monkeypatch.setattr(garmin_api, "PAUSE_S", 0)
    files = garmin_api.download_fit_files(FakeClient(total=1), 42)
    assert [name for name, _ in files] == ["42_ACTIVITY.fit"]


def test_records_accepts_wrapped_payload():
    assert garmin_api._records({"activityList": [{"activityId": 1}]}) == [{"activityId": 1}]
    assert garmin_api._records(None) == []
