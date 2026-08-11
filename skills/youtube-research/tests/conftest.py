import json
from copy import deepcopy
from pathlib import Path

import pytest


class ScriptedClient:
    """Test client that returns scripted responses without network access."""

    def __init__(self, *, search=None, browse=None, next_=None, player=None):
        self.responses = {
            "search": list(search or []),
            "browse": list(browse or []),
            "next": list(next_ or []),
            "player": list(player or []),
        }
        self.calls = []

    def _pop(self, endpoint, **kwargs):
        self.calls.append((endpoint, kwargs))
        if not self.responses[endpoint]:
            return {
                "_error": True,
                "_status": "no_more_responses",
                "_message": "No more scripted responses",
            }
        return deepcopy(self.responses[endpoint].pop(0))

    def search(self, query=None, params=None, continuation=None):
        return self._pop("search", query=query, params=params, continuation=continuation)

    def browse(self, browse_id=None, params=None, continuation=None):
        return self._pop("browse", browse_id=browse_id, params=params, continuation=continuation)

    def next(self, video_id=None, continuation=None):
        return self._pop("next", video_id=video_id, continuation=continuation)

    def player(self, video_id):
        endpoint = "player" if self.responses["player"] else "next"
        return self._pop(endpoint, video_id=video_id)

    def complete(self, q):
        return []

    def get_trending(self, region="VN"):
        return {"_error": True, "_status": 400, "_message": "unsupported"}

    def _get(self, url):
        return None


@pytest.fixture
def fixture_json():
    root = Path(__file__).parent / "fixtures"

    def load(name):
        return json.loads((root / name).read_text(encoding="utf-8"))

    return load
