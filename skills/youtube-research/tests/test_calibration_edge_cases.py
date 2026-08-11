import json
from pathlib import Path

from scripts.calibration import CalibrationRepository
from tests.test_calibration_validation import valid_artifact


def schema_path():
    return Path(__file__).parents[1] / "references" / "keyword_competition_calibration.schema.json"


def test_artifact_file_loading_and_json_rejections(tmp_path):
    valid = tmp_path / "valid.json"
    valid.write_text(json.dumps(valid_artifact()), encoding="utf-8")
    assert CalibrationRepository(schema_path(), valid, allow_test_artifacts=True).valid
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"version":"a","version":"b"}', encoding="utf-8")
    repository = CalibrationRepository(schema_path(), duplicate)
    assert repository.errors[0]["validator"] == "json"
    too_large = tmp_path / "large.json"
    too_large.write_text(" " * (1024 * 1024 + 1), encoding="utf-8")
    assert CalibrationRepository(schema_path(), too_large).valid is False


def test_semantic_feature_numeric_and_threshold_rejections():
    repository = CalibrationRepository(schema_path(), allow_test_artifacts=True)
    artifact = valid_artifact()
    artifact["required_features"] = ["unsupported"]
    artifact["coefficients"] = {"unsupported": 1}
    artifact["feature_transforms"] = {"unsupported": "identity"}
    assert not repository.validate(artifact)
    assert any("unsupported" in error["message"] for error in repository.errors)
    artifact = valid_artifact()
    artifact["thresholds"] = [[40, "same"], [70, "same"], [90, "end"]]
    assert not repository.validate(artifact)
    messages = " ".join(error["message"] for error in repository.errors)
    assert "unique" in messages and "100" in messages
    artifact = valid_artifact()
    artifact["coefficients"] = {}
    assert not repository.validate(artifact)
