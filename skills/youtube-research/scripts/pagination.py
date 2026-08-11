"""Generic drift-aware pagination for InnerTube list surfaces."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import ParsedPage
from .result import Result


def collect_pages(
    fetch_page: Callable[[str | None], dict[str, Any]],
    parse_page: Callable[[dict[str, Any]], ParsedPage],
    *,
    limit: int,
    max_pages: int,
    identity: Callable[[dict[str, Any]], Any],
) -> Result[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_ids: set[Any] = set()
    seen_tokens: set[str] = set()
    diagnostics: list[dict[str, Any]] = []
    token: str | None = None
    pages_requested = pages_succeeded = 0
    stop_reason = "exhausted"
    has_more = False
    api_error = None
    status_override = None
    reason = ""

    while len(items) < limit and pages_requested < max_pages:
        if token and token in seen_tokens:
            stop_reason, has_more = "repeated_token", True
            break
        if token:
            seen_tokens.add(token)
        data = fetch_page(token)
        pages_requested += 1
        if not isinstance(data, dict):
            data = {
                "_error": True,
                "_status": "invalid_payload_type",
                "_message": "Response was not an object",
            }
        if data.get("_error"):
            api_error, stop_reason = data, "api_error"
            break
        page = parse_page(data)
        pages_succeeded += 1
        diag = page.diagnostics.to_dict()
        if page.fingerprint_truncated:
            diag["fingerprint_truncated"] = True
        diagnostics.append(diag)

        if not page.diagnostics.recognized_container:
            status_override = "partial" if items else "unsupported"
            stop_reason = "response_drift"
            reason = "Unrecognized response container"
            break
        if page.diagnostics.candidate_nodes and not page.diagnostics.parsed_nodes:
            status_override = "partial" if items else "unsupported"
            stop_reason = "parser_coverage"
            reason = "Recognized container contained no supported renderers"
            break

        added = 0
        for row in page.items:
            key = identity(row)
            if key and key not in seen_ids:
                seen_ids.add(key)
                items.append(row)
                added += 1
        if page.diagnostics.invalid_nodes or page.diagnostics.unknown_renderer_types:
            status_override = "partial"
            stop_reason = "parser_coverage"
            reason = "Parser coverage was incomplete"
            has_more = bool(page.continuation_token)
            break
        token = page.continuation_token
        has_more = bool(token)
        if not token:
            stop_reason = "exhausted"
            break
        if added == 0:
            stop_reason = "no_progress"
            break
    else:
        if len(items) >= limit:
            stop_reason, has_more = "limit", bool(token)
        elif pages_requested >= max_pages:
            stop_reason, has_more = "page_cap", True

    result = Result.collection(
        items=items,
        requested=limit,
        pages_requested=pages_requested,
        pages_succeeded=pages_succeeded,
        has_more=has_more,
        stop_reason=stop_reason,
        api_error=api_error,
        parser_diagnostics=diagnostics,
        status_override=status_override,
    )
    if reason and result.status in {"partial", "unsupported"}:
        result.reason = reason
    return result
