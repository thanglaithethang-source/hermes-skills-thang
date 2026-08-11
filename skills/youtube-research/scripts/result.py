"""Generic, invariant-enforced public result envelope."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar, cast

from .models import ResultStatus

T = TypeVar("T")


@dataclass
class Result(Generic[T]):
    status: ResultStatus = "ok"
    items: list[T] = field(default_factory=list)
    reason: str = ""
    error_code: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.items, (str, bytes)) or not isinstance(self.items, Sequence):
            raise TypeError("items must be a non-string sequence")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        self.items = list(self.items)
        self.metadata = dict(self.metadata)
        if self.status == "ok" and not self.items:
            raise ValueError("ok status requires at least one item")
        if self.status == "empty" and self.items:
            raise ValueError("empty status cannot contain items")
        if self.status == "partial" and not self.reason:
            raise ValueError("partial status requires a reason")
        if self.status in {"error", "unsupported"}:
            if self.items:
                raise ValueError(f"{self.status} status cannot contain items")
            if not self.reason:
                raise ValueError(f"{self.status} status requires a reason")

    @property
    def ok(self) -> bool:
        return self.status in {"ok", "empty"}

    @property
    def partial(self) -> bool:
        return self.status == "partial"

    @property
    def truncated(self) -> bool:
        return bool(self.metadata.get("truncated"))

    @property
    def has_more(self) -> bool:
        return bool(self.metadata.get("has_more"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "items": list(self.items),
            "reason": self.reason,
            "error_code": self.error_code,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def _nonnegative_int(value: Any, field_name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field_name} must be a non-negative integer")
        return cast(int, value)

    @classmethod
    def collection(
        cls,
        *,
        items: Sequence[T],
        requested: int,
        pages_requested: int = 1,
        pages_succeeded: int = 1,
        has_more: bool = False,
        stop_reason: str = "exhausted",
        api_error: Mapping[str, Any] | None = None,
        parser_diagnostics: Sequence[Mapping[str, Any]] | None = None,
        status_override: str | None = None,
    ) -> Result[T]:
        if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
            raise TypeError("items must be a non-string sequence")
        requested = cls._nonnegative_int(requested, "requested")
        pages_requested = cls._nonnegative_int(pages_requested, "pages_requested")
        pages_succeeded = cls._nonnegative_int(pages_succeeded, "pages_succeeded")
        if pages_succeeded > pages_requested:
            raise ValueError("pages_succeeded cannot exceed pages_requested")
        pre_slice_count = len(items)
        sliced = list(items[:requested])
        metadata = {
            "requested": requested,
            "returned": len(sliced),
            "pages_requested": pages_requested,
            "pages_succeeded": pages_succeeded,
            "has_more": bool(has_more),
            "truncated": bool(has_more or pre_slice_count > requested),
            "stop_reason": stop_reason,
            "parser_diagnostics": [dict(item) for item in (parser_diagnostics or [])],
        }
        if api_error:
            return cls.error(
                str(api_error.get("_message") or "API request failed"),
                api_error.get("_status"),
                metadata=metadata,
                items=sliced,
            )
        if status_override:
            if status_override not in {"partial", "unsupported"}:
                raise ValueError("status_override must be partial or unsupported")
            if status_override == "unsupported":
                return cls.unsupported("Response format is unsupported", metadata=metadata)
            return cls(
                status="partial",
                items=sliced,
                reason="Response format is partially supported",
                metadata=metadata,
            )
        if stop_reason in {"repeated_token", "no_progress", "page_cap"}:
            return cls(
                status="partial",
                items=sliced,
                reason=f"Collection stopped: {stop_reason}",
                metadata=metadata,
            )
        if not sliced:
            return cls(
                status="empty",
                reason="Collection completed with no matching items",
                metadata=metadata,
            )
        return cls(status="ok", items=sliced, metadata=metadata)

    @classmethod
    def error(
        cls,
        reason: str,
        error_code: Any | None = None,
        metadata: Mapping[str, Any] | None = None,
        items: Sequence[T] | None = None,
    ) -> Result[T]:
        copied = list(items or [])
        return cls(
            status="partial" if copied else "error",
            items=copied,
            reason=reason,
            error_code=error_code,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def unsupported(cls, reason: str, metadata: Mapping[str, Any] | None = None) -> Result[T]:
        return cls(
            status="unsupported",
            reason=reason,
            metadata=dict(metadata or {}),
        )

    def __repr__(self) -> str:
        return f"Result(status={self.status}, items={len(self.items)}, reason={self.reason})"
