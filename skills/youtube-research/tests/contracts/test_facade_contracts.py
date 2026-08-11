from scripts.youtube_research import YouTubeResearch


class Delegate:
    def __getattr__(self, name):
        def call(*args, **kwargs):
            return {"method": name, "args": args, "kwargs": kwargs}

        return call


class StorageDelegate:
    def snapshot_video(self, *args, **kwargs):
        self.video = (args, kwargs)

    def snapshot_channel(self, *args, **kwargs):
        self.channel = (args, kwargs)

    def get_video_snapshots(self, *_args):
        return [{"video": 1}]

    def get_channel_snapshots(self, *_args):
        return [{"channel": 1}]

    def get_keyword_snapshots(self, *_args):
        return [{"keyword": 1}]


def facade(storage=True):
    instance = YouTubeResearch.__new__(YouTubeResearch)
    delegate = Delegate()
    instance.client = delegate
    instance.search_mod = delegate
    instance.channel_mod = delegate
    instance.video_mod = delegate
    instance.analytics_mod = delegate
    instance.browse_mod = delegate
    instance.report_mod = delegate
    instance.tracking_mod = delegate
    instance.storage = StorageDelegate() if storage else None
    return instance


def test_facade_collection_and_analytics_delegation():
    yt = facade()
    assert yt.search("x")["method"] == "search"
    assert yt.search_suggestions("x")["method"] == "search_suggestions"
    assert yt.trending()["method"] == "trending"
    assert yt.channel_info("x")["method"] == "channel_info"
    assert yt.channel_videos("x")["method"] == "channel_videos"
    assert yt.channel_stats("x")["method"] == "channel_stats"
    assert yt.video_info("x")["method"] == "video_info"
    assert yt.video_batch(["x"])["method"] == "video_batch"
    assert yt.estimate_ctr({})["method"] == "estimate_ctr"
    assert yt.estimate_retention({})["method"] == "estimate_retention"
    rpm = yt.estimate_rpm({}, scenario_profile="general_user_assumption")
    assert rpm["method"] == "estimate_rpm"
    assert rpm["args"] == ({}, None, None, "general_user_assumption", None)
    assert yt.detect_niche({})["method"] == "detect_niche"
    assert yt.suggested_for("x")["method"] == "suggested_for"
    assert yt.find_in_suggested("x")["method"] == "find_in_suggested"
    assert yt.browse_feed_sample()["method"] == "browse_feed_sample"
    assert yt.check_browse_presence("x")["method"] == "check_browse_presence"
    assert yt.competitor_report("x")["method"] == "competitor_report"
    assert yt.keyword_report("x")["method"] == "keyword_report"
    assert yt.to_markdown({})["method"] == "to_markdown"
    assert yt.snapshot_video_live("x")["method"] == "snapshot_video_live"
    assert yt.snapshot_channel_live("x")["method"] == "snapshot_channel_live"
    assert yt.snapshot_keyword_live("x")["method"] == "snapshot_keyword_live"
    assert yt.calculate_vph("x")["method"] == "calculate_vph"
    assert yt.keyword_competition_score("x", [])["method"] == "keyword_competition_score"
    assert yt.competitor_tracking(["x"])["method"] == "compare_competitors"


def test_facade_storage_contracts_and_unavailable():
    yt = facade()
    assert yt.snapshot_video("video000001").status == "ok"
    assert yt.snapshot_channel("UC12345678901234567890").status == "ok"
    assert yt.video_history("video000001").status == "ok"
    assert yt.channel_history("UC12345678901234567890").status == "ok"
    assert yt.keyword_history("ai").status == "ok"
    unavailable = facade(False)
    assert unavailable.snapshot_video("x").error_code == "storage_unavailable"
    assert unavailable.snapshot_channel("x").error_code == "storage_unavailable"
    assert unavailable.video_history("x").status == "error"
    assert unavailable.channel_history("x").status == "error"
    assert unavailable.keyword_history("x").status == "error"
