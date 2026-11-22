import pytest

from trainingsplan.analytics.load import compute_load, power_tss
from trainingsplan.storage.models import LoadBasis


def test_one_hour_at_ftp_is_100_tss():
    tss, intensity = power_tss(3600, 250, 250)
    assert tss == pytest.approx(100)
    assert intensity == pytest.approx(1.0)


def test_power_preferred_when_available():
    basis, tss, _ = compute_load(
        duration_s=7200, normalized_power_w=200, avg_hr_bpm=140, ftp_w=250, lthr_bpm=165
    )
    assert basis == LoadBasis.POWER
    assert tss == pytest.approx(2 * 0.8**2 * 100)


def test_ebike_uses_heart_rate_even_with_power():
    basis, _, _ = compute_load(
        duration_s=3600,
        normalized_power_w=300,
        avg_hr_bpm=132,
        ftp_w=250,
        lthr_bpm=165,
        is_ebike=True,
    )
    assert basis == LoadBasis.HEART_RATE


def test_no_data_gives_no_load():
    basis, tss, _ = compute_load(
        duration_s=3600, normalized_power_w=None, avg_hr_bpm=None, ftp_w=250, lthr_bpm=165
    )
    assert basis == LoadBasis.NONE
    assert tss is None
