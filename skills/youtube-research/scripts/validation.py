"""Shared public-boundary input validation."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, cast


@dataclass(frozen=True)
class ValidationError(ValueError):
    field: str
    message: str
    code: str = "invalid_input"

    def __str__(self) -> str:
        return self.message


def _string(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(field, f"{field} must be a non-empty string")
    normalized = value.strip()
    if len(normalized) > maximum:
        raise ValidationError(field, f"{field} exceeds {maximum} characters")
    return normalized


def validate_query(value: Any) -> str:
    return _string(value, "query", 200)


def _pattern(value: Any, field: str, pattern: str, maximum: int) -> str:
    normalized = _string(value, field, maximum)
    if not re.fullmatch(pattern, normalized):
        raise ValidationError(field, f"{field} has an invalid format")
    return normalized


def validate_video_id(value: Any) -> str:
    return _pattern(value, "video_id", r"[A-Za-z0-9_-]{11}", 11)


def validate_channel_id(value: Any) -> str:
    return _pattern(value, "channel_id", r"UC[A-Za-z0-9_-]{20,30}", 32)


def validate_handle(value: Any) -> str:
    return _pattern(value, "handle", r"@[A-Za-z0-9._-]{3,30}", 31)


def validate_region(value: Any) -> str:
    return _pattern(value, "region", r"[A-Za-z]{2}", 2).upper()


def validate_locale(value: Any) -> str:
    return _pattern(value, "locale", r"[a-z]{2,3}(?:-[A-Z]{2})?", 6)


def validate_sort(value: Any) -> str | None:
    if value is None:
        return None
    if value not in {"views", "date"}:
        raise ValidationError("filter_sort", "filter_sort must be views, date, or None")
    return cast(str, value)


def validate_int_range(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(field, f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise ValidationError(field, f"{field} must be between {minimum} and {maximum}")
    return cast(int, value)


def validate_id_batch(
    values: Any,
    *,
    maximum: int = 100,
    validator: Callable[[Any], str] = validate_video_id,
) -> list[str]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Iterable):
        raise ValidationError("ids", "ids must be a non-string iterable")
    result = [validator(value) for value in values]
    if not 1 <= len(result) <= maximum:
        raise ValidationError("ids", f"ids must contain 1 to {maximum} values")
    if len(result) != len(set(result)):
        raise ValidationError("ids", "ids must be unique")
    return result
