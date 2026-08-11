import pytest

from scripts.browse_suggested import BrowseSuggestedModule
from scripts.parsers import extract_text, parse_count, parse_duration
from scripts.result import Result
from scripts.search import (
    SearchModule,
    parse_duration_seconds,
    parse_view_count,
)
from scripts.time_utils import parse_utc
from scripts.validation import validate_id_batch, validate_sort
from tests.conftest import ScriptedClient


def test_parser_compatibility_and_remaining_value_states():
    assert parse_view_count("10 views") == 10
    assert parse_duration_seconds("1:00") == 60
    assert extract_text({"content": "content"}) == "content"
    assert extract_text({"simpleText": 1}) == ""
    assert parse_count(None).status == "missing"
    assert parse_count("nonsense").status == "invalid"
    assert parse_duration("LIVE now").status == "live"
    with pytest.raises(TypeError):
        parse_utc(None)


def test_search_and_browse_invalid_contracts():
    module = SearchModule(ScriptedClient())
    assert module.search("x", limit=0).status == "error"
    assert module.search_suggestions("x", limit=0).status == "error"
    assert module.trending("bad", limit=1).status == "error"
    client = ScriptedClient()
    client.complete = lambda _q: "invalid"
    assert SearchModule(client).search_suggestions("x").error_code == "invalid_payload_type"

    browse = BrowseSuggestedModule(ScriptedClient())
    assert browse.suggested_for("bad").status == "error"
    assert browse.browse_feed_sample(limit=0).status == "error"
    assert browse.find_in_suggested("video000001").status == "error"
    browse.browse_feed_sample = lambda limit=30: Result.unsupported("drift")
    assert browse.check_browse_presence("UC12345678901234567890").status == "unsupported"


def test_validation_and_result_remaining_branches():
    assert validate_sort(None) is None
    assert validate_id_batch(
        ["UC12345678901234567890"],
        validator=lambda value: value,
    )
    result = Result(status="ok", items=[1], metadata={"has_more": True})
    assert result.ok and not result.partial and result.has_more
    assert "items=1" in repr(result)
    with pytest.raises(TypeError):
        Result(status="ok", items="bad")
    with pytest.raises(TypeError):
        Result(status="ok", items=[1], metadata=[])
