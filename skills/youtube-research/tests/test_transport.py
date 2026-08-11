import json

import pytest
import requests

from scripts.innertube import InnerTubeClient


class FakeResponse:
    def __init__(self, status=200, payload=None, text=None, headers=None):
        self.status_code = status
        self.payload = payload
        self.text = text if text is not None else json.dumps(payload)
        self.headers = headers or {}

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def client(responses, delays=None, **kwargs):
    delay_log = delays if delays is not None else []
    return InnerTubeClient(
        session=Session(responses),
        sleep=delay_log.append,
        random_uniform=lambda _a, _b: 0,
        rate_limit_seconds=0,
        **kwargs,
    )


@pytest.mark.parametrize(
    ("exception", "code"),
    [
        (requests.Timeout("secret@example.com"), "timeout"),
        (requests.ConnectionError("https://host/?token=abc"), "connection_error"),
        (requests.RequestException("Bearer abc"), "request_error"),
    ],
)
def test_transport_exception_codes_and_redaction(exception, code):
    result = client([exception], max_retries=0).search("x")
    assert result["_status"] == code
    assert "secret@example.com" not in result["_message"]
    assert "token=abc" not in result["_message"]
    assert "Bearer abc" not in result["_message"]


def test_retry_after_and_payload_type():
    delays: list[float] = []
    instance = client(
        [
            FakeResponse(429, {}, headers={"Retry-After": "99"}),
            FakeResponse(200, {"ok": True}),
        ],
        delays=delays,
    )
    assert instance.search("x") == {"ok": True}
    assert delays == [30.0]

    result = client([FakeResponse(200, [])], max_retries=0).search("x")
    assert result["_status"] == "invalid_payload_type"


def test_no_retry_on_400_and_safe_json_error():
    response = FakeResponse(
        400,
        {
            "error": {
                "status": "INVALID_ARGUMENT",
                "message": "bad https://example/?key=secret",
                "errors": [{"reason": "badRequest"}],
            }
        },
    )
    instance = client([response])
    result = instance.search("x")
    assert len(instance.session.calls) == 1
    assert result["_status"] == "INVALID_ARGUMENT"
    assert result["_reason_codes"] == ["badRequest"]
    assert "secret" not in result["_message"]
