from datetime import UTC, datetime

from scripts.analytics_estimate import AnalyticsEstimateModule

AS_OF = datetime(2026, 7, 27, tzinfo=UTC)


def row(index, views=100, duration=300, channel_id=None, title="AI tools"):
    return {
        "videoId": str(index),
        "channelId": channel_id or f"UC{index}",
        "channel": "same display name",
        "title": title,
        "views": views,
        "duration_seconds": duration,
        "publish_date": "2026-07-20T00:00:00Z",
    }


def test_uncalibrated_signals_no_fake_score_and_stable_ids():
    rows = [row(index, views=1_000_000) for index in range(10)]
    result = AnalyticsEstimateModule().keyword_competition_signals("AI tools", rows, as_of=AS_OF)
    assert result["competition_score"] is None
    assert result["competition_level"] is None
    assert result["features"]["channel_concentration_hhi"] == 0
    assert "unique_channels" not in result["features"]


def test_relevance_format_median_and_calibration_gate():
    rows = [
        row(1, 100, 30, title="AI tools"),
        row(2, 1000, 30, title="unrelated"),
        row(3, 200, 300, title="AI guide"),
    ]
    module = AnalyticsEstimateModule()
    first = module.keyword_competition_signals("AI tools", rows, as_of=AS_OF)
    second = module.keyword_competition_signals("cooking", rows, as_of=AS_OF)
    assert first["features"]["relevance_median"] != second["features"]["relevance_median"]
    assert first["features"]["median_views_per_day_short"] is not None
    assert first["features"]["median_views_per_day_long_form"] is not None
    assert (
        module.keyword_competition_signals("AI", rows, calibration={}, as_of=AS_OF)["reason"]
        == "Invalid calibration schema"
    )


def test_deterministic_test_calibration():
    rows = [row(1), row(2, duration=30)]
    calibration = {
        "version": "test-1.0.0",
        "training_query_count": 200,
        "required_features": ["relevance_median"],
        "coefficients": {"relevance_median": 1.0},
        "intercept": 0.0,
        "feature_transforms": {"relevance_median": "identity"},
        "thresholds": [[40, "low"], [70, "medium"], [100, "high"]],
        "provenance": {
            "dataset_id": "unit-test",
            "dataset_sha256": "a" * 64,
            "created_at": "2026-07-27T00:00:00Z",
            "methodology": "deterministic fixture",
            "label_definition": "fixture labels",
            "holdout_query_count": 50,
            "holdout_metrics": {"mae": 1.0, "spearman_r": 0.9},
        },
    }
    from pathlib import Path

    from scripts.calibration import CalibrationRepository

    repository = CalibrationRepository(
        Path(__file__).parents[1] / "references" / "keyword_competition_calibration.schema.json",
        allow_test_artifacts=True,
    )
    assert repository.validate(calibration)
    result = AnalyticsEstimateModule().keyword_competition_signals(
        "AI",
        rows,
        calibration=repository,
        demand={"score": 50},
        as_of=AS_OF,
    )
    assert result["calibration_status"] == "calibrated"
    assert result["competition_score"] == 73
    assert result["opportunity_score"] is not None
