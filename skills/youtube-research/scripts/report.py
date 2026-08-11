"""Result-aware competitor and keyword reports."""

import statistics
from datetime import UTC, datetime

from .analytics_estimate import AnalyticsEstimateModule, detect_niche
from .browse_suggested import BrowseSuggestedModule
from .channel import ChannelModule
from .enrichment import PublishDateEnricher
from .innertube import InnerTubeClient
from .report_status import Dependency, reduce_dependencies
from .result import Result
from .search import SearchModule
from .video import VideoModule


class ReportModule:
    def __init__(self, client=None, storage=None, tracking=None):
        self.client = client or InnerTubeClient()
        self.storage = storage
        self.search_mod = SearchModule(self.client)
        self.channel_mod = ChannelModule(self.client)
        self.video_mod = VideoModule(self.client)
        self.analytics_mod = AnalyticsEstimateModule(self.client, storage)
        self.browse_mod = BrowseSuggestedModule(self.client)
        self.publish_date_enricher = PublishDateEnricher(self.client)
        self.tracking_mod = tracking

    @staticmethod
    def _upstream_failure(result):
        return result.status in {"error", "unsupported"}

    def competitor_report(self, channel_id_or_handle, video_limit=10):
        channel_result = self.channel_mod.channel_info(channel_id_or_handle)
        if self._upstream_failure(channel_result) or not channel_result.items:
            return Result(
                status=channel_result.status,
                reason=channel_result.reason or "Channel information unavailable",
                error_code=channel_result.error_code,
                metadata={"channel": channel_result.to_dict()},
            )
        channel = channel_result.items[0]
        channel_id = channel.get("channel_id", channel_id_or_handle)
        videos_result = self.channel_mod.channel_videos(channel_id, limit=video_limit)
        if self._upstream_failure(videos_result):
            return Result(
                status=videos_result.status,
                reason=videos_result.reason,
                error_code=videos_result.error_code,
                metadata={"videos": videos_result.to_dict()},
            )

        normalized_channel_videos = []
        video_reports = []
        failures = []
        video_dependencies = []
        for raw in videos_result.items:
            fetched = self.video_mod.video_info(raw["videoId"])
            video_dependencies.append(fetched)
            if not fetched.items:
                failures.append({"video_id": raw["videoId"], "result": fetched.to_dict()})
                continue
            info = fetched.items[0]
            normalized = {
                "video_id": raw["videoId"],
                "view_count": info.get("view_count", raw.get("views")),
                "duration_seconds": info.get("duration_seconds", raw.get("duration_seconds")),
                "publish_date": info.get("publish_date"),
            }
            normalized_channel_videos.append(normalized)
            row = {
                **normalized,
                "title": info.get("title", raw.get("title", "")),
                "like_count": info.get("like_count"),
                "comment_count": info.get("comment_count"),
                "tags": info.get("tags", []),
                "category": info.get("category", ""),
                "ctr_estimate": self.analytics_mod.estimate_ctr(info),
                "retention_estimate": self.analytics_mod.estimate_retention(info),
                "rpm_estimate": self.analytics_mod.estimate_rpm(info, channel),
                "vph": self.analytics_mod.calculate_vph(raw["videoId"]),
            }
            video_reports.append(row)

        for row in video_reports:
            row["outlier"] = self.analytics_mod.detect_outlier(row, normalized_channel_videos)

        views = [
            row["view_count"]
            for row in video_reports
            if isinstance(row.get("view_count"), int)
            and not isinstance(row.get("view_count"), bool)
        ]
        suggested_result = None
        suggested_presence = None
        if video_reports:
            suggested_result = self.browse_mod.suggested_for(video_reports[0]["video_id"], limit=20)
            if suggested_result.items:
                own = [
                    item for item in suggested_result.items if item.get("channelId") == channel_id
                ]
                suggested_presence = {
                    "source_video": video_reports[0]["video_id"],
                    "total_suggested": len(suggested_result.items),
                    "channel_videos_in_suggested": len(own),
                    "suggested_list": suggested_result.items[:10],
                    "collection_status": suggested_result.status,
                }

        growth = (
            self.tracking_mod.channel_growth(channel_id)
            if self.tracking_mod
            else Result.unsupported("Tracking module is not configured")
        )
        report = {
            "report_type": "competitor",
            "generated_at": datetime.now(UTC).isoformat(),
            "channel": channel,
            "niche": detect_niche(video_reports[0] if video_reports else {}, channel),
            "aggregate_stats": {
                "avg_views": sum(views) // len(views) if views else None,
                "median_views": statistics.median(views) if views else None,
                "max_views": max(views) if views else None,
                "sample_size": len(video_reports),
            },
            "videos": video_reports,
            "suggested_presence": suggested_presence,
            "collection": videos_result.metadata,
            "collection_status": videos_result.status,
            "tracking": growth.to_dict(),
            "disclaimer": (
                "CTR, retention, and RPM are not observable from public data; "
                "shown outputs are explicitly labelled proxies/scenarios."
            ),
        }
        details_result = Result(
            status=(
                "partial"
                if failures and video_reports
                else "error"
                if failures
                else "ok"
                if video_reports
                else "empty"
            ),
            items=video_reports,
            reason=(
                "Some video details unavailable"
                if failures and video_reports
                else "Video details unavailable"
                if failures
                else "No analyzable video sample"
                if not video_reports
                else ""
            ),
            metadata={
                "results": [result.to_dict() for result in video_dependencies],
                "failures": failures,
            },
        )
        suggested_dependency = suggested_result or Result.unsupported(
            "Suggested section was not emitted"
        )
        dependencies = [
            Dependency("channel", channel_result, True),
            Dependency("videos", videos_result, True, True),
            Dependency("video_details", details_result, True),
            Dependency("suggested", suggested_dependency, False),
            Dependency("tracking", growth, False),
        ]
        status, reason, metadata = reduce_dependencies(dependencies, [report])
        return Result(
            status=status,
            items=[report],
            reason=reason,
            metadata={**metadata, "video_failures": failures},
        )

    def keyword_report(self, keyword, limit=20):
        search_result = self.search_mod.search(keyword, limit=limit)
        if self._upstream_failure(search_result):
            return Result(
                status=search_result.status,
                reason=search_result.reason,
                error_code=search_result.error_code,
                metadata={"search": search_result.to_dict()},
            )
        if search_result.status == "empty":
            return Result(
                status="empty",
                reason=search_result.reason,
                metadata={"dependencies": {"search": search_result.to_dict()}},
            )
        suggestions_result = self.search_mod.search_suggestions(keyword, limit=15)
        enrichment = self.publish_date_enricher.enrich(
            search_result.items, max_items=min(limit, 100)
        )
        rows = []
        failures = []
        for position, raw in enumerate(enrichment.items, 1):
            fetched = self.video_mod.video_info(raw["videoId"])
            if not fetched.items:
                failures.append({"video_id": raw["videoId"], "result": fetched.to_dict()})
                continue
            info = fetched.items[0]
            rows.append(
                {
                    "video_id": raw["videoId"],
                    "title": info.get("title", raw.get("title", "")),
                    "channel": raw.get("channel", ""),
                    "channel_id": raw.get("channelId", ""),
                    "view_count": info.get("view_count", raw.get("views")),
                    "duration_seconds": info.get("duration_seconds", raw.get("duration_seconds")),
                    "publish_date": info.get("publish_date"),
                    "ctr_estimate": self.analytics_mod.estimate_ctr(info, search_position=position),
                    "rpm_estimate": self.analytics_mod.estimate_rpm(info),
                }
            )
        valid_views = [
            row["view_count"]
            for row in rows
            if isinstance(row.get("view_count"), int)
            and not isinstance(row.get("view_count"), bool)
        ]
        signals = self.analytics_mod.keyword_competition_signals(keyword, enrichment.items)
        if self.storage:
            history_rows = self.storage.get_keyword_snapshots(keyword, limit=100)
            history = Result.collection(items=history_rows, requested=100)
        else:
            history = Result.error("No storage configured", "storage_unavailable")
        report = {
            "report_type": "keyword",
            "generated_at": datetime.now(UTC).isoformat(),
            "keyword": keyword,
            "suggestions": suggestions_result.items,
            "total_results_analyzed": len(rows),
            "view_observation_count": len(valid_views),
            "avg_views": (sum(valid_views) // len(valid_views) if valid_views else None),
            "max_views": max(valid_views) if valid_views else None,
            "total_views": sum(valid_views) if valid_views else None,
            "keyword_signals": signals,
            "history": history.to_dict(),
            "top_videos": rows,
            "collection": search_result.metadata,
            "collection_status": search_result.status,
        }
        details_result = Result(
            status="partial" if failures else ("ok" if rows else "empty"),
            items=rows,
            reason="Some video details unavailable"
            if failures
            else ("No video details" if not rows else ""),
            metadata={"failures": failures},
        )
        dependencies = [
            Dependency("search", search_result, True),
            Dependency("date_enrichment", enrichment, True),
            Dependency("video_details", details_result, True),
            Dependency("suggestions", suggestions_result, False),
            Dependency("history", history, False, True),
        ]
        output = [report]
        status, reason, metadata = reduce_dependencies(dependencies, output)
        return Result(
            status=status,
            items=output,
            reason=reason,
            metadata={**metadata, "video_failures": failures},
        )

    def to_markdown(self, report):
        """Render a Result or report dict without converting unknowns to zero."""
        envelope = report if isinstance(report, Result) else Result(status="ok", items=[report])
        if not envelope.items:
            return f"# Report unavailable\n\nStatus: {envelope.status}\n\n{envelope.reason}"
        data = envelope.items[0]
        lines = []
        if envelope.status == "partial":
            lines += ["> **WARNING: PARTIAL REPORT**", f"> {envelope.reason}", ""]
        if data.get("report_type") == "competitor":
            channel = data.get("channel", {})
            lines += [
                f"# Competitor Report: {channel.get('name') or 'unknown'}",
                f"- Collection: {data.get('collection_status', 'unknown')}",
                f"- Subscribers: {self._fmt(channel.get('subscriber_count'))}",
                "",
                "## Videos",
            ]
            for row in data.get("videos", []):
                lines += [
                    f"### {row.get('title') or 'unknown'}",
                    f"- Views: {self._fmt(row.get('view_count'))}",
                    f"- VPH: {self._metric(row.get('vph'))}",
                    f"- Outlier: {self._metric(row.get('outlier'))}",
                ]
            lines += ["", f"Tracking: {self._result_metric(data.get('tracking'))}"]
        else:
            signals = data.get("keyword_signals", {})
            lines += [
                f"# Keyword Report: {data.get('keyword', '')}",
                f"- Collection: {data.get('collection_status', 'unknown')}",
                f"- Average views: {self._fmt(data.get('avg_views'))}",
                f"- Competition: {self._fmt(signals.get('competition_score'))}",
                f"- Competition status: {signals.get('calibration_status', 'unavailable')}",
                f"- Demand: {self._fmt(signals.get('demand'))}",
                f"- Reason: {signals.get('reason', '')}",
            ]
        return "\n".join(lines)

    @staticmethod
    def _fmt(value):
        return "unavailable" if value is None else str(value)

    @staticmethod
    def _metric(value):
        if not isinstance(value, dict):
            return "unavailable"
        if value.get("status") != "ok":
            return f"{value.get('status', 'unavailable')}: {value.get('reason', '')}"
        return str(value.get("vph", value.get("median_multiple", "observed")))

    @staticmethod
    def _result_metric(value):
        if not isinstance(value, dict):
            return "unavailable"
        return f"{value.get('status', 'unavailable')}: {value.get('reason', '')}"
