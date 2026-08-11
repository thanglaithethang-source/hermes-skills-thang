import pytest

from scripts.report_status import Dependency, reduce_dependencies
from scripts.result import Result


@pytest.mark.parametrize(
    ("dependency", "output", "expected"),
    [
        (Result.error("bad"), [], "error"),
        (Result.unsupported("drift"), [], "unsupported"),
        (Result(status="empty", reason="none"), [], "empty"),
        (Result(status="partial", items=[1], reason="degraded"), [1], "partial"),
        (Result.error("optional"), [1], "partial"),
        (Result(status="ok", items=[1]), [1], "ok"),
    ],
)
def test_dependency_reducer(dependency, output, expected):
    status, reason, metadata = reduce_dependencies([Dependency("source", dependency, True)], output)
    assert status == expected
    assert metadata["dependencies"]["source"]["status"] == dependency.status
    if expected == "partial":
        assert "source" in reason
