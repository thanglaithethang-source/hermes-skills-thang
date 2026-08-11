from scripts.enrichment import PublishDateEnricher, extract_player_publish_date
from tests.conftest import ScriptedClient


def test_player_date_extractor_and_batch_dedup(fixture_json):
    player = fixture_json("player_publish_date.json")
    parsed = extract_player_publish_date(player)
    assert parsed.value == "2026-07-20T00:00:00Z"
    rows = [
        {"videoId": "video000001", "published_raw": "2 weeks ago"},
        {"video_id": "video000001", "published_raw": "2 weeks ago"},
    ]
    client = ScriptedClient(player=[player])
    result = PublishDateEnricher(client).enrich(rows)
    assert result.status == "ok"
    assert len([call for call in client.calls if call[0] == "player"]) == 1
    assert all(row["publish_date"].endswith("Z") for row in result.items)
    assert all(row["published_raw"] == "2 weeks ago" for row in result.items)


def test_enrichment_failure_is_partial_and_cap(fixture_json):
    rows = [
        {"videoId": "video000001", "published_raw": "1 day ago"},
        {"videoId": "video000002", "published_raw": "2 weeks ago"},
    ]
    client = ScriptedClient(
        player=[
            fixture_json("player_publish_date.json"),
            fixture_json("player_publish_date_error.json"),
        ]
    )
    result = PublishDateEnricher(client).enrich(rows)
    assert result.status == "partial"
    assert result.items[1]["publish_date"] is None
    assert result.items[1]["published_raw"] == "2 weeks ago"
    assert result.metadata["enrichment_failures"][0]["video_id"] == "video000002"

    cap_rows = [{"videoId": f"video{i:06d}"} for i in range(101)]
    dates = [fixture_json("player_publish_date.json") for _ in range(100)]
    capped = PublishDateEnricher(ScriptedClient(player=dates)).enrich(cap_rows)
    assert capped.metadata["enrichment_failures"][-1]["error_code"] == "enrichment_cap"
