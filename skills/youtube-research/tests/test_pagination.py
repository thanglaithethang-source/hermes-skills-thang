from scripts.channel import ChannelModule
from scripts.search import SearchModule
from tests.conftest import ScriptedClient


def test_two_page_search_commands(fixture_json):
    client = ScriptedClient(
        search=[
            fixture_json("search_initial.json"),
            fixture_json("search_continuation_commands.json"),
        ]
    )
    result = SearchModule(client).search("ai", limit=5)
    assert result.status == "ok"
    assert [item["videoId"] for item in result.items] == ["first", "second"]
    assert result.metadata["pages_requested"] == 2


def test_two_page_channel_actions(fixture_json):
    client = ScriptedClient(
        browse=[
            fixture_json("channel_initial.json"),
            fixture_json("channel_continuation_actions.json"),
        ]
    )
    result = ChannelModule(client).channel_videos("UC12345678901234567890", limit=5)
    assert [item["videoId"] for item in result.items] == ["channel-first", "channel-second"]
    assert client.calls[1][1]["continuation"] == "CHANNEL_NEXT"


def test_duplicate_and_repeated_token_stop(fixture_json):
    initial = fixture_json("search_initial.json")
    repeated = fixture_json("search_initial.json")
    repeated["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"][
        "sectionListRenderer"
    ]["contents"][0]["itemSectionRenderer"]["contents"][0]["videoRenderer"]["videoId"] = "first"
    client = ScriptedClient(search=[initial, repeated])
    result = SearchModule(client).search("ai", limit=5)
    assert result.status == "partial"
    assert result.metadata["stop_reason"] == "no_progress"
    assert len(result.items) == 1
