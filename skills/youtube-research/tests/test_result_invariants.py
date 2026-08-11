import pytest

from scripts.result import Result


@pytest.mark.parametrize(
    "kwargs",
    [
        {"status": "ok", "items": []},
        {"status": "empty", "items": [1]},
        {"status": "partial", "items": [1]},
        {"status": "error", "items": [1], "reason": "bad"},
        {"status": "unsupported", "reason": ""},
    ],
)
def test_status_invariants(kwargs):
    with pytest.raises(ValueError):
        Result(**kwargs)


def test_collection_counts_and_defensive_copies():
    source = [1, 2, 3]
    metadata = {"value": 1}
    result = Result(status="ok", items=source, metadata=metadata)
    source.append(4)
    metadata["value"] = 2
    assert result.items == [1, 2, 3]
    assert result.metadata == {"value": 1}
    sliced = Result.collection(items=[1, 2], requested=1)
    assert sliced.items == [1]
    assert sliced.truncated is True
    with pytest.raises(ValueError):
        Result.collection(items=[], requested=1, pages_requested=0, pages_succeeded=1)
    with pytest.raises(TypeError):
        Result.collection(items="bad", requested=1)
