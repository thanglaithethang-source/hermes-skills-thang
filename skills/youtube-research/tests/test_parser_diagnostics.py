from scripts.search import SearchModule
from tests.conftest import ScriptedClient


def test_unknown_200_is_unsupported_and_empty_is_empty(fixture_json):
    unknown = SearchModule(
        ScriptedClient(search=[fixture_json("search_unknown_shape.json")])
    ).search("x")
    assert unknown.status == "unsupported"
    diagnostic = unknown.metadata["parser_diagnostics"][0]
    assert diagnostic["recognized_container"] is False
    assert diagnostic["shape_fingerprint"]
    assert "visitorData" not in str(diagnostic)

    empty = SearchModule(
        ScriptedClient(search=[fixture_json("successful_empty_search.json")])
    ).search("x")
    assert empty.status == "empty"
    assert empty.metadata["parser_diagnostics"][0]["recognized_container"] is True


def test_mixed_parser_coverage_is_partial(fixture_json):
    result = SearchModule(
        ScriptedClient(search=[fixture_json("search_mixed_known_unknown.json")])
    ).search("x")
    assert result.status == "partial"
    assert result.items[0]["video_id"] == "knownvideo1"
    assert result.metadata["parser_diagnostics"][0]["unknown_renderer_types"] == [
        "futureVideoRenderer"
    ]


def test_second_page_drift_retains_first_page(fixture_json):
    result = SearchModule(
        ScriptedClient(
            search=[
                fixture_json("search_initial.json"),
                fixture_json("search_unknown_shape.json"),
            ]
        )
    ).search("x", limit=2)
    assert result.status == "partial"
    assert [row["videoId"] for row in result.items] == ["first"]
    assert result.metadata["stop_reason"] == "response_drift"
