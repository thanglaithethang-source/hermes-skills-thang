import pytest

from scripts.parsers import parse_duration


@pytest.mark.parametrize(
    ("raw", "value"),
    [
        ("00:01", 1),
        ("59:59", 3599),
        ("1:00:00", 3600),
        ("1 hour, 2 minutes, 3 seconds", 3723),
        ("1 giờ, 2 phút, 3 giây", 3723),
    ],
)
def test_valid_duration_formats(raw, value):
    parsed = parse_duration(raw)
    assert parsed.value == value and parsed.status == "parsed"


@pytest.mark.parametrize("raw", [None, "", "0:00", "1:60", "1:60:00", "abc"])
def test_missing_invalid_duration_never_zero(raw):
    assert parse_duration(raw).value is None


def test_live_and_upcoming_duration_states():
    assert parse_duration("LIVE").status == "live"
    assert parse_duration("Premiere upcoming").status == "upcoming"
