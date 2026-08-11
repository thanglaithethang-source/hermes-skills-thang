"""
Channel module — channel info, subscriber count, video list, stats.
"""

import re

from .client_profile import KNOWN_GOOD_PROFILE
from .innertube import InnerTubeClient
from .pagination import collect_pages
from .parsers import (
    extract_text,
    parse_lockup_video,
    parse_video_page,
    shape_fingerprint,
)
from .parsers import (
    parse_count as _central_parse_count,
)
from .result import Result
from .validation import (
    ValidationError,
    validate_channel_id,
    validate_handle,
    validate_int_range,
)


def parse_subscriber_count(value):
    return _central_parse_count(value).value


class ChannelModule:
    """Channel info, subscriber count, video list, aggregate stats."""

    def __init__(self, client=None):
        self.client = client or InnerTubeClient()

    def channel_info(self, channel_id_or_handle):
        """
        Get channel info by channel ID (UC...) or handle (@name).
        Returns: name, subscriber_count, subscriber_raw, total_views, video_count,
                 description, country, joined_date, channel_id
        """
        try:
            channel_id_or_handle = (
                validate_handle(channel_id_or_handle)
                if isinstance(channel_id_or_handle, str) and channel_id_or_handle.startswith("@")
                else validate_channel_id(channel_id_or_handle)
            )
        except ValidationError as exc:
            return Result.error(str(exc), exc.code, metadata={"field": exc.field})
        # Determine if it's a handle or channel ID
        if channel_id_or_handle.startswith("@") or not channel_id_or_handle.startswith("UC"):
            # Handle — use browse with handle
            browse_id = None
            if channel_id_or_handle.startswith("@"):
                # @handle → browse with params
                # Encode handle
                browse_id = None
                # Use the channel page URL approach
                return self._channel_info_from_page(channel_id_or_handle)
            else:
                browse_id = channel_id_or_handle
        else:
            browse_id = channel_id_or_handle

        data = self.client.browse(browse_id=browse_id)
        if data.get("_error"):
            return Result.error(data.get("_message", "Unknown error"), data.get("_status"))

        item = self._parse_channel_browse(data, browse_id)
        recognized = any(
            key in data.get("header", {})
            for key in ("pageHeaderRenderer", "c4TabbedHeaderRenderer")
        ) or "channelMetadataRenderer" in data.get("metadata", {})
        fingerprint, truncated = shape_fingerprint(data)
        diagnostic = {
            "surface": "channel_info",
            "response_kind": "entity",
            "recognized_container": recognized,
            "container_path": "header|metadata" if recognized else None,
            "candidate_nodes": 1 if recognized else 0,
            "parsed_nodes": 1 if item.get("channel_id") and item.get("name") else 0,
            "invalid_nodes": 1
            if recognized and not (item.get("channel_id") and item.get("name"))
            else 0,
            "unknown_renderer_types": [],
            "continuation_token_present": False,
            "shape_fingerprint": fingerprint,
        }
        if truncated:
            diagnostic["fingerprint_truncated"] = True
        if not recognized or not item.get("channel_id") or not item.get("name"):
            return Result.unsupported(
                "Channel identity response format is unsupported",
                metadata={"parser_diagnostics": [diagnostic]},
            )
        return Result(
            status="ok",
            items=[item],
            metadata={"parser_diagnostics": [diagnostic]},
        )

    def _channel_info_from_page(self, handle):
        """Get channel info by scraping channel page (for @handles)."""
        url = f"https://www.youtube.com/{handle}"
        try:
            resp = self.client._get(url)
            if not isinstance(resp, dict) or resp.get("_error"):
                return Result.error(
                    resp.get("_message", "Failed to fetch channel page")
                    if isinstance(resp, dict)
                    else "Failed to fetch channel page",
                    resp.get("_status") if isinstance(resp, dict) else None,
                )
            html = resp["text"]
        except Exception as e:
            return Result.error(f"Channel page fetch failed: {e}")

        # Extract channel ID from page
        channel_id = ""
        m = re.search(r'"channelId":"(UC[^"]+)"', html)
        if m:
            channel_id = m.group(1)
        if not channel_id:
            m = re.search(
                r'canonical"/>\s*<link[^>]*href="https://www.youtube.com/channel/(UC[^"]+)"', html
            )
            if m:
                channel_id = m.group(1)

        if not channel_id:
            return Result.error("Could not find channel ID from handle")

        # Now use browse API with channel ID
        data = self.client.browse(browse_id=channel_id)
        if data.get("_error"):
            return Result.error(data.get("_message", "Unknown error"), data.get("_status"))

        return Result(status="ok", items=[self._parse_channel_browse(data, channel_id)])

    def _parse_channel_browse(self, data, channel_id):
        """Parse browse API response for channel info."""
        result = {
            "channel_id": channel_id,
            "name": "",
            "subscriber_count": None,
            "subscriber_raw": "",
            "video_count": 0,
            "video_count_raw": "",
            "description": "",
            "country": "",
            "tags": [],
            # Note: total_views and joined_date are NOT available from InnerTube browse.
            # They require YouTube Data API v3 channels.list endpoint.
        }

        header = data.get("header", {})

        # === NEW FORMAT: pageHeaderRenderer with pageHeaderViewModel ===
        if "pageHeaderRenderer" in header:
            phr = header["pageHeaderRenderer"]
            content = phr.get("content", {})
            view_model = content.get("pageHeaderViewModel", {})

            # Channel name
            title_vm = view_model.get("title", {})
            if "dynamicTextViewModel" in title_vm:
                result["name"] = title_vm["dynamicTextViewModel"].get("text", {}).get("content", "")
            elif "content" in title_vm:
                result["name"] = title_vm["content"]

            # Subscriber count + video count from metadata
            metadata = view_model.get("metadata", {})
            cmv = metadata.get("contentMetadataViewModel", {})
            metadata_rows = cmv.get("metadataRows", [])
            for row in metadata_rows:
                parts = row.get("metadataParts", [])
                for part in parts:
                    text_obj = part.get("text", {})
                    content_text = text_obj.get("content", "")

                    # Check for subscriber count
                    if "người đăng ký" in content_text or "subscriber" in content_text.lower():
                        result["subscriber_raw"] = content_text
                        result["subscriber_count"] = parse_subscriber_count(content_text)
                    # Check for video count
                    if "video" in content_text.lower():
                        result["video_count_raw"] = content_text
                        m = re.search(r"([\d.,]+)\s*video", content_text.lower())
                        if m:
                            result["video_count"] = int(
                                m.group(1).replace(",", "").replace(".", "")
                            )

        # === OLD FORMAT: c4TabbedHeaderRenderer (fallback) ===
        if "c4TabbedHeaderRenderer" in header:
            hdr = header["c4TabbedHeaderRenderer"]
            if not result["name"]:
                result["name"] = hdr.get("title", "")
            sub_text = hdr.get("subscriberCountText", {})
            sub_raw = extract_text(sub_text)
            if sub_raw and not result["subscriber_raw"]:
                result["subscriber_raw"] = sub_raw
                result["subscriber_count"] = parse_subscriber_count(sub_raw)

        # === Channel metadata ===
        metadata = data.get("metadata", {})
        if "channelMetadataRenderer" in metadata:
            cmr = metadata["channelMetadataRenderer"]
            if not result["name"]:
                result["name"] = cmr.get("title", "")
            result["description"] = cmr.get("description", "")
            result["country"] = cmr.get("country", "") or cmr.get("regionCode", "")
            result["channel_id"] = cmr.get("externalId", channel_id)
            keywords = cmr.get("keywords", "")
            if keywords:
                result["tags"] = [k.strip() for k in keywords.split(",") if k.strip()]

        # === Video count from tabs (fallback if not in header) ===
        if not result["video_count"]:
            contents = data.get("contents", {})
            two_col = contents.get("twoColumnBrowseResultsRenderer", {})
            tabs = two_col.get("tabs", [])
            for tab in tabs:
                tab_renderer = tab.get("tabRenderer", {})
                tab_title = tab_renderer.get("title", "")
                if tab_title in ("Videos", "Home", "Trang chủ", "Video"):
                    content = tab_renderer.get("content", {})
                    rich_grid = content.get("richGridRenderer", {})
                    header_rg = rich_grid.get("header", {})
                    if header_rg:
                        feed_filter = header_rg.get("feedFilterChipBarRenderer", {})
                        chips = feed_filter.get("contents", [])
                        for chip in chips:
                            chip_renderer = chip.get("chipCloudChipRenderer", {})
                            text = extract_text(chip_renderer.get("text"))
                            m = re.search(r"([\d.,]+)\s*video", text.lower())
                            if m:
                                result["video_count_raw"] = text
                                result["video_count"] = int(
                                    m.group(1).replace(",", "").replace(".", "")
                                )
                                break

        return result

    def channel_videos(self, channel_id, limit=30, max_pages=20):
        """
        Get list of recent videos from a channel. Supports pagination.
        Returns Result envelope with items + pagination metadata.
        """
        try:
            channel_id = validate_channel_id(channel_id)
            limit = validate_int_range(limit, "limit", 1, 100)
            max_pages = validate_int_range(max_pages, "max_pages", 1, 50)
        except ValidationError as exc:
            return Result.error(str(exc), exc.code, metadata={"field": exc.field})
        params = KNOWN_GOOD_PROFILE.channel_videos_params
        return collect_pages(
            lambda continuation: (
                self.client.browse(continuation=continuation)
                if continuation
                else self.client.browse(browse_id=channel_id, params=params)
            ),
            lambda data: parse_video_page(
                data, surface="channel_videos", known_channel_id=channel_id
            ),
            limit=limit,
            max_pages=max_pages,
            identity=lambda row: row.get("video_id"),
        )

    def _parse_channel_videos_page(self, data, channel_id):
        """Parse a single channel videos page (initial or continuation)."""
        page = parse_video_page(data, surface="channel_videos", known_channel_id=channel_id)
        return page.items, page.continuation_token

    def _parse_lockup_view_model(self, lvm, known_channel_id=None):
        """Parse lockupViewModel using centralized parser."""
        return parse_lockup_video(lvm, known_channel_id=known_channel_id)

    def channel_stats(self, channel_id):
        """
        Get aggregate channel stats: subscriber count, video count,
        avg views, median views, max views, upload frequency estimate.
        """
        info = self.channel_info(channel_id)
        if not info.ok:
            return info
        info_item = info.items[0]

        videos_result = self.channel_videos(channel_id, limit=30)
        if videos_result.status in {"error", "unsupported"}:
            return videos_result
        videos = videos_result.items

        views_list = [
            v["views"]
            for v in videos
            if v.get("views") is not None and isinstance(v.get("views"), int)
        ]
        if views_list:
            import statistics as stats_mod

            avg_views = sum(views_list) // len(views_list)
            median_views = stats_mod.median(views_list)
            max_views = max(views_list)
        else:
            avg_views = median_views = max_views = None

        item = {
            **info_item,
            "videos": videos,
            "video_count_sample": len(videos),
            "avg_views": avg_views,
            "median_views": median_views,
            "max_views": max_views,
        }
        no_sample = not videos
        return Result(
            status="partial" if videos_result.partial or no_sample else "ok",
            items=[item],
            reason=("No analyzable video sample" if no_sample else videos_result.reason),
            metadata={"upstream": videos_result.metadata},
        )
