import pytest

from scripts.formatting import classify_content_format


@pytest.mark.parametrize(
    ("duration", "expected"),
    [(59, "short"), (60, "short"), (180, "short"), (181, "long_form"), (None, "unknown")],
)
def test_format_boundaries(duration, expected):
    assert classify_content_format(duration) == expected
    assert classify_content_format(duration, is_live=True) == "live"
