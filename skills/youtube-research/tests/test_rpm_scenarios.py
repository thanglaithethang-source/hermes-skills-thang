from scripts.analytics_estimate import estimate_rpm


def test_rpm_is_explicit_scenario_not_estimate():
    unavailable = estimate_rpm({"duration_seconds": 120})
    assert unavailable["estimable"] is False
    assert unavailable["scenario"] is None
    selected = estimate_rpm(
        {"duration_seconds": 120},
        scenario_profile="general_user_assumption",
    )
    assert selected["profile_version"] == "1.0.0"
    assert selected["scenario"]["source_type"] == "user_assumption"
    assert "format" not in selected
