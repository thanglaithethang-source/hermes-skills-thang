"""JSON Schema and semantic validation for competition calibration artifacts."""

from __future__ import annotations

import itertools
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

MAX_ARTIFACT_BYTES = 1024 * 1024
SUPPORTED_FEATURES = {
    "sample_size",
    "eligible_sample_size",
    "relevance_median",
    "channel_concentration_hhi",
    "median_views_per_day_short",
    "median_views_per_day_long_form",
}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    if path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError("JSON artifact exceeds 1 MiB")
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON number: {value}")
        ),
    )


def _json_path(parts: Any) -> str:
    value = "$"
    for part in parts:
        value += f"[{part}]" if isinstance(part, int) else f".{part}"
    return value


class CalibrationRepository:
    supported_major = 1

    def __init__(
        self,
        schema_path: str | Path,
        artifact_path: str | Path | None = None,
        allow_test_artifacts: bool = False,
    ):
        self.schema_path = Path(schema_path)
        self.allow_test_artifacts = allow_test_artifacts
        self.schema = _load_json(self.schema_path)
        Draft202012Validator.check_schema(self.schema)
        self.validator = Draft202012Validator(self.schema, format_checker=FormatChecker())
        self.artifact: Mapping[str, Any] | None = None
        self.errors: list[dict[str, str]] = []
        if artifact_path is not None:
            try:
                artifact = _load_json(Path(artifact_path))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                self.errors = [{"path": "$", "validator": "json", "message": str(exc)[:200]}]
            else:
                self.validate(artifact)

    @property
    def valid(self) -> bool:
        return self.artifact is not None and not self.errors

    def validate(self, artifact: Any) -> bool:
        self.artifact = None
        self.errors = []
        if not isinstance(artifact, Mapping):
            self.errors.append(
                {"path": "$", "validator": "type", "message": "artifact must be an object"}
            )
            return False
        schema_errors = sorted(
            self.validator.iter_errors(artifact),
            key=lambda error: list(error.absolute_path),
        )
        self.errors.extend(
            {
                "path": _json_path(error.absolute_path),
                "validator": str(error.validator),
                "message": error.message[:200],
            }
            for error in schema_errors
        )
        if self.errors:
            return False
        required = artifact["required_features"]
        coefficients = artifact["coefficients"]
        transforms = artifact["feature_transforms"]
        if set(coefficients) != set(required) or set(transforms) != set(required):
            self._semantic("$.required_features", "feature keys must match exactly")
        unsupported = sorted(set(required) - SUPPORTED_FEATURES)
        if unsupported:
            self._semantic("$.required_features", "unsupported runtime feature")
        thresholds = artifact["thresholds"]
        bounds = [entry[0] for entry in thresholds]
        labels = [entry[1] for entry in thresholds]
        if any(left >= right for left, right in itertools.pairwise(bounds)):
            self._semantic("$.thresholds", "threshold bounds must be strictly increasing")
        if bounds[-1] != 100:
            self._semantic("$.thresholds", "last threshold must equal 100")
        if len(labels) != len(set(labels)):
            self._semantic("$.thresholds", "threshold labels must be unique")
        numeric_values = [
            artifact["intercept"],
            *coefficients.values(),
            *bounds,
            artifact["provenance"]["holdout_metrics"]["mae"],
            artifact["provenance"]["holdout_metrics"]["spearman_r"],
        ]
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in numeric_values
        ):
            self._semantic("$", "all numeric values must be finite real numbers")
        version = artifact["version"]
        if version.startswith("test-") and not self.allow_test_artifacts:
            self._semantic("$.version", "test artifact requires explicit test mode")
        if (
            not version.startswith("test-")
            and int(version.split(".", 1)[0]) != self.supported_major
        ):
            self._semantic("$.version", "unsupported production major version")
        provenance_count = artifact["provenance"].get("training_query_count")
        if provenance_count is not None and provenance_count != artifact["training_query_count"]:
            self._semantic(
                "$.provenance.training_query_count",
                "training query count does not match artifact",
            )
        if self.errors:
            return False
        self.artifact = dict(artifact)
        return True

    def _semantic(self, path: str, message: str) -> None:
        self.errors.append({"path": path, "validator": "semantic", "message": message})
