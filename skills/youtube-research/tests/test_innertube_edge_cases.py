from copy import deepcopy

import pytest

from scripts.innertube import InnerTubeClient
from tests.test_transport import FakeResponse, Session


def bare_client():
    return InnerTubeClient(rate_limit_seconds=0)


@pytest.mark.parametrize(
    "saved",
    [
        [],
        {},
        {"context": {"client": {}}},
        {
            "context": {
                "client": {
                    "clientName": "x" * 41,
                    "clientVersion": "1",
                    "hl": "en",
                    "gl": "VN",
                }
            }
        },
        {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "1",
                    "hl": "en",
                    "gl": "VN",
                }
            },
            "api_key": "",
        },
        {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "1",
                    "hl": "en",
                    "gl": "VN",
                }
            },
            "cookies": [],
        },
    ],
)
def test_saved_context_validation_errors(saved):
    with pytest.raises(ValueError):
        bare_client()._validated_saved(saved)


def test_retry_after_invalid_json_rate_limit_and_complete_errors():
    client = bare_client()
    assert client._retry_after(FakeResponse(headers={})) is None
    assert client._retry_after(FakeResponse(headers={"Retry-After": "invalid"})) is None
    invalid_json = InnerTubeClient(
        session=Session([FakeResponse(200, ValueError("bad"), text="bad")]),
        rate_limit_seconds=0,
        max_retries=0,
    ).search("q")
    assert invalid_json["_status"] == "invalid_json"
    delays = []
    rate_limited = InnerTubeClient(
        session=Session([FakeResponse(200, {})]),
        sleep=delays.append,
        rate_limit_seconds=0.25,
        max_retries=0,
    )
    assert rate_limited.search("q") == {}
    assert delays == [0.25]
    assert bare_client().complete("")["_status"] == "invalid_input"
    transport = bare_client()
    transport._get = lambda *_a, **_k: {"_error": True, "_status": "timeout", "_message": "late"}
    assert transport.complete("q")["_status"] == "timeout"


def test_headers_without_cookie_and_refresh_rollback(monkeypatch):
    client = bare_client()
    client.authenticated = True
    client.cookies = {}
    assert "Authorization" not in client._build_headers()
    previous = deepcopy(client.context)
    monkeypatch.setattr(
        client,
        "_load_context",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("bad")),
    )
    with pytest.raises(ValueError):
        client.refresh_context()
    assert client.context == previous
