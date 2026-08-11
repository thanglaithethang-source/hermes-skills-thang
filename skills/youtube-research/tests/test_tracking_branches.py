from scripts.result import Result
from scripts.tracking import TrackingModule


class Storage:
    def __init__(self):
        self.video = None
        self.keyword = None

    def snapshot_video(self, *args, **kwargs):
        self.video = (args, kwargs)

    def snapshot_keyword(self, *args, **kwargs):
        self.keyword = (args, kwargs)


class Video:
    def video_info(self, _id):
        return Result(
            status="ok",
            items=[
                {
                    "video_id": "video000001",
                    "channel_id": "UC12345678901234567890",
                    "view_count": 10,
                    "like_count": 1,
                    "comment_count": 1,
                }
            ],
        )


class Search:
    def search(self, _query, limit=20):
        return Result(status="ok", items=[{"videoId": "video000001", "views": 10}])


def test_snapshot_video_keyword_and_compare_empty():
    storage = Storage()
    module = TrackingModule(None, Video(), Search(), None, storage)
    assert module.snapshot_video_live("video000001").status == "ok"
    assert storage.video is not None
    assert module.snapshot_keyword_live("ai").status == "ok"
    assert storage.keyword is not None
    no_storage = TrackingModule(None, Video(), Search(), None, None)
    assert no_storage.snapshot_video_live("video000001").status == "error"

    module.snapshot_channel_live = lambda _id: Result(status="ok", items=[{}])
    module.channel_growth = lambda *_args: Result(status="empty", reason="none")
    compared = module.compare_competitors([], refresh=False)
    assert compared.status == "empty"
