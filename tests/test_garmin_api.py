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


def _http_error(status):
    return garmin_api.HttpError(status_code=status, method="GET", url="u", response_text="")


def test_retry_on_gateway_timeout(monkeypatch):
    monkeypatch.setattr(garmin_api, "PAUSE_S", 0)
    monkeypatch.setattr(garmin_api, "RETRY_DELAYS_S", (0, 0))
    client = FakeClient(total=1)
    original = client.download_activity
    failures = iter([_http_error(504)])

    def flaky(activity_id):
        for exc in failures:
            raise exc
        return original(activity_id)

    client.download_activity = flaky
    assert len(garmin_api.download_fit_files(client, 7)) == 1


def test_no_retry_on_not_found(monkeypatch):
    import pytest

    monkeypatch.setattr(garmin_api, "RETRY_DELAYS_S", (0, 0))
    calls = []

    class Missing(FakeClient):
        def download_activity(self, activity_id):
            calls.append(activity_id)
            raise _http_error(404)

    with pytest.raises(garmin_api.HttpError):
        garmin_api.download_fit_files(Missing(total=1), 7)
    assert calls == [7]


def test_gives_up_after_retries(monkeypatch):
    import pytest

    monkeypatch.setattr(garmin_api, "RETRY_DELAYS_S", (0, 0))
    calls = []

    class Down(FakeClient):
        def download_activity(self, activity_id):
            calls.append(activity_id)
            raise _http_error(504)

    with pytest.raises(garmin_api.HttpError):
        garmin_api.download_fit_files(Down(total=1), 7)
    assert len(calls) == 3
