from copy import deepcopy
from pathlib import Path

from scripts.calibration import CalibrationRepository


def valid_artifact():
    return {
        "version": "test-1.0.0",
        "training_query_count": 200,
        "required_features": ["relevance_median"],
        "coefficients": {"relevance_median": 1.0},
        "intercept": 0.0,
        "feature_transforms": {"relevance_median": "identity"},
        "thresholds": [[40, "low"], [70, "medium"], [100, "high"]],
        "provenance": {
            "dataset_id": "fixture",
            "dataset_sha256": "a" * 64,
            "created_at": "2026-07-27T00:00:00Z",
            "methodology": "fixture",
            "label_definition": "fixture",
            "holdout_query_count": 50,
            "holdout_metrics": {"mae": 1.0, "spearman_r": 0.9},
        },
    }


def repository(allow=True):
    return CalibrationRepository(
        Path(__file__).parents[1] / "references" / "keyword_competition_calibration.schema.json",
        allow_test_artifacts=allow,
    )


def test_valid_artifact_and_test_mode_gate():
    assert repository().validate(valid_artifact())
    production = repository(False)
    assert not production.validate(valid_artifact())
    assert production.errors[0]["path"] == "$.version"


def test_training_threshold_and_provenance_semantics():
    artifact = valid_artifact()
    artifact["training_query_count"] = 199
    repo = repository()
    assert not repo.validate(artifact)
    assert any(error["validator"] == "minimum" for error in repo.errors)

    artifact = valid_artifact()
    artifact["thresholds"] = [[70, "high"], [40, "low"], [100, "end"]]
    assert not repo.validate(artifact)
    assert any("strictly increasing" in error["message"] for error in repo.errors)

    artifact = deepcopy(valid_artifact())
    del artifact["provenance"]["dataset_id"]
    assert not repo.validate(artifact)
    assert any("dataset_id" in error["message"] for error in repo.errors)
