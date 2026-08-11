from scripts.channel import ChannelModule
from scripts.result import Result


class ChannelStub(ChannelModule):
    def __init__(self, videos):
        self.videos = videos

    def channel_info(self, _channel):
        return Result(
            status="ok", items=[{"channel_id": "UC12345678901234567890", "name": "Channel"}]
        )

    def channel_videos(self, _channel, limit=30, max_pages=20):
        return self.videos


def test_empty_channel_sample_is_partial():
    result = ChannelStub(Result(status="empty", reason="none")).channel_stats(
        "UC12345678901234567890"
    )
    assert result.status == "partial"
    assert result.items[0]["avg_views"] is None
