"""Typed, drift-aware parsers for supported InnerTube response surfaces."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

from .models import CanonicalVideo, ParseDiagnostics, ParsedPage, ParsedValue

KNOWN_VIDEO_RENDERERS = {
    "videoRenderer",
    "compactVideoRenderer",
    "gridVideoRenderer",
    "lockupViewModel",
}
WRAPPER_RENDERERS = {
    "itemSectionRenderer",
    "richItemRenderer",
    "continuationItemRenderer",
}


def extract_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, Mapping):
        return ""
    simple = value.get("simpleText")
    if isinstance(simple, str):
        return simple
    content = value.get("content")
    if isinstance(content, str):
        return content
    runs = value.get("runs")
    if isinstance(runs, list):
        return "".join(
            run.get("text", "")
            for run in runs
            if isinstance(run, Mapping) and isinstance(run.get("text", ""), str)
        )
    return ""


def parse_count(value: Any) -> ParsedValue[int]:
    raw = extract_text(value) if not isinstance(value, str) else value
    if not raw:
        return ParsedValue(None, "", "missing")
    text = unicodedata.normalize("NFKC", raw).casefold()
    text = text.replace("\u00a0", " ").replace("\u202f", " ")
    if any(word in text for word in ("hidden", "ẩn")):
        return ParsedValue(None, raw, "hidden")
    text = re.sub(r"\b(views?|subscribers?|lượt xem|người đăng ký|no views?)\b", "", text).strip()
    suffixes = {
        "k": 1_000,
        "n": 1_000,
        "nghìn": 1_000,
        "m": 1_000_000,
        "tr": 1_000_000,
        "triệu": 1_000_000,
        "b": 1_000_000_000,
        "t": 1_000_000_000,
        "tỷ": 1_000_000_000,
    }
    match = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*(k|n|nghìn|m|tr|triệu|b|t|tỷ)?\s*", text)
    if not match:
        plain = re.sub(r"[\s.,]", "", text)
        if not plain.isdigit():
            return ParsedValue(None, raw, "invalid")
        return ParsedValue(int(plain), raw, "parsed")
    number_text = match.group(1)
    suffix = match.group(2)
    if suffix is None and re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", number_text):
        return ParsedValue(int(re.sub(r"[.,]", "", number_text)), raw, "parsed")
    number = float(number_text.replace(",", "."))
    return ParsedValue(round(number * suffixes.get(suffix, 1)), raw, "parsed")


def _parse_count(value: Any) -> int | None:
    return parse_count(value).value


def parse_duration(value: Any) -> ParsedValue[int]:
    raw = extract_text(value) if not isinstance(value, str) else value
    if not raw:
        return ParsedValue(None, "", "missing")
    normalized = unicodedata.normalize("NFKC", raw).casefold()
    live = any(word in normalized for word in ("live", "trực tiếp"))
    upcoming = any(word in normalized for word in ("upcoming", "premiere", "sắp"))
    if live:
        return ParsedValue(None, raw, "live")
    if upcoming:
        return ParsedValue(None, raw, "upcoming")
    if ":" in normalized:
        parts = normalized.strip().split(":")
        if len(parts) not in (2, 3) or not all(part.isdigit() for part in parts):
            return ParsedValue(None, raw, "invalid")
        numbers = [int(part) for part in parts]
        if numbers[-1] > 59 or (len(numbers) == 3 and numbers[-2] > 59):
            return ParsedValue(None, raw, "invalid")
        seconds = numbers[-1] + numbers[-2] * 60
        if len(numbers) == 3:
            seconds += numbers[0] * 3600
    else:
        units = {
            "hour": 3600,
            "hours": 3600,
            "giờ": 3600,
            "minute": 60,
            "minutes": 60,
            "phút": 60,
            "second": 1,
            "seconds": 1,
            "giây": 1,
        }
        found = re.findall(r"(\d+)\s*(hours?|giờ|minutes?|phút|seconds?|giây)", normalized)
        seconds = sum(int(number) * units[unit] for number, unit in found)
        if not found:
            return ParsedValue(None, raw, "invalid")
    return ParsedValue(seconds, raw, "parsed") if seconds > 0 else ParsedValue(None, raw, "invalid")


def _parse_duration(value: Any) -> int | None:
    return parse_duration(value).value


def _extract_owner(owner: Any) -> tuple[str, str | None]:
    name = extract_text(owner)
    channel_id = None
    if isinstance(owner, Mapping) and isinstance(owner.get("runs"), list):
        for run in owner["runs"]:
            if isinstance(run, Mapping):
                candidate = (
                    run.get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId")
                )
                if candidate:
                    channel_id = candidate
                    break
    return name, channel_id


def _canonical(
    video_id: Any,
    title: str,
    channel_id: str | None,
    channel: str,
    views_raw: str,
    duration_raw: str,
    published_raw: str,
    badges: Iterable[str] = (),
) -> dict[str, Any] | None:
    if not isinstance(video_id, str) or not video_id:
        return None
    badge_text = " ".join(badges).casefold()
    is_live = any(word in badge_text for word in ("live", "trực tiếp"))
    is_upcoming = any(word in badge_text for word in ("upcoming", "premiere", "sắp"))
    duration = parse_duration(duration_raw or badge_text)
    return CanonicalVideo(
        video_id=video_id,
        channel_id=channel_id,
        title=title,
        view_count=parse_count(views_raw).value,
        duration_seconds=duration.value,
        publish_date=None,
        published_raw=published_raw,
        duration_raw=duration_raw,
        is_live=is_live or duration.status == "live",
        is_upcoming=is_upcoming or duration.status == "upcoming",
        extra={"channel": channel, "views_raw": views_raw},
    ).to_dict()


def parse_video_renderer(
    renderer: Mapping[str, Any], surface: str = "search"
) -> dict[str, Any] | None:
    owner = renderer.get("ownerText") or renderer.get("shortBylineText") or {}
    channel, channel_id = _extract_owner(owner)
    badges = [
        extract_text(badge.get("metadataBadgeRenderer", {}).get("label", ""))
        for badge in renderer.get("badges", [])
        if isinstance(badge, Mapping)
    ]
    return _canonical(
        renderer.get("videoId"),
        extract_text(renderer.get("title")),
        channel_id,
        channel,
        extract_text(renderer.get("viewCountText")),
        extract_text(renderer.get("lengthText")),
        extract_text(renderer.get("publishedTimeText")),
        badges,
    )


def parse_compact_video(renderer: Mapping[str, Any]) -> dict[str, Any] | None:
    return parse_video_renderer(renderer, "suggested")


def parse_lockup_video(
    renderer: Mapping[str, Any], known_channel_id: str | None = None
) -> dict[str, Any] | None:
    if renderer.get("contentType") not in ("", None, "LOCKUP_CONTENT_TYPE_VIDEO"):
        return None
    metadata = renderer.get("metadata", {}).get("lockupMetadataViewModel", {})
    if not isinstance(metadata, Mapping):
        metadata = {}
    labels: list[str] = []
    rows = metadata.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", [])
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        for part in row.get("metadataParts", []):
            if isinstance(part, Mapping):
                labels.append(
                    str(
                        part.get("accessibilityLabel")
                        or part.get("text", {}).get("accessibilityLabel")
                        or extract_text(part.get("text"))
                    )
                )
    views_raw = next((label for label in labels if re.search(r"views?|lượt xem", label, re.I)), "")
    published_raw = next(
        (
            label
            for label in labels
            if re.search(r"ago|trước|day|week|month|year|ngày|tuần|tháng|năm", label, re.I)
        ),
        "",
    )
    channel = next((label for label in labels if label not in {views_raw, published_raw}), "")
    overlays = renderer.get("contentImage", {}).get("thumbnailViewModel", {}).get("overlays", [])
    badge_texts: list[str] = []
    for overlay in overlays if isinstance(overlays, list) else []:
        if not isinstance(overlay, Mapping):
            continue
        badges = overlay.get("thumbnailBottomOverlayViewModel", {}).get("badges", [])
        for badge in badges:
            if isinstance(badge, Mapping):
                vm = badge.get("thumbnailBadgeViewModel", {})
                badge_texts.append(
                    str(
                        vm.get("text")
                        or vm.get("rendererContext", {})
                        .get("accessibilityContext", {})
                        .get("label", "")
                    )
                )
    duration_raw = next((text for text in badge_texts if ":" in text), "")
    channel_id = known_channel_id
    if not channel_id:
        channel_id = (
            metadata.get("image", {})
            .get("decoratedAvatarViewModel", {})
            .get("rendererContext", {})
            .get("commandContext", {})
            .get("onTap", {})
            .get("innertubeCommand", {})
            .get("browseEndpoint", {})
            .get("browseId")
        )
    video_id = renderer.get("contentId")
    if not video_id:
        video_id = (
            renderer.get("rendererContext", {})
            .get("commandContext", {})
            .get("onTap", {})
            .get("innertubeCommand", {})
            .get("watchEndpoint", {})
            .get("videoId")
        )
    return _canonical(
        video_id,
        extract_text(metadata.get("title")),
        channel_id,
        channel,
        views_raw,
        duration_raw,
        published_raw,
        badge_texts,
    )


def parse_any_video(
    node: Any, surface: str = "search", known_channel_id: str | None = None
) -> dict[str, Any] | None:
    if not isinstance(node, Mapping):
        return None
    if "lockupViewModel" in node and isinstance(node["lockupViewModel"], Mapping):
        return parse_lockup_video(node["lockupViewModel"], known_channel_id)
    if "videoRenderer" in node and isinstance(node["videoRenderer"], Mapping):
        return parse_video_renderer(node["videoRenderer"], surface)
    if "compactVideoRenderer" in node and isinstance(node["compactVideoRenderer"], Mapping):
        return parse_compact_video(node["compactVideoRenderer"])
    if "gridVideoRenderer" in node and isinstance(node["gridVideoRenderer"], Mapping):
        return parse_video_renderer(node["gridVideoRenderer"], surface)
    return None


def _shape_fingerprint(data: Any) -> tuple[str, bool]:
    paths: list[str] = []
    nodes = 0
    truncated = False

    def walk(value: Any, path: str, depth: int) -> None:
        nonlocal nodes, truncated
        if depth > 12 or nodes >= 2_000:
            truncated = True
            return
        nodes += 1
        if isinstance(value, Mapping):
            for key in sorted(str(key) for key in value):
                paths.append(f"{path}.{key}")
                walk(value[key], f"{path}.{key}", depth + 1)
        elif isinstance(value, list):
            paths.append(f"{path}[]")
            for child in value:
                walk(child, f"{path}[]", depth + 1)
        else:
            paths.append(f"{path}:{type(value).__name__}")

    walk(data, "$", 0)
    digest = hashlib.sha256("\n".join(sorted(paths)).encode()).hexdigest()[:16]
    return digest, truncated


def shape_fingerprint(data: Any) -> tuple[str, bool]:
    """Return the stable redacted structural fingerprint used in diagnostics."""
    return _shape_fingerprint(data)


def continuation_items(data: Mapping[str, Any]) -> list[Any]:
    for container in ("onResponseReceivedCommands", "onResponseReceivedActions"):
        entries = data.get(container)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            action = entry.get("appendContinuationItemsAction") or entry.get(
                "reloadContinuationItemsCommand"
            )
            if isinstance(action, Mapping) and isinstance(action.get("continuationItems"), list):
                return list(action["continuationItems"])
    return []


def _find_container(
    data: Mapping[str, Any], surface: str
) -> tuple[bool, str | None, list[Any], str]:
    continuation = continuation_items(data)
    if continuation or any(
        key in data for key in ("onResponseReceivedCommands", "onResponseReceivedActions")
    ):
        return True, "onResponseReceived*.continuationItems", continuation, "continuation"
    paths: dict[str, tuple[str, ...]] = {
        "search": (
            "contents",
            "twoColumnSearchResultsRenderer",
            "primaryContents",
            "sectionListRenderer",
            "contents",
        ),
        "channel_videos": ("contents", "twoColumnBrowseResultsRenderer", "tabs"),
        "trending": ("contents", "twoColumnBrowseResultsRenderer", "tabs"),
        "suggested": (
            "contents",
            "twoColumnWatchNextResults",
            "secondaryResults",
            "secondaryResults",
            "results",
        ),
        "browse": ("contents", "twoColumnBrowseResultsRenderer", "tabs"),
    }
    path = paths.get(surface)
    if not path:
        return False, None, [], "entity"
    current: Any = data
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return False, None, [], "initial"
        current = current[key]
    if surface in {"channel_videos", "trending", "browse"}:
        if not isinstance(current, list):
            return False, ".".join(path), [], "initial"
        selected = next(
            (
                tab.get("tabRenderer", {}).get("content", {})
                for tab in current
                if isinstance(tab, Mapping) and tab.get("tabRenderer", {}).get("selected")
            ),
            None,
        )
        if not isinstance(selected, Mapping):
            return False, ".".join(path), [], "initial"
        grid = selected.get("richGridRenderer", {})
        if not isinstance(grid, Mapping) or not isinstance(grid.get("contents"), list):
            return False, ".".join(path), [], "initial"
        return (
            True,
            ".".join(path) + "[selected].content.richGridRenderer.contents",
            grid["contents"],
            "initial",
        )
    return (
        isinstance(current, list),
        ".".join(path),
        current if isinstance(current, list) else [],
        "initial",
    )


def iter_video_nodes(items: Iterable[Any]) -> Iterable[Any]:
    for item in items:
        if not isinstance(item, Mapping):
            yield item
            continue
        section = item.get("itemSectionRenderer")
        if isinstance(section, Mapping):
            yield from iter_video_nodes(section.get("contents", []))
        elif isinstance(item.get("richItemRenderer"), Mapping):
            yield item["richItemRenderer"].get("content", {})
        else:
            yield item


def continuation_token_from_items(items: Iterable[Any]) -> str | None:
    for item in items:
        if not isinstance(item, Mapping):
            continue
        token = (
            item.get("continuationItemRenderer", {})
            .get("continuationEndpoint", {})
            .get("continuationCommand", {})
            .get("token")
        )
        if isinstance(token, str) and token:
            return token
    return None


def parse_video_page(
    data: Mapping[str, Any],
    *,
    surface: str,
    known_channel_id: str | None = None,
) -> ParsedPage:
    found, path, raw_items, kind = _find_container(data, surface)
    nodes = list(iter_video_nodes(raw_items))
    items: list[dict[str, Any]] = []
    invalid = 0
    unknown: set[str] = set()
    candidates = 0
    for node in nodes:
        if not isinstance(node, Mapping):
            invalid += 1
            candidates += 1
            continue
        keys = set(node)
        if "continuationItemRenderer" in keys:
            continue
        candidates += 1
        parsed = parse_any_video(node, surface, known_channel_id)
        if parsed:
            items.append(parsed)
        elif keys & KNOWN_VIDEO_RENDERERS:
            invalid += 1
        else:
            unknown.update(
                key
                for key in keys
                if key.endswith(("Renderer", "ViewModel")) and key not in WRAPPER_RENDERERS
            )
    token = continuation_token_from_items(nodes)
    fingerprint, truncated = _shape_fingerprint(data)
    diagnostics = ParseDiagnostics(
        surface=surface,
        response_kind=kind,  # type: ignore[arg-type]
        recognized_container=found,
        container_path=path,
        candidate_nodes=candidates,
        parsed_nodes=len(items),
        invalid_nodes=invalid,
        unknown_renderer_types=tuple(sorted(unknown)),
        continuation_token_present=bool(token),
        shape_fingerprint=fingerprint,
    )
    return ParsedPage(items, token, diagnostics, truncated)


def initial_search_items(data: Mapping[str, Any]) -> list[Any]:
    return _find_container(data, "search")[2]


def initial_channel_video_items(data: Mapping[str, Any]) -> list[Any]:
    return _find_container(data, "channel_videos")[2]


def extract_continuation_token(data: Mapping[str, Any]) -> str | None:
    return continuation_token_from_items(continuation_items(data))
