import pytest

from scripts.parsers import extract_text, parse_count


@pytest.mark.parametrize(
    ("raw", "value"),
    [
        ("1.2M views", 1_200_000),
        ("1,2 Tr lượt xem", 1_200_000),
        ("89\u202fnghìn người đăng ký", 89_000),
        ("0 views", 0),
        ("34.734 lượt xem", 34_734),
    ],
)
def test_locale_counts(raw, value):
    assert parse_count(raw).value == value


def test_hidden_malformed_and_text_nodes():
    assert parse_count("hidden subscribers").status == "hidden"
    assert parse_count("1.2.3K views").status == "invalid"
    assert extract_text({"runs": [1, {"text": "ok"}, None]}) == "ok"
    assert extract_text(["bad"]) == ""
