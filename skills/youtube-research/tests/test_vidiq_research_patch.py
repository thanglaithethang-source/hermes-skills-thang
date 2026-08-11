import sqlite3
from datetime import UTC, datetime, timedelta

from scripts.analytics_estimate import AnalyticsEstimateModule, vidiq_score_client
from scripts.innertube import InnerTubeClient
from scripts.storage import Storage
from tests.test_transport import FakeResponse, Session


def _insert_video(db, video_id, count, observed, **extra):
    columns = ["video_id", "view_count", "snapshot_at", *extra]
    values = [video_id, count, observed, *extra.values()]
    with sqlite3.connect(db.db_path) as connection:
        connection.execute(
            f"INSERT INTO video_snapshots ({','.join(columns)}) "
            f"VALUES ({','.join('?' for _ in values)})",
            values,
        )


def test_vph_snapshot_window_lifetime_fallback_and_live_skip(tmp_path):
    db = Storage(str(tmp_path / "vph-new.db"))
    now = datetime(2026, 1, 7, tzinfo=UTC)
    published = now - timedelta(hours=48)
    _insert_video(
        db,
        "snapshot",
        100,
        (now - timedelta(hours=13)).isoformat(),
        published_at=published.isoformat(),
    )
    _insert_video(
        db,
        "snapshot",
        230,
        now.isoformat(),
        published_at=published.isoformat(),
    )
    result = AnalyticsEstimateModule(storage=db).calculate_vph("snapshot")
    assert result["vph_method"] == "snapshot"
    assert result["vph"] == 10

    _insert_video(
        db,
        "young",
        240,
        now.isoformat(),
        published_at=(now - timedelta(hours=24)).isoformat(),
    )
    average = AnalyticsEstimateModule(storage=db).calculate_vph("young")
    assert average["vph_method"] == "lifetime_average"
    assert average["vph"] == 10

    _insert_video(
        db,
        "live",
        100,
        now.isoformat(),
        published_at=published.isoformat(),
        is_live=1,
    )
    assert AnalyticsEstimateModule(storage=db).calculate_vph("live")["vph"] is None


def test_performance_curve_storage_comparison_and_outlier_rules(tmp_path):
    def clock():
        return datetime(2026, 1, 4, tzinfo=UTC)

    db = Storage(str(tmp_path / "curve.db"), clock=clock)
    published = datetime(2026, 1, 1, tzinfo=UTC)
    for video_id, views in (("a", 1000), ("b", 2000), ("c", 3000)):
        db.snapshot_performance_curve(
            video_id=video_id,
            channel_id="UCcurve",
            published_at=published,
            observed_at=clock(),
            view_count=views,
        )
    curve = db.get_channel_performance_curve("UCcurve")
    assert curve == [
        {
            "age_hours": 72,
            "perc30": 1600.0,
            "perc70": 2400.0,
            "median": 2000.0,
        }
    ]
    comparison = db.compare_video_to_performance_curve("UCcurve", 20_000, 72)
    assert comparison["baseline_views"] == 2000
    assert comparison["score"] == 10

    target = {
        "video_id": "target",
        "channel_id": "UCcurve",
        "view_count": 20_000,
        "duration_seconds": 300,
        "publish_date": published.isoformat(),
    }
    outlier = AnalyticsEstimateModule(storage=db).detect_outlier(
        target, [], as_of=clock()
    )
    assert outlier["metric"] == "vidiq_client_curve_estimate_v1"
    assert outlier["median_multiple"] == 10
    assert outlier["score_label"] == "client estimate"

    target["view_count"] = 999
    assert (
        AnalyticsEstimateModule(storage=db).detect_outlier(target, [], as_of=clock())[
            "median_multiple"
        ]
        is None
    )


def test_curve_bucket_order_rounding_cap_and_early_suppression():
    module = AnalyticsEstimateModule()
    target = {
        "video_id": "target",
        "view_count": 1000,
        "duration_seconds": 300,
        "publish_date": "2026-01-01T00:00:00Z",
    }
    curve = [
        {"age_hours": 24, "perc30": 100, "perc70": 100, "median": 100},
        {"age_hours": 168, "perc30": 10, "perc70": 10, "median": 10},
    ]
    exact = module.detect_outlier(
        target,
        [],
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
        performance_curve=curve,
    )
    assert exact["curve_age_hours"] == 24
    assert exact["median_multiple"] == 10

    capped = module.detect_outlier(
        target,
        [],
        as_of=datetime(2026, 1, 4, tzinfo=UTC),
        performance_curve=[{"age_hours": 72, "perc30": 5, "perc70": 5}],
    )
    assert capped["display_multiple"] == ">100x"

    early = {**target, "publish_date": "2026-01-01T12:00:00Z"}
    suppressed = module.detect_outlier(
        early,
        [],
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
        performance_curve=[{"age_hours": 12, "perc30": 2000, "perc70": 2000}],
    )
    assert suppressed["reason"] == "suppressed_first_24_hours_at_or_below_1x"


def test_autocomplete_is_youtube_specific():
    session = Session([FakeResponse(200, text='["a", [["one"]]]')])
    client = InnerTubeClient(session=session, rate_limit_seconds=0)
    assert client.complete("a") == ["one"]
    params = session.calls[0][1]["params"]
    assert params["ds"] == "yt"
    assert params["client"] == "firefox"


def test_authenticated_player_page_state_fallback():
    tabs = {"tabs": [{"id": 7, "url": "https://www.youtube.com/watch?v=video000001"}]}
    state = {
        "ytInitialData": {
            "videoPrimaryInfoRenderer": {
                "title": {"runs": [{"text": "Page title"}]},
                "viewCount": {
                    "videoViewCountRenderer": {
                        "viewCount": {"simpleText": "1,234 views"}
                    }
                },
            }
        },
        "ytInitialPlayerResponse": {
            "videoDetails": {
                "channelId": "UC123",
                "author": "Channel",
                "lengthSeconds": "60",
            },
            "microformat": {},
        },
    }

    def bridge(command):
        if command["type"] == "list_tabs":
            return tabs
        return {"result": {"value": __import__("json").dumps(state)}}

    client = InnerTubeClient(
        authenticated=False,
        session=Session([FakeResponse(503, text="down")]),
        max_retries=0,
        rate_limit_seconds=0,
        bridge_send=bridge,
    )
    client.authenticated = True
    result = client.player("video000001")
    assert result["_page_state_fallback"] is True
    assert result["videoDetails"]["title"] == "Page title"
    assert result["videoDetails"]["viewCount"] == "1234"


def test_vidiq_client_score_is_labeled_and_capped():
    assert vidiq_score_client(0, 0) == 0
    assert vidiq_score_client(1024, 1) == 30
    result = AnalyticsEstimateModule().vidiq_score_client(2**40, 2**40)
    assert result == {
        "score": 100,
        "label": "client estimate",
        "production_score": False,
    }
