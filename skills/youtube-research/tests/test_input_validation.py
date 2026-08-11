import pytest

from scripts.search import SearchModule
from scripts.validation import (
    ValidationError,
    validate_channel_id,
    validate_id_batch,
    validate_int_range,
    validate_query,
    validate_video_id,
)
from scripts.video import VideoModule
from tests.conftest import ScriptedClient


@pytest.mark.parametrize("value", [None, "", " ", "x" * 201])
def test_invalid_queries(value):
    with pytest.raises(ValidationError):
        validate_query(value)
    result = SearchModule(ScriptedClient()).search(value)
    assert result.error_code == "invalid_input"


@pytest.mark.parametrize("value", [None, "", True, "short", "a" * 12])
def test_invalid_video_ids(value):
    with pytest.raises(ValidationError):
        validate_video_id(value)
    assert VideoModule(ScriptedClient()).video_info(value).error_code == "invalid_input"


def test_batch_and_integer_boundaries():
    with pytest.raises(ValidationError):
        validate_id_batch("video000001")
    with pytest.raises(ValidationError):
        validate_id_batch(["video000001", "video000001"])
    with pytest.raises(ValidationError):
        validate_int_range(True, "limit", 1, 100)
    assert validate_channel_id("UC12345678901234567890")
