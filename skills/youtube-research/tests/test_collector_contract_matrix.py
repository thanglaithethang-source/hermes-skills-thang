from scripts.browse_suggested import BrowseSuggestedModule
from scripts.channel import ChannelModule
from scripts.result import Result
from scripts.search import SearchModule
from tests.conftest import ScriptedClient

VALID_CHANNEL = "UC12345678901234567890"
VALID_VIDEO = "video000001"


class CompleteClient(ScriptedClient):
    def __init__(self, complete):
        super().__init__()
        self.complete_value = complete

    def complete(self, _q):
        return self.complete_value


def test_search_suggestion_and_trending_statuses(fixture_json):
    assert SearchModule(CompleteClient(["one"])).search_suggestions("a").status == "ok"
    assert SearchModule(CompleteClient([])).search_suggestions("a").status == "empty"
    assert (
        SearchModule(CompleteClient({"_error": True, "_status": 500, "_message": "bad"}))
        .search_suggestions("a")
        .status
        == "error"
    )

    unsupported = SearchModule(ScriptedClient()).trending("VN")
    assert unsupported.status == "unsupported"
    client = ScriptedClient()
    client.get_trending = lambda region: fixture_json("browse_recognized_empty.json")
    assert SearchModule(client).trending("US").status == "empty"
    client.get_trending = lambda region: fixture_json("search_unknown_shape.json")
    assert SearchModule(client).trending("US").status == "unsupported"


def test_browse_suggested_contracts(fixture_json):
    unknown = BrowseSuggestedModule(
        ScriptedClient(next_=[fixture_json("search_unknown_shape.json")])
    ).suggested_for(VALID_VIDEO)
    assert unknown.status == "unsupported"
    empty_payload = {
        "contents": {
            "twoColumnWatchNextResults": {"secondaryResults": {"secondaryResults": {"results": []}}}
        }
    }
    empty = BrowseSuggestedModule(ScriptedClient(next_=[empty_payload])).suggested_for(VALID_VIDEO)
    assert empty.status == "empty"

    module = BrowseSuggestedModule.__new__(BrowseSuggestedModule)
    module.browse_feed_sample = lambda limit=30: Result(
        status="ok",
        items=[
            {
                "video_id": VALID_VIDEO,
                "channel_id": VALID_CHANNEL,
                "channelId": VALID_CHANNEL,
            }
        ],
    )
    presence = module.check_browse_presence(VALID_CHANNEL)
    assert presence.status == "ok" and presence.items[0]["found"] is True
    module.browse_feed_sample = lambda limit=30: Result.error("bad")
    assert module.check_browse_presence(VALID_CHANNEL).status == "error"


def test_channel_info_unknown_and_channel_stats_branches(fixture_json):
    unknown = ChannelModule(
        ScriptedClient(browse=[fixture_json("search_unknown_shape.json")])
    ).channel_info(VALID_CHANNEL)
    assert unknown.status == "unsupported"

    module = ChannelModule.__new__(ChannelModule)
    module.channel_info = lambda _id: Result(
        status="ok", items=[{"channel_id": VALID_CHANNEL, "name": "Channel"}]
    )
    module.channel_videos = lambda _id, limit=30: Result(
        status="ok", items=[{"views": 10}, {"views": 30}, {"views": None}]
    )
    stats = module.channel_stats(VALID_CHANNEL)
    assert stats.status == "ok"
    assert stats.items[0]["avg_views"] == 20
    module.channel_videos = lambda _id, limit=30: Result.unsupported("drift")
    assert module.channel_stats(VALID_CHANNEL).status == "unsupported"
