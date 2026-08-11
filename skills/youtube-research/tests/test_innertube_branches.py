import json

import pytest
import requests

from scripts.exceptions import AuthUnavailableError
from scripts.innertube import InnerTubeClient
from tests.test_transport import FakeResponse, Session


def test_context_validation_and_downgrade(tmp_path):
    malformed = tmp_path / "bad.json"
    malformed.write_text("[]", encoding="utf-8")
    with pytest.raises(AuthUnavailableError):
        InnerTubeClient(str(malformed), authenticated=True)
    client = InnerTubeClient(str(malformed), authenticated=True, strict_auth=False)
    assert client.auth_status == "downgraded"

    missing_cookie = tmp_path / "missing-cookie.json"
    missing_cookie.write_text(
        json.dumps(
            {
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": "1",
                        "hl": "en",
                        "gl": "VN",
                    }
                },
                "cookies": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(AuthUnavailableError):
        InnerTubeClient(str(missing_cookie), authenticated=True)


def test_get_and_endpoint_wrapper_branches():
    timeout = InnerTubeClient(
        session=Session([requests.Timeout("late")]), rate_limit_seconds=0
    )._get("https://example.invalid")
    assert timeout["_status"] == "timeout"
    bad = InnerTubeClient(
        session=Session([FakeResponse(500, text="bad")]), rate_limit_seconds=0
    )._get("https://example.invalid")
    assert bad["_status"] == 500

    session = Session(
        [
            FakeResponse(200, {}),
            FakeResponse(200, {}),
            FakeResponse(200, {}),
            FakeResponse(200, {}),
        ]
    )
    client = InnerTubeClient(session=session, max_retries=0, rate_limit_seconds=0)
    client.search("q", params="p", continuation="c")
    client.browse("browse", params="p", continuation="c")
    client.next("video000001", continuation="c")
    client.player("video000001")
    bodies = [call[1]["json"] for call in session.calls]
    assert bodies[0]["query"] == "q"
    assert bodies[1]["browseId"] == "browse"
    assert bodies[2]["videoId"] == "video000001"
    assert bodies[3]["videoId"] == "video000001"
