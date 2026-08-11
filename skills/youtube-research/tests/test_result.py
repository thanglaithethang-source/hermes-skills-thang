import json

from scripts.browse_suggested import BrowseSuggestedModule
from scripts.channel import ChannelModule
from scripts.result import Result
from scripts.search import SearchModule
from scripts.video import VideoModule
from tests.conftest import ScriptedClient


def test_result_status_matrix_and_serialization(fixture_json):
    ok = Result.collection(items=[1], requested=1, has_more=True)
    assert ok.status == "ok" and ok.truncated
    assert Result.collection(items=[], requested=2).status == "empty"
    assert Result.error("bad").status == "error"
    assert Result.error("bad", items=[1]).status == "partial"
    assert Result.unsupported("no").status == "unsupported"
    json.dumps(ok.to_dict())


def test_search_error_empty_and_partial(fixture_json):
    error = fixture_json("api_error_first_page.json")
    empty = fixture_json("successful_empty_search.json")
    assert SearchModule(ScriptedClient(search=[error])).search("x").status == "error"
    assert SearchModule(ScriptedClient(search=[empty])).search("x").status == "empty"
    initial = fixture_json("search_initial.json")
    partial = SearchModule(ScriptedClient(search=[initial, error])).search("x", limit=2)
    assert partial.status == "partial"
    assert [item["videoId"] for item in partial.items] == ["first"]


def test_presence_does_not_turn_error_into_false(fixture_json):
    module = BrowseSuggestedModule(
        ScriptedClient(next_=[fixture_json("api_error_first_page.json")])
    )
    result = module.find_in_suggested("source", target_video_id="target")
    assert result.status == "error"
    assert result.items == []


def test_channel_and_video_collectors_return_result(fixture_json):
    channel = ChannelModule(
        ScriptedClient(browse=[fixture_json("channel_info_success.json")])
    ).channel_info("UC12345678901234567890")
    assert channel.status == "ok" and channel.items[0]["channel_id"] == "UC1"
    client = ScriptedClient(next_=[fixture_json("video_info_success.json"), {}])
    video = VideoModule(client).video_info("video000001")
    assert video.status == "ok" and video.items[0]["view_count"] == 123
