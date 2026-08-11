import re
from pathlib import Path

from scripts.analytics_estimate import estimate_ctr, estimate_retention, estimate_rpm
from scripts.client_profile import KNOWN_GOOD_PROFILE
from scripts.models import CanonicalVideo
from scripts.result import Result

ROOT = Path(__file__).parents[1]


def test_skill_frontmatter_and_documented_files():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = skill.split("---", 2)[1]
    keys = {
        line.split(":", 1)[0]
        for line in frontmatter.splitlines()
        if line and not line.startswith(" ")
    }
    assert keys == {"name", "description"}
    assert "C:\\" not in skill
    assert "returns raw JSON" not in skill

    tree = re.search(r"```text\n(.*?)\n```", skill, re.DOTALL)
    assert tree
    entries = []
    for line in tree.group(1).splitlines()[1:]:
        leaf = re.sub(r"^[│ ]*[├└]── ", "", line)
        if leaf.endswith("/") or not leaf:
            continue
        entries.append(leaf)
    for filename in entries:
        matches = list(ROOT.rglob(filename))
        assert matches, f"Documented architecture entry does not exist: {filename}"


def test_documented_result_and_canonical_video_contract():
    result = Result.collection(items=[{"video_id": "dQw4w9WgXcQ"}], requested=1)
    assert result.status == "ok"
    assert result.items[0]["video_id"] == "dQw4w9WgXcQ"

    video = CanonicalVideo(
        video_id="dQw4w9WgXcQ",
        channel_id=None,
        title="Example",
        view_count=10,
        duration_seconds=181,
        publish_date="2024-01-02",
        published_raw="2 years ago",
        duration_raw="3:01",
    ).to_dict()
    assert video["video_id"] == video["videoId"]
    assert video["publish_date"] == "2024-01-02"
    assert video["published_raw"] == "2 years ago"


def test_documented_owner_only_and_scenario_shapes():
    assert estimate_ctr({})["estimable"] is False
    assert estimate_retention({})["estimable"] is False
    unavailable = estimate_rpm({})
    assert unavailable["estimable"] is False
    assert unavailable["scenario"] is None

    selected = estimate_rpm({}, scenario_profile="general_user_assumption")
    assert selected["estimable"] is False
    assert selected["scenario"]["source_type"] == "user_assumption"


def test_endpoint_reference_matches_runtime_profile():
    reference = (ROOT / "references" / "innertube_endpoints.md").read_text(encoding="utf-8")
    assert KNOWN_GOOD_PROFILE.profile_id in reference
    assert KNOWN_GOOD_PROFILE.context.client_version in reference
    for value in KNOWN_GOOD_PROFILE.search_sort_params.values():
        assert value in reference
        assert "%" not in value
    assert KNOWN_GOOD_PROFILE.channel_videos_params in reference


def test_reference_claims_and_requirements_are_consistent():
    rpm = (ROOT / "references" / "niche_rpm_table.md").read_text(encoding="utf-8")
    assert "industry average" in rpm
    assert "does not estimate RPM" in rpm
    assert "user_assumption" in rpm

    calibration = " ".join(
        (ROOT / "references" / "keyword_competition_calibration.md")
        .read_text(encoding="utf-8")
        .split()
    )
    assert "at least 200 training queries" in calibration
    assert "strictly increasing thresholds" in calibration
    assert "explicit test mode" in calibration

    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert re.search(r"^requests\b", requirements, re.MULTILINE)
    assert re.search(r"^jsonschema\b", requirements, re.MULTILINE)
