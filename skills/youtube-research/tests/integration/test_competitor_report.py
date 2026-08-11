from scripts.report import ReportModule
from scripts.result import Result

VALID_CHANNEL = "UC12345678901234567890"


class Channel:
    def channel_info(self, _value):
        return Result(
            status="ok",
            items=[
                {
                    "channel_id": VALID_CHANNEL,
                    "name": "Channel",
                    "subscriber_count": 10,
                    "video_count": 2,
                }
            ],
        )

    def channel_videos(self, _value, limit=10):
        return Result(
            status="ok",
            items=[
                {"videoId": "video000001", "title": "One", "views": 100},
                {"videoId": "video000002", "title": "Two", "views": 300},
            ],
        )


class Video:
    def video_info(self, video_id):
        return Result(
            status="ok",
            items=[
                {
                    "video_id": video_id,
                    "title": video_id,
                    "view_count": 100,
                    "duration_seconds": 120,
                    "publish_date": "2026-07-20T00:00:00Z",
                    "tags": [],
                }
            ],
        )


class Analytics:
    def estimate_ctr(self, *_args, **_kwargs):
        return {"estimable": False}

    def estimate_retention(self, *_args, **_kwargs):
        return {"estimable": False}

    def estimate_rpm(self, *_args, **_kwargs):
        return {"estimable": False}

    def calculate_vph(self, *_args):
        return {"status": "unavailable", "reason": "no snapshots"}

    def detect_outlier(self, *_args):
        return {"status": "unavailable", "reason": "small sample"}


class Browse:
    def suggested_for(self, *_args, **_kwargs):
        return Result(status="ok", items=[{"videoId": "video000003", "channelId": VALID_CHANNEL}])


def test_competitor_report_and_markdown():
    module = ReportModule.__new__(ReportModule)
    module.channel_mod = Channel()
    module.video_mod = Video()
    module.analytics_mod = Analytics()
    module.browse_mod = Browse()
    module.tracking_mod = None
    result = module.competitor_report(VALID_CHANNEL, video_limit=2)
    assert result.status == "partial"
    report = result.items[0]
    assert report["aggregate_stats"]["median_views"] == 100
    markdown = module.to_markdown(result)
    assert "Competitor Report" in markdown
    assert "PARTIAL REPORT" in markdown
    assert module.to_markdown(Result.error("bad")).startswith("# Report unavailable")


def test_competitor_upstream_errors():
    module = ReportModule.__new__(ReportModule)
    module.channel_mod = Channel()
    module.channel_mod.channel_info = lambda _value: Result.unsupported("drift")
    assert module.competitor_report(VALID_CHANNEL).status == "unsupported"
    module.channel_mod = Channel()
    module.channel_mod.channel_videos = lambda *_args, **_kwargs: Result.error("bad")
    assert module.competitor_report(VALID_CHANNEL).status == "error"
