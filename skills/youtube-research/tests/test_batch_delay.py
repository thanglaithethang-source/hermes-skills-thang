from scripts.video import VideoModule
from tests.conftest import ScriptedClient


def test_video_batch_uses_injected_sleeper(fixture_json):
    delays = []
    client = ScriptedClient(
        player=[
            fixture_json("video_info_success.json"),
            fixture_json("video_info_success.json"),
        ],
        next_=[{}, {}],
    )
    client.sleep = delays.append
    result = VideoModule(client).video_batch(["video000001", "video000002"], delay=0.25)
    assert result.status == "ok"
    assert delays == [0.25]
