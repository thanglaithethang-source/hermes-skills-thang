"""Public facade for drift-aware YouTube research."""

from .analytics_estimate import AnalyticsEstimateModule
from .browse_suggested import BrowseSuggestedModule
from .channel import ChannelModule
from .enrichment import PublishDateEnricher
from .innertube import InnerTubeClient
from .report import ReportModule
from .result import Result
from .search import SearchModule
from .storage import Storage
from .tracking import TrackingModule
from .video import VideoModule


class YouTubeResearch:
    """Collect public observations and run explicitly labeled analytics."""

    def __init__(self, context_path=None, authenticated=False, db_path=None):
        self.client = InnerTubeClient(context_path, authenticated=authenticated)
        self.storage = Storage(db_path) if db_path else None
        self.search_mod = SearchModule(self.client)
        self.channel_mod = ChannelModule(self.client)
        self.video_mod = VideoModule(self.client)
        self.analytics_mod = AnalyticsEstimateModule(self.client, self.storage)
        self.publish_date_enricher = PublishDateEnricher(self.client)
        self.browse_mod = BrowseSuggestedModule(self.client)
        self.report_mod = ReportModule(self.client, storage=self.storage)
        self.tracking_mod = TrackingModule(
            self.channel_mod,
            self.video_mod,
            self.search_mod,
            self.analytics_mod,
            self.storage,
        )
        self.report_mod.tracking_mod = self.tracking_mod

    # === Search ===
    def search(self, query, limit=20, filter_sort=None):
        """Search YouTube videos. filter_sort: None, 'views', 'date'."""
        return self.search_mod.search(query, limit=limit, filter_sort=filter_sort)

    def search_suggestions(self, prefix, limit=20):
        """Get autocomplete suggestions."""
        return self.search_mod.search_suggestions(prefix, limit=limit)

    def trending(self, region="VN", limit=30):
        """Get trending videos."""
        return self.search_mod.trending(region=region, limit=limit)

    # === Channel ===
    def channel_info(self, channel_id_or_handle):
        """Get channel info by ID (UC...) or handle (@name)."""
        return self.channel_mod.channel_info(channel_id_or_handle)

    def channel_videos(self, channel_id, limit=30):
        """Get recent videos from a channel."""
        return self.channel_mod.channel_videos(channel_id, limit=limit)

    def channel_stats(self, channel_id):
        """Get aggregate channel stats."""
        return self.channel_mod.channel_stats(channel_id)

    # === Video ===
    def video_info(self, video_id):
        """Get video metadata."""
        return self.video_mod.video_info(video_id)

    def video_batch(self, video_ids):
        """Get info for multiple videos."""
        return self.video_mod.video_batch(video_ids)

    # === Public proxies and scenarios ===
    def estimate_ctr(self, video_info, search_position=None):
        """Return ``estimable=False`` and observable CTR-related public proxies."""
        return self.analytics_mod.estimate_ctr(video_info, search_position)

    def estimate_retention(self, video_info):
        """Return ``estimable=False`` and observable retention-related public proxies."""
        return self.analytics_mod.estimate_retention(video_info)

    def estimate_rpm(
        self,
        video_info,
        channel_info=None,
        niche=None,
        scenario_profile=None,
        scenario_override=None,
    ):
        """Return ``estimable=False`` with an explicitly selected RPM scenario."""
        return self.analytics_mod.estimate_rpm(
            video_info,
            channel_info,
            niche,
            scenario_profile,
            scenario_override,
        )

    def detect_niche(self, video_info, channel_info=None):
        """Detect niche from video/channel metadata."""
        return self.analytics_mod.detect_niche(video_info, channel_info)

    # === Browse/Suggested ===
    def suggested_for(self, video_id, limit=20):
        """Get suggested/related videos for a video."""
        return self.browse_mod.suggested_for(video_id, limit=limit)

    def find_in_suggested(self, video_id, target_channel_id=None, target_video_id=None, limit=50):
        """Check if target appears in suggested list of a video."""
        return self.browse_mod.find_in_suggested(
            video_id, target_channel_id, target_video_id, limit
        )

    def browse_feed_sample(self, limit=30):
        """Sample the YouTube browse feed."""
        return self.browse_mod.browse_feed_sample(limit=limit)

    def check_browse_presence(self, channel_id, limit=30):
        """Check if channel appears in browse feed."""
        return self.browse_mod.check_browse_presence(channel_id, limit=limit)

    # === Reports ===
    def competitor_report(self, channel_id_or_handle, video_limit=10):
        """Build a dependency-aware competitor report from public observations."""
        return self.report_mod.competitor_report(channel_id_or_handle, video_limit)

    def keyword_report(self, keyword, limit=20):
        """Build a dependency-aware keyword report from public observations."""
        return self.report_mod.keyword_report(keyword, limit=limit)

    def to_markdown(self, report):
        """Convert report to markdown."""
        return self.report_mod.to_markdown(report)

    # === Utility ===
    def refresh_context(self):
        """Reload context/cookies from file."""
        self.client.refresh_context()

    # === VPH + Outlier + Keyword Competition ===
    def snapshot_video(self, video_id, **kwargs):
        """Low-level manual snapshot insertion. Prefer snapshot_video_live()."""
        if not self.storage:
            return Result.error("No storage configured", "storage_unavailable")
        self.storage.snapshot_video(video_id, **kwargs)
        return Result(status="ok", items=[{"video_id": video_id}])

    def snapshot_channel(self, channel_id, **kwargs):
        """Low-level manual snapshot insertion. Prefer snapshot_channel_live()."""
        if not self.storage:
            return Result.error("No storage configured", "storage_unavailable")
        self.storage.snapshot_channel(channel_id, **kwargs)
        return Result(status="ok", items=[{"channel_id": channel_id}])

    def snapshot_video_live(self, video_id):
        return self.tracking_mod.snapshot_video_live(video_id)

    def snapshot_channel_live(self, channel_id_or_handle):
        return self.tracking_mod.snapshot_channel_live(channel_id_or_handle)

    def snapshot_keyword_live(self, keyword, limit=20):
        return self.tracking_mod.snapshot_keyword_live(keyword, limit=limit)

    def calculate_vph(self, video_id, window_hours=24, min_interval_minutes=15):
        """Calculate Views Per Hour from stored snapshots. Requires db_path."""
        return self.analytics_mod.calculate_vph(
            video_id,
            window_hours=window_hours,
            min_interval_minutes=min_interval_minutes,
        )

    def detect_outlier(
        self,
        video_info,
        channel_videos,
        as_of=None,
        *,
        performance_curve=None,
        enrich_publish_dates=True,
        max_enrichment_items=100,
    ):
        """Detect if a video overperforms vs channel baseline."""
        rows = [video_info, *channel_videos]
        enrichment = (
            self.publish_date_enricher.enrich(rows, max_items=max_enrichment_items)
            if enrich_publish_dates
            else Result(status="ok", items=rows)
        )
        enriched = enrichment.items or rows
        result = self.analytics_mod.detect_outlier(
            enriched[0],
            enriched[1:],
            as_of=as_of,
            performance_curve=performance_curve,
        )
        result["enrichment"] = enrichment.metadata
        if enrichment.partial and result.get("status") == "ok":
            result["status"] = "partial"
        return result

    def performance_curve(self, channel_id):
        """Return stored public performance-curve percentiles for a channel."""
        if not self.storage:
            return Result.error("No storage configured", "storage_unavailable")
        curve = self.storage.get_channel_performance_curve(channel_id)
        return Result.collection(items=curve, requested=len(curve))

    def compare_to_performance_curve(self, channel_id, current_views, age_hours):
        """Compare current views with the stored channel curve midpoint."""
        if not self.storage:
            return Result.error("No storage configured", "storage_unavailable")
        comparison = self.storage.compare_video_to_performance_curve(
            channel_id, current_views, age_hours
        )
        return Result(
            status="ok" if comparison else "empty",
            items=[comparison] if comparison else [],
            reason="" if comparison else "No usable performance curve",
        )

    def vidiq_score_client(self, views, facebook_likes=0):
        """Return the legacy formula, explicitly labeled as a client estimate."""
        return self.analytics_mod.vidiq_score_client(views, facebook_likes)

    def keyword_competition_signals(
        self,
        keyword,
        search_results,
        *,
        enrich_publish_dates=True,
        max_enrichment_items=100,
        **kwargs,
    ):
        enrichment = (
            self.publish_date_enricher.enrich(search_results, max_items=max_enrichment_items)
            if enrich_publish_dates
            else Result(status="ok", items=search_results)
        )
        result = self.analytics_mod.keyword_competition_signals(
            keyword, enrichment.items or search_results, **kwargs
        )
        result["enrichment"] = enrichment.metadata
        result["collection_status"] = "partial" if enrichment.partial else "ok"
        return result

    def keyword_competition_score(self, keyword, search_results, **kwargs):
        """Deprecated compatibility alias; score may be unavailable."""
        return self.analytics_mod.keyword_competition_score(keyword, search_results, **kwargs)

    def video_history(self, video_id, limit=100):
        if not self.storage:
            return Result.error("No storage configured", "storage_unavailable")
        return Result.collection(
            items=self.storage.get_video_snapshots(video_id, limit),
            requested=limit,
        )

    def channel_history(self, channel_id, limit=100):
        if not self.storage:
            return Result.error("No storage configured", "storage_unavailable")
        return Result.collection(
            items=self.storage.get_channel_snapshots(channel_id, limit),
            requested=limit,
        )

    def keyword_history(self, keyword, limit=100):
        if not self.storage:
            return Result.error("No storage configured", "storage_unavailable")
        return Result.collection(
            items=self.storage.get_keyword_snapshots(keyword, limit),
            requested=limit,
        )

    def competitor_tracking(self, channel_ids, interval_hours=168, refresh=True):
        if isinstance(channel_ids, str):
            channel_ids = [channel_ids]
        return self.tracking_mod.compare_competitors(
            channel_ids,
            interval_hours=interval_hours,
            refresh=refresh,
        )


def main():
    import argparse
    import json

    from .client_profile import KNOWN_GOOD_PROFILE

    parser = argparse.ArgumentParser()
    parser.add_argument("--show-profile", action="store_true")
    args = parser.parse_args()
    if args.show_profile:
        print(
            json.dumps(
                {
                    "profile_id": KNOWN_GOOD_PROFILE.profile_id,
                    "client_version": KNOWN_GOOD_PROFILE.context.client_version,
                    "locale": {
                        "hl": KNOWN_GOOD_PROFILE.context.hl,
                        "gl": KNOWN_GOOD_PROFILE.context.gl,
                    },
                    "parameter_names": {
                        "search_sort": sorted(KNOWN_GOOD_PROFILE.search_sort_params),
                        "browse": sorted(KNOWN_GOOD_PROFILE.browse_ids),
                    },
                },
                indent=2,
            )
        )
        return
    yt = YouTubeResearch()

    print("=== YouTube Research Skill ===")
    print("Testing search...")
    result = yt.search("AI automation", limit=5)
    print(f"{result.status}: {len(result.items)} items")
    if result.reason:
        print(result.reason)
    for video in result.items:
        print(video["title"])


if __name__ == "__main__":
    main()
