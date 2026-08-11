"""Live snapshot and interval tracking workflows."""

from datetime import UTC, datetime, timedelta

from .exceptions import StorageError
from .result import Result
from .time_utils import parse_utc

MIN_GROWTH_INTERVAL_MINUTES = 15
BASELINE_TOLERANCE_RATIO = 0.25
MAX_BASELINE_TOLERANCE_HOURS = 24


class TrackingModule:
    def __init__(self, channel_module, video_module, search_module, analytics, storage):
        self.channel_module = channel_module
        self.video_module = video_module
        self.search_module = search_module
        self.analytics = analytics
        self.storage = storage

    def _require_storage(self):
        if self.storage is None:
            return Result.error("No storage configured", "storage_unavailable")
        return None

    def snapshot_channel_live(self, channel_id_or_handle):
        error = self._require_storage()
        if error:
            return error
        fetched = self.channel_module.channel_info(channel_id_or_handle)
        if not fetched.ok or not fetched.items:
            return fetched
        channel = fetched.items[0]
        try:
            self.storage.snapshot_channel(
                channel["channel_id"],
                name=channel.get("name"),
                subscriber_count=channel.get("subscriber_count"),
                video_count=channel.get("video_count"),
            )
        except StorageError:
            return Result.error(
                "Channel loaded; snapshot persistence failed",
                "storage_error",
                items=[channel],
            )
        return Result(status="ok", items=[channel])

    def snapshot_video_live(self, video_id):
        error = self._require_storage()
        if error:
            return error
        fetched = self.video_module.video_info(video_id)
        if not fetched.ok or not fetched.items:
            return fetched
        video = fetched.items[0]
        try:
            self.storage.snapshot_video(
                video_id,
                channel_id=video.get("channel_id"),
                title=video.get("title"),
                view_count=video.get("view_count"),
                like_count=video.get("like_count"),
                comment_count=video.get("comment_count"),
                published_at=video.get("publish_date"),
                is_live=bool(video.get("is_live")),
            )
        except StorageError:
            return Result.error(
                "Video loaded; snapshot persistence failed",
                "storage_error",
                items=[video],
            )
        return Result(status="ok", items=[video])

    def snapshot_keyword_live(self, keyword, limit=20):
        error = self._require_storage()
        if error:
            return error
        fetched = self.search_module.search(keyword, limit=limit)
        if fetched.status in {"error", "unsupported"}:
            return fetched
        top = fetched.items[0] if fetched.items else {}
        try:
            self.storage.snapshot_keyword(
                keyword,
                result_count=len(fetched.items),
                top_video_id=top.get("videoId"),
                top_video_views=top.get("views"),
            )
        except StorageError:
            return Result.error(
                "Search loaded; snapshot persistence failed",
                "storage_error",
                items=[
                    {
                        "keyword": keyword,
                        "sample_result_count": len(fetched.items),
                    }
                ],
            )
        return Result(
            status=fetched.status,
            items=[
                {
                    "keyword": keyword,
                    "sample_result_count": len(fetched.items),
                    "top_video_id": top.get("videoId"),
                    "top_video_views": top.get("views"),
                }
            ],
            reason=fetched.reason,
            metadata={"collection": fetched.metadata},
        )

    def channel_growth(self, channel_id, interval_hours=168, as_of=None):
        error = self._require_storage()
        if error:
            return error
        if interval_hours <= 0:
            raise ValueError("interval_hours must be positive")
        as_of = as_of or datetime.now(UTC)
        if as_of.tzinfo is None:
            return Result.error("as_of must be timezone-aware", "invalid_input")
        as_of = as_of.astimezone(UTC)
        current_rows = self.storage.get_channel_snapshots(channel_id, limit=1)
        if not current_rows:
            return Result(
                status="empty",
                reason="No channel snapshots",
                metadata={"channel_id": channel_id},
            )
        latest = current_rows[-1]
        # Use snapshot at or before as_of, not just the newest in DB
        latest_at_or_before = self.storage.get_channel_snapshot_at_or_before(
            channel_id, as_of.isoformat()
        )
        if latest_at_or_before is None:
            return Result(
                status="empty",
                reason="No snapshot at or before as_of",
                metadata={"channel_id": channel_id, "as_of": as_of.isoformat()},
            )
        latest = latest_at_or_before
        target_time = as_of - timedelta(hours=interval_hours)
        baseline = self.storage.get_channel_snapshot_at_or_before(
            channel_id, target_time.isoformat()
        )
        if baseline is None:
            return Result(
                status="partial",
                items=[{"channel_id": channel_id, "latest": latest}],
                reason="No baseline at or before requested interval",
                metadata={"interval_hours_requested": interval_hours},
            )
        start = parse_utc(baseline["snapshot_at"])
        end = parse_utc(latest["snapshot_at"])
        elapsed_seconds = (end - start).total_seconds()
        if (
            baseline.get("id") == latest.get("id")
            or elapsed_seconds <= 0
            or elapsed_seconds < MIN_GROWTH_INTERVAL_MINUTES * 60
        ):
            return Result(
                status="partial",
                items=[{"channel_id": channel_id, "latest": latest}],
                reason="Need two distinct observations at least 15 minutes apart",
                metadata={
                    "baseline_id": baseline.get("id"),
                    "latest_id": latest.get("id"),
                    "baseline_at": baseline.get("snapshot_at"),
                    "latest_at": latest.get("snapshot_at"),
                    "minimum_interval_minutes": MIN_GROWTH_INTERVAL_MINUTES,
                },
            )
        tolerance_hours = min(
            interval_hours * BASELINE_TOLERANCE_RATIO,
            MAX_BASELINE_TOLERANCE_HOURS,
        )
        baseline_age_hours = (target_time - start).total_seconds() / 3600
        if baseline_age_hours > tolerance_hours:
            return Result(
                status="partial",
                items=[{"channel_id": channel_id, "latest": latest}],
                reason="Baseline is outside requested interval tolerance",
                metadata={
                    "requested_target": target_time.isoformat(),
                    "actual_baseline": start.isoformat(),
                    "tolerance_hours": tolerance_hours,
                },
            )
        elapsed_days = elapsed_seconds / 86400

        def delta(field):
            before, after = baseline.get(field), latest.get(field)
            if (
                isinstance(before, bool)
                or isinstance(after, bool)
                or not isinstance(before, int)
                or not isinstance(after, int)
            ):
                return None
            return after - before

        subscriber_delta = delta("subscriber_count")
        video_delta = delta("video_count")
        growth = {
            "channel_id": channel_id,
            "baseline": baseline,
            "latest": latest,
            "interval_hours_requested": interval_hours,
            "interval_hours_observed": round(elapsed_days * 24, 2),
            "subscriber_delta": subscriber_delta,
            "subscriber_delta_per_day": (
                round(subscriber_delta / elapsed_days, 2)
                if subscriber_delta is not None and elapsed_days > 0
                else None
            ),
            "video_delta": video_delta,
            "video_delta_per_day": (
                round(video_delta / elapsed_days, 2)
                if video_delta is not None and elapsed_days > 0
                else None
            ),
        }
        return Result(status="ok", items=[growth])

    def compare_competitors(self, channel_ids, interval_hours=168, refresh=True):
        rows = []
        failures = []
        for channel_id in dict.fromkeys(channel_ids):
            if refresh:
                refreshed = self.snapshot_channel_live(channel_id)
                if refreshed.status in {"error", "unsupported"}:
                    failures.append(
                        {
                            "channel_id": channel_id,
                            "result": refreshed.to_dict(),
                        }
                    )
                    continue
            growth = self.channel_growth(channel_id, interval_hours)
            if growth.items:
                rows.append(growth.items[0])
            if growth.status != "ok":
                failures.append(
                    {
                        "channel_id": channel_id,
                        "result": growth.to_dict(),
                    }
                )
        status = (
            "error"
            if not rows and failures
            else ("partial" if failures else ("empty" if not rows else "ok"))
        )
        return Result(
            status=status,
            items=rows,
            reason="Some competitors were unavailable" if failures else "",
            metadata={
                "interval_hours_requested": interval_hours,
                "failures": failures,
            },
        )
