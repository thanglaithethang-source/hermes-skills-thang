from scripts.channel import ChannelModule
from tests.conftest import ScriptedClient

VALID_CHANNEL = "UC12345678901234567890"


class HandleClient(ScriptedClient):
    def __init__(self, html, browse):
        super().__init__(browse=browse)
        self.html = html

    def _get(self, _url):
        return {"text": self.html}


def test_handle_resolves_and_missing_handle_errors(fixture_json):
    payload = fixture_json("channel_info_success.json")
    payload["metadata"]["channelMetadataRenderer"]["externalId"] = VALID_CHANNEL
    resolved = ChannelModule(
        HandleClient(f'"channelId":"{VALID_CHANNEL}"', [payload])
    ).channel_info("@valid_name")
    assert resolved.status == "ok"
    missing = ChannelModule(HandleClient("no channel", [])).channel_info("@valid_name")
    assert missing.status == "error"


def test_handle_get_and_browse_errors():
    client = HandleClient("", [])
    client._get = lambda _url: {"_error": True, "_status": 500, "_message": "bad"}
    assert ChannelModule(client).channel_info("@valid_name").status == "error"
    client = HandleClient(
        f'"channelId":"{VALID_CHANNEL}"', [{"_error": True, "_status": 500, "_message": "bad"}]
    )
    assert ChannelModule(client).channel_info("@valid_name").status == "error"
