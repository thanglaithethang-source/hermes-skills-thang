"""
Browse/Suggested module — detect presence in suggested videos, browse feed.
"""

from .innertube import InnerTubeClient
from .pagination import collect_pages
from .parsers import parse_compact_video, parse_lockup_video, parse_video_page
from .result import Result
from .validation import (
    ValidationError,
    validate_channel_id,
    validate_int_range,
    validate_video_id,
)


class BrowseSuggestedModule:
    """Suggested video detection and browse feed sampling."""

    def __init__(self, client=None):
        self.client = client or InnerTubeClient()

    def suggested_for(self, video_id, limit=20, max_pages=20):
        """
        Get suggested/related videos for a given video.
        Uses InnerTube /next endpoint.
        Returns list of dicts: videoId, title, channel, views, duration, published
        """
        try:
            video_id = validate_video_id(video_id)
            limit = validate_int_range(limit, "limit", 1, 100)
            max_pages = validate_int_range(max_pages, "max_pages", 1, 50)
        except ValidationError as exc:
            return Result.error(str(exc), exc.code, metadata={"field": exc.field})
        return collect_pages(
            lambda token: (
                self.client.next(continuation=token)
                if token
                else self.client.next(video_id=video_id)
            ),
            lambda data: parse_video_page(data, surface="suggested"),
            limit=limit,
            max_pages=max_pages,
            identity=lambda row: row.get("video_id"),
        )

    def _parse_lockup_suggested(self, lvm):
        """Parse lockupViewModel from suggested videos using centralized parser."""
        return parse_lockup_video(lvm)

    def _parse_compact_video(self, cvr):
        """Parse old compactVideoRenderer format using centralized parser."""
        return parse_compact_video(cvr)

    def find_in_suggested(self, video_id, target_channel_id=None, target_video_id=None, limit=50):
        """
        Check if a target channel/video appears in the suggested list of a video.
        Returns: {found, position, video_id, channel_id, suggested_list}
        """
        try:
            video_id = validate_video_id(video_id)
            if target_channel_id is not None:
                target_channel_id = validate_channel_id(target_channel_id)
            if target_video_id is not None:
                target_video_id = validate_video_id(target_video_id)
            if target_channel_id is None and target_video_id is None:
                raise ValidationError("target", "At least one target ID is required")
        except ValidationError as exc:
            return Result.error(str(exc), exc.code, metadata={"field": exc.field})
        suggested_result = self.suggested_for(video_id, limit=limit)
        if suggested_result.status in {"error", "unsupported"}:
            return Result(
                status=suggested_result.status,
                reason=suggested_result.reason,
                error_code=suggested_result.error_code,
                metadata={"upstream": suggested_result.to_dict()},
            )
        suggested = suggested_result.items

        found_entries = []

        for i, s in enumerate(suggested):
            matched_by = []
            if target_video_id and s["videoId"] == target_video_id:
                matched_by.append("video_id")
            if target_channel_id and s["channelId"] == target_channel_id:
                matched_by.append("channel_id")
            if matched_by:
                found_entries.append(
                    {
                        "position": i + 1,
                        "video_id": s["videoId"],
                        "title": s["title"],
                        "channel": s["channel"],
                        "channel_id": s["channelId"],
                        "views": s["views"],
                        "matched_by": matched_by,
                    }
                )

        presence = {
            "source_video_id": video_id,
            "target_channel_id": target_channel_id,
            "target_video_id": target_video_id,
            "found": len(found_entries) > 0,
            "found_entries": found_entries,
            "total_suggested_checked": len(suggested),
            "suggested_list": suggested,
        }
        return Result(
            status="partial" if suggested_result.partial else "ok",
            items=[presence],
            reason=suggested_result.reason,
            metadata={"upstream": suggested_result.metadata},
        )

    def browse_feed_sample(self, limit=30, max_pages=20):
        """
        Sample the browse feed (YouTube home page).
        Returns list of videos in the browse feed.
        """
        try:
            limit = validate_int_range(limit, "limit", 1, 100)
            max_pages = validate_int_range(max_pages, "max_pages", 1, 50)
        except ValidationError as exc:
            return Result.error(str(exc), exc.code, metadata={"field": exc.field})
        return collect_pages(
            lambda token: (
                self.client.browse(continuation=token)
                if token
                else self.client.browse(browse_id="FEwhat_to_watch")
            ),
            lambda data: parse_video_page(data, surface="browse"),
            limit=limit,
            max_pages=max_pages,
            identity=lambda row: row.get("video_id"),
        )

    def check_browse_presence(self, channel_id, limit=30):
        """
        Check if a channel's videos appear in the browse feed.
        Returns: {found, appearances, total_checked}
        """
        feed_result = self.browse_feed_sample(limit=limit)
        if feed_result.status in {"error", "unsupported"}:
            return Result(
                status=feed_result.status,
                reason=feed_result.reason,
                error_code=feed_result.error_code,
                metadata={"upstream": feed_result.to_dict()},
            )
        feed = feed_result.items
        appearances = []
        for v in feed:
            if v.get("channelId") == channel_id or v.get("channel_id") == channel_id:
                appearances.append(v)

        presence = {
            "target_channel_id": channel_id,
            "found": len(appearances) > 0,
            "appearances": appearances,
            "total_feed_checked": len(feed),
            "feed_sample": feed,
        }
        return Result(
            status="partial" if feed_result.partial else "ok",
            items=[presence],
            reason=feed_result.reason,
            metadata={"upstream": feed_result.metadata},
        )
