import pytest
from fitfactory import make_fit, make_non_activity_fit

from trainingsplan.ingest.fit import FitParseError, parse_fit


def test_parse_road_ride():
    parsed = parse_fit(make_fit())
    assert parsed.sport == "cycling"
    assert parsed.sub_sport == "road"
    assert not parsed.is_ebike
    assert parsed.moving_time_s == 7200
    assert parsed.normalized_power_w == 200
    assert parsed.avg_hr_bpm == 140
    assert parsed.file_ftp_w == 250
    assert parsed.file_lthr_bpm == 165
    assert parsed.distance_m == 60000


@pytest.mark.parametrize(
    ("sport", "sub_sport"),
    [("cycling", "e_bike_fitness"), ("e_biking", "generic"), ("cycling", "e_bike_mountain")],
)
def test_ebike_detection(sport, sub_sport):
    parsed = parse_fit(make_fit(sport=sport, sub_sport=sub_sport, normalized_power=None))
    assert parsed.is_ebike


def test_non_activity_file_is_rejected():
    with pytest.raises(FitParseError):
        parse_fit(make_non_activity_fit())


def test_garbage_is_rejected():
    with pytest.raises(FitParseError):
        parse_fit(b"not a fit file at all")
