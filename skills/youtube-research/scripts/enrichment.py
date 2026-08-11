"""Exact publish-date enrichment through InnerTube's /player endpoint."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import UTC, date, datetime
from typing import Any

from .models import ParsedValue
from .result import Result


def extract_player_publish_date(player: Mapping[str, Any]) -> ParsedValue[str]:
    if not isinstance(player, Mapping):
        return ParsedValue(None, "", "invalid", "player response is not an object")
    renderer = player.get("microformat", {})
    renderer = (
        renderer.get("playerMicroformatRenderer", {}) if isinstance(renderer, Mapping) else {}
    )
    details = player.get("videoDetails", {})
    details = details if isinstance(details, Mapping) else {}
    values = (
        renderer.get("publishDate"),
        renderer.get("uploadDate"),
        details.get("publishDate"),
    )
    raw = next((value for value in values if value is not None), "")
    if not isinstance(raw, str):
        return ParsedValue(None, "", "invalid", "publish date is not a string")
    raw = raw.strip()
    if not raw:
        return ParsedValue(None, raw, "missing", "exact publish date is absent")
    try:
        if len(raw) == 10:
            parsed_date = date.fromisoformat(raw)
            return ParsedValue(f"{parsed_date.isoformat()}T00:00:00Z", raw, "parsed", "date")
        if "T" not in raw:
            raise ValueError
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        normalized = parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
        return ParsedValue(normalized, raw, "parsed", "instant")
    except (TypeError, ValueError):
        return ParsedValue(None, raw, "invalid", "publish date is not authoritative ISO 8601")


class PublishDateEnricher:
    def __init__(self, client: Any):
        self.client = client

    def enrich(
        self,
        rows: Sequence[Mapping[str, Any]],
        *,
        max_items: int = 100,
    ) -> Result[dict[str, Any]]:
        if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
            return Result.error("rows must be a non-string sequence", "invalid_input")
        if (
            isinstance(max_items, bool)
            or not isinstance(max_items, int)
            or not 1 <= max_items <= 100
        ):
            return Result.error("max_items must be between 1 and 100", "invalid_input")
        copied = [deepcopy(dict(row)) for row in rows if isinstance(row, Mapping)]
        if not copied:
            if rows:
                return Result.error("No usable input rows", "invalid_input")
            return Result(status="empty", reason="No rows to enrich")

        missing_ids: list[str] = []
        by_id: dict[str, list[dict[str, Any]]] = {}
        skipped = 0
        for row in copied:
            row.setdefault("publish_date", None)
            video_id = row.get("video_id") or row.get("videoId")
            if not isinstance(video_id, str) or not video_id:
                skipped += 1
                continue
            by_id.setdefault(video_id, []).append(row)
            if not row.get("publish_date") and video_id not in missing_ids:
                missing_ids.append(video_id)

        failures: list[dict[str, Any]] = []
        attempted = succeeded = 0
        for index, video_id in enumerate(missing_ids):
            if index >= max_items:
                failures.append(
                    {
                        "video_id": video_id,
                        "stage": "player_publish_date",
                        "error_code": "enrichment_cap",
                        "reason": "Publish-date enrichment cap reached",
                    }
                )
                continue
            attempted += 1
            player = self.client.player(video_id)
            if not isinstance(player, Mapping):
                player = {"_status": "invalid_payload_type"}
            playable = player.get("playabilityStatus", {})
            playable_status = playable.get("status") if isinstance(playable, Mapping) else None
            parsed = extract_player_publish_date(player)
            if (
                player.get("_error")
                or playable_status
                in {"ERROR", "UNPLAYABLE", "LOGIN_REQUIRED", "AGE_CHECK_REQUIRED"}
                or parsed.value is None
            ):
                reason = (
                    player.get("_message")
                    or (playable.get("reason") if isinstance(playable, Mapping) else None)
                    or parsed.reason
                    or "Exact publish date unavailable"
                )
                failures.append(
                    {
                        "video_id": video_id,
                        "stage": "player_publish_date",
                        "error_code": player.get("_status") or "publish_date_unavailable",
                        "reason": str(reason)[:200],
                    }
                )
                continue
            succeeded += 1
            for row in by_id[video_id]:
                row["publish_date"] = parsed.value
                row.setdefault("extra", {})["publish_date_precision"] = parsed.reason

        metadata = {
            "enrichment_requested": len(missing_ids),
            "enrichment_attempted": attempted,
            "enrichment_succeeded": succeeded,
            "enrichment_failed": len(failures),
            "enrichment_skipped": skipped,
            "enrichment_failures": failures,
        }
        return Result(
            status="partial" if failures or skipped else "ok",
            items=copied,
            reason="Some publish dates could not be enriched" if failures or skipped else "",
            metadata=metadata,
        )
