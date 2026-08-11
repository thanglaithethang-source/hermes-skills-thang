"""Search, autocomplete, and trending collectors."""

from __future__ import annotations

from typing import Any

from .client_profile import KNOWN_GOOD_PROFILE
from .innertube import InnerTubeClient
from .pagination import collect_pages
from .parsers import parse_count, parse_duration, parse_video_page
from .result import Result
from .validation import (
    ValidationError,
    validate_int_range,
    validate_query,
    validate_region,
    validate_sort,
)


def parse_view_count(value: Any) -> int | None:
    """Compatibility wrapper around the canonical count parser."""
    return parse_count(value).value


def parse_duration_seconds(value: Any) -> int | None:
    """Compatibility wrapper around the canonical duration parser."""
    return parse_duration(value).value


class SearchModule:
    def __init__(self, client: Any = None):
        self.client = client or InnerTubeClient()

    def search(
        self,
        query: Any,
        limit: int = 20,
        filter_sort: str | None = None,
        max_pages: int = 20,
    ) -> Result[dict[str, Any]]:
        try:
            query = validate_query(query)
            limit = validate_int_range(limit, "limit", 1, 100)
            max_pages = validate_int_range(max_pages, "max_pages", 1, 50)
            filter_sort = validate_sort(filter_sort)
        except ValidationError as exc:
            return Result.error(str(exc), exc.code, metadata={"field": exc.field})
        params = KNOWN_GOOD_PROFILE.search_sort_params.get(filter_sort) if filter_sort else None
        return collect_pages(
            lambda continuation: self.client.search(
                query if continuation is None else None,
                params=params,
                continuation=continuation,
            ),
            lambda data: parse_video_page(data, surface="search"),
            limit=limit,
            max_pages=max_pages,
            identity=lambda row: row.get("video_id"),
        )

    def _parse_search_page(self, data: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
        page = parse_video_page(data, surface="search")
        return page.items, page.continuation_token

    def search_suggestions(self, prefix: Any, limit: int = 20) -> Result[str]:
        try:
            prefix = validate_query(prefix)
            limit = validate_int_range(limit, "limit", 1, 100)
        except ValidationError as exc:
            return Result.error(str(exc), exc.code, metadata={"field": exc.field})
        suggestions = self.client.complete(prefix)
        if isinstance(suggestions, dict) and suggestions.get("_error"):
            return Result.error(
                suggestions.get("_message", "Autocomplete request failed"),
                suggestions.get("_status"),
            )
        if not isinstance(suggestions, list):
            return Result.error(
                "Autocomplete request failed or returned an invalid payload",
                "invalid_payload_type",
            )
        return Result.collection(items=suggestions, requested=limit)

    def trending(self, region: Any = "VN", limit: int = 30) -> Result[dict[str, Any]]:
        try:
            region = validate_region(region)
            limit = validate_int_range(limit, "limit", 1, 100)
        except ValidationError as exc:
            return Result.error(str(exc), exc.code, metadata={"field": exc.field})
        data = self.client.get_trending(region=region)
        if data.get("_error"):
            return Result.unsupported(
                f"Trending endpoint returned error: {data.get('_status')} "
                f"{data.get('_message', '')[:100]}",
                metadata={"region": region},
            )
        page = parse_video_page(data, surface="trending")
        diagnostic = page.diagnostics.to_dict()
        if not page.diagnostics.recognized_container:
            return Result.unsupported(
                "Trending response format is unsupported",
                metadata={"parser_diagnostics": [diagnostic], "region": region},
            )
        result = Result.collection(
            items=page.items,
            requested=limit,
            parser_diagnostics=[diagnostic],
        )
        result.metadata["region"] = region
        return result
