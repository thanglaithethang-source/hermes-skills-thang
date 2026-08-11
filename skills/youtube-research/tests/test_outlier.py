from datetime import UTC, datetime

from scripts.analytics_estimate import AnalyticsEstimateModule

AS_OF = datetime(2026, 7, 27, tzinfo=UTC)


def video(video_id, views, duration=120, published="2026-07-26T00:00:00Z"):
    return {
        "videoId": video_id,
        "views": views,
        "duration_seconds": duration,
        "publish_date": published,
    }


def test_target_format_age_exclusion_and_midrank():
    target = video("target", 100, duration=300)
    baseline = [
        target,
        video("a", 100, duration=300),
        video("b", 100, duration=300),
        video("c", 100, duration=300),
        video("short", 100, duration=30),
        video("old", 100, duration=300, published="2020-01-01T00:00:00Z"),
    ]
    result = AnalyticsEstimateModule().detect_outlier(target, baseline, as_of=AS_OF)
    assert result["status"] == "ok"
    assert result["percentile_midrank"] == 50
    assert result["baseline_excluded"] == {"target": 1, "invalid": 0, "format": 1, "age_bucket": 1}
    assert result["metric"] == "custom_comparable_median_multiple_v1"


def test_three_x_threshold_and_future_unavailable():
    baseline = [video("a", 100), video("b", 100), video("c", 200)]
    result = AnalyticsEstimateModule().detect_outlier(video("target", 300), baseline, as_of=AS_OF)
    assert result["is_outlier"] is True
    future = video("future", 10, published="2027-01-01T00:00:00Z")
    assert (
        AnalyticsEstimateModule().detect_outlier(future, baseline, as_of=AS_OF)["reason"]
        == "future_publish_date"
    )
