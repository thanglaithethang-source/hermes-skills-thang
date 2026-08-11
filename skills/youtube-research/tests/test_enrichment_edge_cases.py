from scripts.enrichment import PublishDateEnricher, extract_player_publish_date
from tests.conftest import ScriptedClient


def test_publish_date_extractor_edge_cases():
    instant = extract_player_publish_date(
        {"microformat": {"playerMicroformatRenderer": {"uploadDate": "2026-07-20T12:00:00+02:00"}}}
    )
    assert instant.value == "2026-07-20T10:00:00Z"
    assert extract_player_publish_date([]).status == "invalid"
    assert extract_player_publish_date({"videoDetails": {"publishDate": 123}}).status == "invalid"
    assert (
        extract_player_publish_date({"videoDetails": {"publishDate": "2 weeks ago"}}).status
        == "invalid"
    )
    assert (
        extract_player_publish_date({"videoDetails": {"publishDate": "2026-07-20T12:00:00"}}).status
        == "invalid"
    )
    assert extract_player_publish_date({}).status == "missing"


def test_enricher_invalid_rows_skips_and_unplayable():
    enricher = PublishDateEnricher(ScriptedClient())
    assert enricher.enrich("bad").status == "error"
    assert enricher.enrich([], max_items=0).status == "error"
    assert enricher.enrich([]).status == "empty"
    assert enricher.enrich([1]).status == "error"
    skipped = enricher.enrich([{"title": "no id"}])
    assert skipped.status == "partial"
    assert skipped.metadata["enrichment_skipped"] == 1
    unplayable = PublishDateEnricher(
        ScriptedClient(
            player=[{"playabilityStatus": {"status": "LOGIN_REQUIRED", "reason": "Login"}}]
        )
    ).enrich([{"videoId": "video000001"}])
    assert unplayable.status == "partial"
