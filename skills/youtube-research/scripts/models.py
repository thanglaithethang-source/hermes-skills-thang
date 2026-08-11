"""Shared result and parser models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Literal, TypeVar

ResultStatus = Literal["ok", "empty", "partial", "error", "unsupported"]
ParseStatus = Literal["parsed", "missing", "invalid", "hidden", "live", "upcoming"]
T = TypeVar("T")


@dataclass(frozen=True)
class ParseDiagnostics:
    surface: str
    response_kind: Literal["initial", "continuation", "entity"]
    recognized_container: bool
    container_path: str | None
    candidate_nodes: int
    parsed_nodes: int
    invalid_nodes: int
    unknown_renderer_types: tuple[str, ...]
    continuation_token_present: bool
    shape_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        value = dict(self.__dict__)
        value["unknown_renderer_types"] = list(self.unknown_renderer_types)
        return value


@dataclass(frozen=True)
class ParsedValue(Generic[T]):
    value: T | None
    raw: str
    status: ParseStatus
    reason: str | None = None


@dataclass
class CanonicalVideo:
    video_id: str
    channel_id: str | None
    title: str
    view_count: int | None
    duration_seconds: int | None
    publish_date: str | None
    published_raw: str
    duration_raw: str
    is_live: bool = False
    is_upcoming: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        row = {
            "video_id": self.video_id,
            "channel_id": self.channel_id,
            "title": self.title,
            "view_count": self.view_count,
            "duration_seconds": self.duration_seconds,
            "publish_date": self.publish_date,
            "published_raw": self.published_raw,
            "duration_raw": self.duration_raw,
            "is_live": self.is_live,
            "is_upcoming": self.is_upcoming,
            **self.extra,
        }
        row.update(
            {
                "videoId": self.video_id,
                "channelId": self.channel_id or "",
                "views": self.view_count,
                "duration": self.duration_raw,
                "published": self.published_raw,
            }
        )
        return row


@dataclass(frozen=True)
class ParsedPage:
    items: list[dict[str, Any]]
    continuation_token: str | None
    diagnostics: ParseDiagnostics
    fingerprint_truncated: bool = False
