import tarfile
import zipfile
from pathlib import Path

FORBIDDEN = {
    "SESSION_HANDOFF.md",
    "IMPLEMENTATION_PLAN_V8.md",
    "REVIEW_CODEX_V8.md",
    ".pytest_cache",
    "__pycache__",
    "yt_context.json",
    "cookies.json",
}


def test_wheel_and_sdist_exclude_internal_material():
    dist = Path(__file__).parents[1] / "dist"
    wheels = list(dist.glob("*.whl"))
    sdists = list(dist.glob("*.tar.gz"))
    assert wheels and sdists
    with zipfile.ZipFile(wheels[-1]) as archive:
        wheel_names = archive.namelist()
        metadata_name = next(name for name in wheel_names if name.endswith(".dist-info/METADATA"))
        metadata = archive.read(metadata_name).decode("utf-8")
    with tarfile.open(sdists[-1]) as archive:
        sdist_names = archive.getnames()
    for name in [*wheel_names, *sdist_names]:
        assert not any(forbidden in name for forbidden in FORBIDDEN)
        assert not name.endswith(".db")
    assert any(name.endswith("rpm_scenarios.json") for name in wheel_names)
    assert any(name.endswith("keyword_competition_calibration.md") for name in wheel_names)
    assert "Requires-Dist: requests" in metadata
    assert "Requires-Dist: jsonschema" in metadata
