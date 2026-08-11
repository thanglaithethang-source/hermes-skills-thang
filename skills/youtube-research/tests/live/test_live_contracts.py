import os

import pytest

from scripts.youtube_research import YouTubeResearch

pytestmark = pytest.mark.live


@pytest.mark.skipif(
    os.environ.get("YT_LIVE_TESTS") != "1",
    reason="Set YT_LIVE_TESTS=1 to run live contract tests",
)
def test_live_search_contract():
    result = YouTubeResearch().search("OpenAI", limit=1)
    assert result.status in {"ok", "empty", "partial", "error", "unsupported"}
    assert isinstance(result.metadata, dict)
