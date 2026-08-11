"""Shared timezone-safe timestamp helpers."""

from datetime import UTC, datetime, tzinfo


def parse_utc(value: str, *, assume_timezone: tzinfo | None = None) -> datetime:
    if not isinstance(value, str):
        raise TypeError("timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        if assume_timezone is None:
            raise ValueError("naive timestamp is ambiguous")
        parsed = parsed.replace(tzinfo=assume_timezone)
    return parsed.astimezone(UTC)


# Kept as the plan's internal spelling for callers/tests.
_parse_utc = parse_utc
