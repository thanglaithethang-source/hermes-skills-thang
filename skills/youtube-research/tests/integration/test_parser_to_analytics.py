from datetime import UTC, datetime

from scripts.analytics_estimate import AnalyticsEstimateModule
from scripts.enrichment import PublishDateEnricher
from scripts.parsers import parse_video_page
from tests.conftest import ScriptedClient


def test_parser_enrichment_keyword_pipeline(fixture_json):
    parsed = parse_video_page(fixture_json("search_initial.json"), surface="search")
    player = {
        "playabilityStatus": {"status": "OK"},
        "microformat": {"playerMicroformatRenderer": {"publishDate": "2026-07-20"}},
    }
    enriched = PublishDateEnricher(ScriptedClient(player=[player])).enrich(parsed.items)
    signals = AnalyticsEstimateModule().keyword_competition_signals(
        "AI",
        enriched.items,
        as_of=datetime(2026, 7, 27, tzinfo=UTC),
    )
    assert signals["features"]["eligible_sample_size"] == 1
    assert signals["features"]["median_views_per_day_short"] is not None
