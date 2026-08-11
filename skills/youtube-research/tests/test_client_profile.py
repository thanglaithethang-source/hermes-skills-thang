from copy import deepcopy

from scripts.client_profile import KNOWN_GOOD_PROFILE
from scripts.innertube import InnerTubeClient
from tests.test_transport import FakeResponse, Session


def test_context_independent_and_trending_region():
    session = Session([FakeResponse(200, {}), FakeResponse(200, {})])
    client = InnerTubeClient(session=session, rate_limit_seconds=0, max_retries=0)
    original = deepcopy(client.context)
    client.get_trending("VN")
    client.get_trending("US")
    assert session.calls[0][1]["json"]["context"]["client"]["gl"] == "VN"
    assert session.calls[1][1]["json"]["context"]["client"]["gl"] == "US"
    assert client.context == original
    assert KNOWN_GOOD_PROFILE.profile_id
