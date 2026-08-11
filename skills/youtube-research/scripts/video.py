"""
Video module — video metadata, batch video info, tags, duration, publish date.
"""

import json
import re

from .enrichment import extract_player_publish_date
from .innertube import InnerTubeClient
from .parsers import _parse_count
from .result import Result
from .validation import ValidationError, validate_id_batch, validate_video_id


class VideoModule:
    """Video metadata via InnerTube /player endpoint."""

    def __init__(self, client=None):
        self.client = client or InnerTubeClient()

    def video_info(self, video_id):
        """
        Get video metadata: title, channel, channel_id, view_count, like_count,
        comment_count, duration_seconds, publish_date, tags, description, thumbnail.
        """
        try:
            video_id = validate_video_id(video_id)
        except ValidationError as exc:
            return Result.error(str(exc), exc.code, metadata={"field": exc.field})
        data = self.client.player(video_id)
        if (
            (data.get("_error") or not data.get("videoDetails"))
            and getattr(self.client, "authenticated", False)
            and hasattr(self.client, "page_state")
        ):
            fallback = self.client.page_state(video_id)
            if isinstance(fallback, dict):
                data = fallback
        if data.get("_error"):
            return Result.error(data.get("_message", "Unknown error"), data.get("_status"))

        playability = data.get("playabilityStatus", {})
        status = playability.get("status") if isinstance(playability, dict) else None
        vd = data.get("videoDetails", {})
        if (
            status in {"ERROR", "UNPLAYABLE", "LOGIN_REQUIRED", "AGE_CHECK_REQUIRED"}
            or not isinstance(vd, dict)
            or not vd
        ):
            safe_status = str(status or "missing_details").lower()
            reason = (
                playability.get("reason") if isinstance(playability, dict) else None
            ) or "Video is not playable"
            metadata = {
                "playability_status": status,
                "subreason_codes": [
                    item.get("reason")
                    for item in playability.get("errorScreen", {})
                    .get("playerErrorMessageRenderer", {})
                    .get("subreason", {})
                    .get("runs", [])
                    if isinstance(item, dict) and item.get("reason")
                ]
                if isinstance(playability, dict)
                else [],
            }
            return Result.error(
                str(reason)[:200],
                f"playability_{safe_status}",
                metadata=metadata,
            )

        # Parse duration
        duration_seconds = None
        try:
            parsed_duration = int(vd.get("lengthSeconds", 0))
            duration_seconds = parsed_duration if parsed_duration > 0 else None
        except (ValueError, TypeError):
            pass

        # Parse view count — preserve None for missing/unparseable
        view_count = None
        try:
            vc = vd.get("viewCount", "")
            if vc:
                view_count = int(vc)
        except (ValueError, TypeError):
            view_count = None

        # Parse like count (from player response)
        like_count = 0
        # Try to get from microformat or other fields
        data.get("microformat", {}).get("playerMicroformatRenderer", {})
        parsed_publish_date = extract_player_publish_date(data)
        publish_date = parsed_publish_date.value

        # Try to get like/comment from streamingData or other
        # InnerTube player response sometimes has rating
        data.get("playerConfig", {}).get("audioConfig", {}).get("averageVolme", 0)

        # Get channel info
        channel_name = vd.get("author", "")
        channel_id = vd.get("channelId", "")

        # Get tags
        tags = vd.get("keywords", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        # Get thumbnail
        thumbnails = vd.get("thumbnail", {}).get("thumbnails", [])
        thumbnail_url = thumbnails[-1].get("url", "") if thumbnails else ""

        # Get description
        description = vd.get("shortDescription", "")

        # Get is_live / is_upcoming
        is_live = vd.get("isLiveContent", False)
        is_upcoming = vd.get("isUpcoming", False) if "isUpcoming" in vd else False

        # Try to get like count from playabilityStatus or other
        # Some videos expose like count in the player response
        like_count = 0
        # Check if like count is in the response
        if "allowRatings" in vd:
            # Video allows ratings — like count may be available via /next endpoint
            pass

        # Get like + comment count from /next endpoint
        like_count = None
        comment_count = None
        next_data = self.client.next(video_id=video_id)
        next_failed = next_data.get("_error")
        if not next_failed:
            # Structured traversal for like count
            like_count = self._extract_like_count(next_data)
            # Comment count from engagement panel
            comment_count = self._extract_comment_count(next_data)

        item = {
            "video_id": video_id,
            "title": vd.get("title", ""),
            "channel": channel_name,
            "channel_id": channel_id,
            "view_count": view_count,
            "like_count": like_count,
            "comment_count": comment_count,
            "duration_seconds": duration_seconds,
            "publish_date": publish_date,
            "tags": tags,
            "description": description[:500],
            "thumbnail": thumbnail_url,
            "is_live": is_live,
            "is_upcoming": is_upcoming,
            "category": vd.get("category", ""),
        }
        visibility = {
            "likes": "observed" if like_count is not None else "absent",
            "comments": "observed" if comment_count is not None else "absent",
        }
        source_metadata = (
            {"video_metadata_source": "authenticated_page_state"}
            if data.get("_page_state_fallback")
            else {}
        )
        if next_failed:
            failure = {
                "endpoint": "next",
                "error_code": next_data.get("_status"),
                "reason": next_data.get("_message"),
            }
            return Result(
                status="partial",
                items=[item],
                reason="Video details loaded; engagement enrichment failed",
                metadata={"enrichment_failures": [failure], **source_metadata},
            )
        return Result(
            status="ok",
            items=[item],
            metadata={"engagement_visibility": visibility, **source_metadata},
        )

    def video_batch(self, video_ids, delay=0.3):
        """Get info for multiple videos with per-item failure metadata."""
        try:
            video_ids = validate_id_batch(video_ids)
        except ValidationError as exc:
            return Result.error(str(exc), exc.code, metadata={"field": exc.field})
        results = []
        failures = []
        for index, vid_id in enumerate(video_ids):
            info = self.video_info(vid_id)
            if info.items:
                results.extend(info.items)
            if info.status != "ok":
                failures.append({"video_id": vid_id, "result": info.to_dict()})
            if delay and index + 1 < len(video_ids):
                sleeper = getattr(self.client, "sleep", None)
                if sleeper:
                    sleeper(delay)
        if failures:
            return Result(
                status="partial" if results else "error",
                items=results,
                reason="Some videos were unavailable",
                metadata={"failures": failures, "requested": len(video_ids)},
            )
        return Result.collection(items=results, requested=len(video_ids))

    def _extract_like_count(self, next_data):
        """Extract like count from /next response using structured traversal.

        Looks for likeCountEntity.likeCountIfIndifferentNumber.
        Falls back to button title text.
        """

        def walk_dicts(node):
            if isinstance(node, dict):
                yield node
                for value in node.values():
                    yield from walk_dicts(value)
            elif isinstance(node, list):
                for value in node:
                    yield from walk_dicts(value)

        # Method 1: likeCountEntity.likeCountIfIndifferentNumber
        for node in walk_dicts(next_data):
            entity = node.get("likeCountEntity")
            if entity and isinstance(entity, dict):
                raw = entity.get("likeCountIfIndifferentNumber")
                if raw and str(raw).isdigit():
                    return int(raw)

        # Method 2: button title text (fallback)
        raw = json.dumps(next_data, ensure_ascii=False)
        match = re.search(r'"iconName"\s*:\s*"LIKE"[^}]*?"title"\s*:\s*"(\d+)"', raw)
        if match:
            return int(match.group(1))

        return None

    def _extract_comment_count(self, next_data):
        """Extract comment count from /next response.

        Looks for contextualInfo in comments engagement panel.
        Parses localized compact values like '2,4 Tr' through count parser.
        """
        panels = next_data.get("engagementPanels", [])
        for panel in panels:
            epslr = panel.get("engagementPanelSectionListRenderer", {})
            # Verify this is the comments panel
            panel_id = epslr.get("panelIdentifier", "")
            if panel_id != "engagement-panel-comments-section":
                continue
            header = epslr.get("header", {})
            ept = header.get("engagementPanelTitleHeaderRenderer", {})
            contextual = ept.get("contextualInfo", {})
            if contextual and "runs" in contextual:
                for run in contextual["runs"]:
                    text = run.get("text", "")
                    # Try parsing as digit first
                    if text.isdigit():
                        return int(text)
                    # Try parsing as localized count (e.g. '2,4 Tr')
                    parsed = _parse_count(text)
                    if parsed is not None:
                        return parsed

        # No regex fallback — previous regex scanned entire response and could
        # match unrelated engagement panels. Only the structured path above is used.
        return None
