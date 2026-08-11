from datetime import UTC, datetime

from scripts.analytics_estimate import AnalyticsEstimateModule, detect_niche


def test_naive_as_of_and_optional_tags():
    module = AnalyticsEstimateModule()
    result = module.detect_outlier({}, [], as_of=datetime(2026, 1, 1))
    assert result["reason"] == "naive_as_of"
    assert detect_niche({"title": "AI", "tags": None}) == "ai"
    signals = module.keyword_competition_signals(
        "tiếng Việt", [], as_of=datetime(2026, 1, 1, tzinfo=UTC)
    )
    assert signals["competition_score"] is None
