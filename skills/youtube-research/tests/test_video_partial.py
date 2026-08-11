from scripts.video import VideoModule
from tests.conftest import ScriptedClient


def test_next_failure_is_partial(fixture_json):
    client = ScriptedClient(
        player=[fixture_json("video_info_success.json")],
        next_=[fixture_json("next_error.json")],
    )
    result = VideoModule(client).video_info("video000001")
    assert result.status == "partial" and len(result.items) == 1
    assert result.items[0]["like_count"] is None
    assert result.metadata["enrichment_failures"][0]["endpoint"] == "next"


def test_unplayable_player_is_error(fixture_json):
    result = VideoModule(
        ScriptedClient(player=[fixture_json("player_unplayable.json")])
    ).video_info("video000001")
    assert result.status == "error"
    assert result.error_code == "playability_unplayable"


def test_hidden_engagement_is_observable_absence(fixture_json):
    result = VideoModule(
        ScriptedClient(
            player=[fixture_json("video_info_success.json")],
            next_=[{}],
        )
    ).video_info("video000001")
    assert result.status == "ok"
    assert result.metadata["engagement_visibility"] == {"likes": "absent", "comments": "absent"}
