from scripts.browse_suggested import BrowseSuggestedModule
from scripts.result import Result


class Stub(BrowseSuggestedModule):
    def __init__(self):
        pass

    def suggested_for(self, video_id, limit=20, max_pages=20):
        return Result(
            status="ok",
            items=[
                {
                    "videoId": "target00001",
                    "video_id": "target00001",
                    "title": "Target",
                    "channel": "Target Channel",
                    "channelId": "UC12345678901234567890",
                    "views": 1,
                }
            ],
        )


def test_dual_criteria_match_is_emitted_once():
    result = Stub().find_in_suggested(
        "source00001",
        target_channel_id="UC12345678901234567890",
        target_video_id="target00001",
    )
    entries = result.items[0]["found_entries"]
    assert len(entries) == 1
    assert entries[0]["matched_by"] == ["video_id", "channel_id"]
