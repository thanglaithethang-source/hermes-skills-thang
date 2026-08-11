from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts.analytics_estimate import (
    AnalyticsEstimateModule,
    _normalized_hhi,
    _title_relevance,
    _video_observation,
    detect_niche,
    estimate_ctr,
    estimate_retention,
    estimate_rpm,
)
from scripts.calibration import CalibrationRepository
from scripts.storage import Storage


def test_public_proxy_branches():
    video = {
        "title": "WHY 10 AI TOOLS?",
        "view_count": 100,
        "like_count": 10,
        "comment_count": 5,
        "duration_seconds": 700,
        "tags": ["software"],
    }
    ctr = estimate_ctr(video, search_position=1)
    assert ctr["observable_proxies"]["like_view_ratio"] == 0.1
    assert ctr["observable_proxies"]["title_features"]["has_number"] is True
    retention = estimate_retention(video)
    assert retention["observable_proxies"]["comment_view_ratio"] == 0.05
    assert detect_niche(video) in {"ai", "software"}
    rpm = estimate_rpm(video, scenario_override=[2, 4])
    assert rpm["scenario"]["source_type"] == "user_override"
    with pytest.raises(ValueError):
        estimate_rpm(video, scenario_override=[4, 2])
    with pytest.raises(ValueError):
        estimate_rpm(video, scenario_profile="missing")


def test_vph_unavailable_window_and_invalid_inputs(tmp_path):
    module = AnalyticsEstimateModule()
    assert module.calculate_vph("video000001")["status"] == "unavailable"
    storage = Storage(str(tmp_path / "analytics.db"))
    module = AnalyticsEstimateModule(storage=storage)
    with pytest.raises(ValueError):
        module.calculate_vph("video000001", window_hours=0)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    storage.clock = lambda: now
    storage.snapshot_video("video000001", view_count=1)
    assert module.calculate_vph("video000001")["status"] == "unavailable"


def test_observation_relevance_hhi_and_module_wrappers():
    now = datetime(2026, 1, 2, tzinfo=UTC)
    assert _video_observation([], now)[1] == "invalid_video"
    assert (
        _video_observation(
            {
                "views": True,
                "duration_seconds": 1,
                "publish_date": "2026-01-01T00:00:00Z",
            },
            now,
        )[1]
        == "invalid_views"
    )
    assert (
        _video_observation(
            {
                "views": 1,
                "duration_seconds": 0,
                "publish_date": "2026-01-01T00:00:00Z",
            },
            now,
        )[1]
        == "missing_duration"
    )
    assert (
        _video_observation(
            {
                "views": 1,
                "duration_seconds": 1,
                "publish_date": "bad",
            },
            now,
        )[1]
        == "invalid_publish_date"
    )
    assert _title_relevance("", "title") is None
    assert _normalized_hhi(["one"]) is None
    assert _normalized_hhi(["one", "one"]) == 1

    module = AnalyticsEstimateModule()
    video = {"title": "AI", "duration_seconds": 100}
    assert module.estimate_ctr(video)["estimable"] is False
    assert module.estimate_retention(video)["estimable"] is False
    assert module.estimate_rpm(video)["estimable"] is False
    assert module.detect_niche(video) == "ai"


def test_keyword_exclusions_log_transform_and_demand():
    now = datetime(2026, 7, 27, tzinfo=UTC)
    rows = [
        {"videoId": "missing", "views": 1, "duration_seconds": 30},
        {
            "videoId": "invalid",
            "channelId": "channel",
            "views": 1,
            "duration_seconds": 30,
            "publish_date": "bad",
        },
        {
            "videoId": "valid",
            "channelId": "channel",
            "title": "AI",
            "views": 100,
            "duration_seconds": 30,
            "publish_date": "2026-07-20T00:00:00Z",
        },
    ]
    artifact = {
        "version": "test-1.0.0",
        "training_query_count": 200,
        "required_features": ["median_views_per_day_short"],
        "coefficients": {"median_views_per_day_short": 0.01},
        "intercept": 0,
        "feature_transforms": {"median_views_per_day_short": "log1p"},
        "thresholds": [[100, "level"]],
        "provenance": {
            "dataset_id": "x",
            "dataset_sha256": "a" * 64,
            "created_at": "2026-01-01T00:00:00Z",
            "methodology": "test",
            "label_definition": "test",
            "holdout_query_count": 50,
            "holdout_metrics": {"mae": 1, "spearman_r": 0.5},
        },
    }
    repository = CalibrationRepository(
        Path(__file__).parents[1] / "references" / "keyword_competition_calibration.schema.json",
        allow_test_artifacts=True,
    )
    assert repository.validate(artifact)
    module = AnalyticsEstimateModule()
    result = module.keyword_competition_signals(
        "AI", rows, calibration=repository, demand={"score": "bad"}, as_of=now
    )
    assert result["calibration_status"] == "calibrated"
    assert result["demand_diagnostic"] == "invalid_demand"
    assert result["excluded"] == {"missing_channel_id": 1, "invalid_views_or_age": 1}
    deprecated = module.keyword_competition_score("AI", rows, as_of=now)
    assert "deprecated_api" in deprecated
