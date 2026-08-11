from scripts.innertube import InnerTubeClient
from tests.test_transport import FakeResponse, Session


def test_autocomplete_query_is_request_parameter():
    session = Session([FakeResponse(200, text='["a", [["one"], ["two"]]]')])
    client = InnerTubeClient(session=session, sleep=lambda _: None, rate_limit_seconds=0)
    assert client.complete("a & b # tiếng Việt") == ["one", "two"]
    params = session.calls[0][1]["params"]
    assert params["q"] == "a & b # tiếng Việt"


def test_exact_jsonp_and_invalid_wrapper():
    good = Session([FakeResponse(200, text=' window.google.ac.h(["a", [["one"]]]); ')])
    client = InnerTubeClient(session=good, rate_limit_seconds=0)
    assert client.complete("a") == ["one"]
    bad = InnerTubeClient(
        session=Session([FakeResponse(200, text='callback(["a", []]);')]),
        rate_limit_seconds=0,
    ).complete("a")
    assert bad["_status"] == "invalid_jsonp"
