"""Public analytics signals and explicitly selected scenario assumptions."""

import json
import math
import re
import statistics
import unicodedata
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from numbers import Integral
from pathlib import Path

from .calibration import CalibrationRepository
from .formatting import classify_content_format
from .time_utils import parse_utc

AGE_BUCKETS_HOURS = (48, 24 * 7, 24 * 30, 24 * 90, 24 * 365)


def _reference_path(name):
    source_path = Path(__file__).parents[1] / "references" / name
    if source_path.exists():
        return source_path
    return Path(__file__).parent / "references" / name


def _video_observation(video, as_of):
    if not isinstance(video, Mapping):
        return None, "invalid_video"
    video_id = video.get("video_id") or video.get("videoId")
    views = video.get("view_count", video.get("views"))
    duration = video.get("duration_seconds")
    published = video.get("publish_date") or video.get("published_at")
    if isinstance(views, bool) or not isinstance(views, Integral) or views < 0:
        return None, "invalid_views"
    if isinstance(duration, bool) or not isinstance(duration, Integral) or duration <= 0:
        return None, "missing_duration"
    try:
        published_at = parse_utc(published)
    except (AttributeError, TypeError, ValueError):
        return None, "invalid_publish_date"
    age_hours = (as_of - published_at).total_seconds() / 3600
    if age_hours < 0:
        return None, "future_publish_date"
    age_bucket = next(
        (upper for upper in AGE_BUCKETS_HOURS if age_hours <= upper),
        float("inf"),
    )
    return {
        "video_id": video_id,
        "views": int(views),
        "duration_seconds": int(duration),
        "format": classify_content_format(duration, bool(video.get("is_live"))),
        "published_at": published_at,
        "age_hours": age_hours,
        "age_bucket_hours": age_bucket,
    }, None


def _tokens(text):
    return {
        token
        for token in re.findall(
            r"\w+",
            unicodedata.normalize("NFKC", text or "").casefold(),
            flags=re.UNICODE,
        )
        if len(token) > 1
    }


def _title_relevance(keyword, title):
    wanted = _tokens(keyword)
    if not wanted:
        return None
    return len(wanted & _tokens(title)) / len(wanted)


def _normalized_hhi(channel_ids):
    n = len(channel_ids)
    if n < 2:
        return None
    counts = {}
    for channel_id in channel_ids:
        counts[channel_id] = counts.get(channel_id, 0) + 1
    hhi = sum((count / n) ** 2 for count in counts.values())
    floor = 1 / n
    normalized = (hhi - floor) / (1 - floor)
    if abs(normalized) < 1e-12:
        return 0.0
    return max(0.0, min(1.0, normalized))


def vidiq_score_client(views, facebook_likes=0):
    """Return the legacy vidIQ client estimate, not the production score."""

    def term(value):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("score inputs must be finite numbers")
        return 0.0 if value < 1 else 3 * math.log2(value)

    return min(100, term(views) + term(facebook_likes))


def _select_curve_point(performance_curve, age_hours):
    points = {}
    for raw in performance_curve or []:
        if not isinstance(raw, Mapping):
            continue
        try:
            bucket = round(float(raw["age_hours"]))
            perc30 = float(raw["perc30"])
            perc70 = float(raw["perc70"])
        except (KeyError, TypeError, ValueError):
            continue
        if all(math.isfinite(value) and value >= 0 for value in (perc30, perc70)):
            points[bucket] = {**raw, "age_hours": bucket, "perc30": perc30, "perc70": perc70}
    if not points:
        return None
    exact_hour = round(age_hours)
    day_hour = round(age_hours / 24) * 24
    return (
        points.get(exact_hour)
        or points.get(day_hour)
        or (points.get(168) if age_hours <= 168 else None)
        or points[max(points)]
    )


def detect_niche(video_info, channel_info=None):
    """Detect niche from video/channel metadata."""
    text = ""
    if isinstance(video_info, Mapping):
        text += video_info.get("title", "") + " "
        text += video_info.get("description", "") + " "
        text += video_info.get("category", "") + " "
        for tag in video_info.get("tags") or []:
            if isinstance(tag, str):
                text += tag + " "
    if isinstance(channel_info, Mapping):
        text += channel_info.get("description", "") + " "
        text += channel_info.get("name", "") + " "
        for tag in channel_info.get("tags") or []:
            if isinstance(tag, str):
                text += tag + " "

    text_lower = text.lower()

    # Score each niche
    niche_scores = {}
    niche_keywords = {
        "finance": [
            "finance",
            "money",
            "invest",
            "stock",
            "crypto",
            "trading",
            "wealth",
            "rich",
            "budget",
            "passive income",
        ],
        "business": ["business", "entrepreneur", "startup", "marketing", "sales", "leadership"],
        "technology": ["tech", "technology", "gadget", "review", "smartphone", "laptop"],
        "software": ["software", "programming", "code", "developer", "python", "javascript", "api"],
        "ai": ["ai", "artificial intelligence", "machine learning", "gpt", "llm", "neural"],
        "education": ["education", "learn", "course", "study", "school", "university"],
        "science": ["science", "physics", "chemistry", "biology", "space", "universe"],
        "history": ["history", "ancient", "medieval", "war", "civilization", "empire"],
        "geography": ["geography", "country", "map", "world", "continent"],
        "gaming": ["game", "gaming", "gameplay", "walkthrough", "minecraft", "fortnite"],
        "entertainment": ["entertainment", "funny", "comedy", "prank", "challenge"],
        "music": ["music", "song", "album", "beat", "rap", "pop", "rock"],
        "lifestyle": ["lifestyle", "vlog", "daily", "routine", "day in"],
        "beauty": ["beauty", "makeup", "skincare", "cosmetic"],
        "food": ["food", "cooking", "recipe", "kitchen", "eat"],
        "travel": ["travel", "trip", "country", "city", "adventure"],
        "health": ["health", "medical", "doctor", "disease", "medicine"],
        "fitness": ["fitness", "workout", "gym", "exercise", "muscle", "diet"],
        "psychology": ["psychology", "mind", "behavior", "mental", "therapy", "stoic"],
        "true_crime": ["crime", "murder", "mystery", "investigation", "detective"],
        "paranormal": ["paranormal", "ghost", "haunted", "supernatural", "scary"],
        "documentary": ["documentary", "doc"],
        "news": ["news", "breaking", "report", "journalism"],
        "politics": ["politics", "government", "election", "president"],
    }

    for niche, keywords in niche_keywords.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            niche_scores[niche] = score

    if niche_scores:
        return max(niche_scores, key=niche_scores.get)

    return "default"


def estimate_ctr(video_info, search_position=None):
    """
    CTR is NOT estimable from public data (no impressions/clicks).
    Returns observable packaging/engagement proxies instead of fake CTR.
    """
    views = video_info.get("view_count") or 0
    likes = video_info.get("like_count")
    video_info.get("comment_count")
    title = video_info.get("title", "")

    proxies = {}

    # Engagement rate (like/view) — observable, not CTR
    if views > 0 and likes is not None and likes > 0:
        proxies["like_view_ratio"] = round(likes / views, 4)

    # Title features — observable packaging signals
    title_features = {}
    if title:
        title_features["has_number"] = bool(re.search(r"\d", title))
        title_features["has_question"] = "?" in title
        title_features["has_caps"] = any(w.isupper() and len(w) > 3 for w in title.split())
        title_features["length"] = len(title)
    proxies["title_features"] = title_features

    if search_position is not None:
        proxies["search_rank_snapshot"] = search_position

    return {
        "metric": "ctr",
        "estimable": False,
        "reason": (
            "Public data has no impressions or clicks. CTR is only visible "
            "to the channel owner in YouTube Studio."
        ),
        "observable_proxies": proxies,
    }


def estimate_retention(video_info):
    """
    Retention is NOT estimable from public data (no watch-time data).
    Returns observable engagement proxies instead.
    """
    views = video_info.get("view_count") or 0
    likes = video_info.get("like_count")
    comments = video_info.get("comment_count")
    duration = video_info.get("duration_seconds") or 0

    proxies = {}

    if views > 0 and likes is not None and likes > 0:
        proxies["like_view_ratio"] = round(likes / views, 4)
    if views > 0 and comments is not None and comments > 0:
        proxies["comment_view_ratio"] = round(comments / views, 4)
    if duration > 0:
        proxies["duration_seconds"] = duration
        proxies["duration_category"] = (
            "short" if duration < 300 else "medium" if duration < 1200 else "long"
        )

    return {
        "metric": "retention",
        "estimable": False,
        "reason": (
            "Audience retention requires watch-time data. Only the channel "
            "owner sees it in YouTube Studio."
        ),
        "observable_proxies": proxies,
    }


def _load_rpm_scenarios():
    path = _reference_path("rpm_scenarios.json")
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(artifact.get("version"), str) or not isinstance(
        artifact.get("profiles"), dict
    ):
        raise ValueError("invalid RPM scenario artifact")
    for name, profile in artifact["profiles"].items():
        required = {
            "currency",
            "geography_assumption",
            "effective_date",
            "uncertainty_range",
            "source_type",
            "source_url",
        }
        if not isinstance(profile, dict) or set(profile) != required:
            raise ValueError(f"invalid RPM scenario provenance: {name}")
    return artifact


def estimate_rpm(
    video_info,
    channel_info=None,
    niche=None,
    scenario_profile=None,
    scenario_override=None,
):
    """Return an explicit RPM scenario, never a public-data RPM estimate."""
    if niche is None:
        niche = detect_niche(video_info, channel_info)

    artifact = _load_rpm_scenarios()
    duration = video_info.get("duration_seconds") or 0
    content_format = classify_content_format(duration, bool(video_info.get("is_live")))
    format_type = (
        "shorts_feed"
        if content_format == "short"
        else "long_form_midroll_eligible"
        if duration > 600
        else "long_form_no_midroll_assumed"
        if content_format == "long_form"
        else "unknown"
    )

    selected = None
    if scenario_override is not None:
        if (
            not isinstance(scenario_override, (list, tuple))
            or len(scenario_override) != 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
                for value in scenario_override
            )
            or scenario_override[0] > scenario_override[1]
        ):
            raise ValueError("scenario_override must be a finite [low, high] range")
        selected = {
            "currency": "USD",
            "uncertainty_range": list(scenario_override),
            "source_type": "user_override",
        }
    elif scenario_profile is not None:
        if scenario_profile not in artifact["profiles"]:
            raise ValueError("unknown scenario_profile")
        selected = artifact["profiles"][scenario_profile]
    return {
        "metric": "rpm",
        "estimable": False,
        "reason": (
            "RPM depends on geography, ad format, monetization status, season, "
            "and rights. Only the channel owner sees it."
        ),
        "niche": niche,
        "content_format": content_format,
        "ad_inventory_scenario": format_type,
        "scenario_profile": scenario_profile,
        "scenario": selected,
        "available_scenarios": artifact["profiles"] if selected is None else None,
        "profile_version": artifact["version"],
        "missing_inputs": ["geography", "monetized playbacks", "rights", "season", "ypp_status"],
    }


class AnalyticsEstimateModule:
    """Public proxies, explicit scenarios, VPH, and comparable-cohort analytics."""

    def __init__(self, client=None, storage=None):
        self.client = client
        self.storage = storage

    def estimate_ctr(self, video_info, search_position=None):
        return estimate_ctr(video_info, search_position)

    def estimate_retention(self, video_info):
        return estimate_retention(video_info)

    def estimate_rpm(
        self,
        video_info,
        channel_info=None,
        niche=None,
        scenario_profile=None,
        scenario_override=None,
    ):
        return estimate_rpm(
            video_info,
            channel_info,
            niche,
            scenario_profile,
            scenario_override,
        )

    def detect_niche(self, video_info, channel_info=None):
        return detect_niche(video_info, channel_info)

    def calculate_vph(self, video_id, window_hours=24, min_interval_minutes=15, max_snapshots=100):
        if not self.storage:
            return {"status": "unavailable", "vph": None, "reason": "No storage configured"}
        if window_hours <= 0 or min_interval_minutes <= 0:
            raise ValueError("window_hours and min_interval_minutes must be positive")
        snapshots = self.storage.get_video_snapshots(video_id, limit=max_snapshots)
        valid = []
        invalid_observations = 0
        for row in snapshots:
            count = row.get("view_count")
            if isinstance(count, bool) or not isinstance(count, Integral) or count < 0:
                invalid_observations += 1
                continue
            try:
                observed_at = parse_utc(row["snapshot_at"])
            except (KeyError, TypeError, ValueError):
                invalid_observations += 1
                continue
            valid.append((observed_at, int(count), row))
        valid.sort(key=lambda item: item[0])
        if valid and (
            valid[-1][2].get("published_at") is not None
            or bool(valid[-1][2].get("is_live"))
        ):
            latest_at, current_views, latest_row = valid[-1]
            if bool(latest_row.get("is_live")):
                return {
                    "status": "unavailable",
                    "vph": None,
                    "reason": "Live streams do not use snapshot VPH",
                    "vph_method": None,
                }
            try:
                published_at = parse_utc(latest_row["published_at"])
            except (KeyError, TypeError, ValueError):
                published_at = None
            age_hours = (
                (latest_at - published_at).total_seconds() / 3600
                if published_at is not None
                else None
            )
            historical = [
                item
                for item in reversed(valid[:-1])
                if 12 <= (latest_at - item[0]).total_seconds() / 3600 <= 168
            ]
            if historical:
                snapshot_at, snapshot_views, _ = historical[0]
                elapsed_hours = (latest_at - snapshot_at).total_seconds() / 3600
                snapshot_vph = abs(current_views - snapshot_views) / elapsed_hours
                if math.isfinite(snapshot_vph) and snapshot_vph <= current_views:
                    return {
                        "status": "ok",
                        "vph": round(snapshot_vph, 1),
                        "vph_method": "snapshot",
                        "views_delta": abs(current_views - snapshot_views),
                        "hours_delta": round(elapsed_hours, 4),
                        "snapshot_window_hours": [12, 168],
                        "invalid_observations": invalid_observations,
                        "first_snapshot": snapshot_at.isoformat(),
                        "last_snapshot": latest_at.isoformat(),
                    }
            if age_hours is not None and 0 < age_hours < 168:
                average_vph = current_views / age_hours
                if math.isfinite(average_vph):
                    return {
                        "status": "ok",
                        "vph": round(average_vph, 1),
                        "vph_method": "lifetime_average",
                        "age_hours": round(age_hours, 4),
                        "invalid_observations": invalid_observations,
                    }
            return {
                "status": "unavailable",
                "vph": None,
                "reason": "No valid 12-168 hour snapshot and lifetime fallback is ineligible",
                "vph_method": None,
                "age_hours": round(age_hours, 4) if age_hours is not None else None,
                "invalid_observations": invalid_observations,
            }
        if len(valid) < 2:
            return {
                "status": "unavailable",
                "vph": None,
                "reason": "Need two valid view observations",
                "valid_observations": len(valid),
                "invalid_observations": invalid_observations,
            }
        latest_at = valid[-1][0]
        cutoff = latest_at - timedelta(hours=window_hours)
        window = [item for item in valid if item[0] >= cutoff]
        if len(window) < 2:
            return {
                "status": "unavailable",
                "vph": None,
                "reason": "Not enough observations inside requested window",
                "window_hours_requested": window_hours,
                "invalid_observations": invalid_observations,
            }
        first_at, first_views, _ = window[0]
        last_at, last_views, _ = window[-1]
        elapsed_hours = (last_at - first_at).total_seconds() / 3600
        if elapsed_hours < min_interval_minutes / 60:
            return {
                "status": "unavailable",
                "vph": None,
                "reason": "Observation interval is below minimum",
                "hours_delta": round(elapsed_hours, 4),
                "minimum_interval_minutes": min_interval_minutes,
                "invalid_observations": invalid_observations,
            }
        views_delta = last_views - first_views
        if views_delta < 0:
            return {
                "status": "counter_decrease",
                "vph": None,
                "reason": "View counter decreased; velocity is not computed",
                "views_delta": views_delta,
                "hours_delta": round(elapsed_hours, 4),
                "invalid_observations": invalid_observations,
            }
        return {
            "status": "ok",
            "vph": round(views_delta / elapsed_hours, 1),
            "views_delta": views_delta,
            "hours_delta": round(elapsed_hours, 4),
            "window_hours_requested": window_hours,
            "window_hours_observed": round(elapsed_hours, 4),
            "minimum_interval_minutes": min_interval_minutes,
            "snapshots_used": len(window),
            "invalid_observations": invalid_observations,
            "first_snapshot": first_at.isoformat(),
            "last_snapshot": last_at.isoformat(),
        }

    def detect_outlier(
        self,
        video_info,
        channel_videos,
        as_of=None,
        performance_curve=None,
    ):
        as_of = as_of or datetime.now(UTC)
        if as_of.tzinfo is None:
            return {
                "status": "unavailable",
                "is_outlier": None,
                "reason": "naive_as_of",
            }
        as_of = as_of.astimezone(UTC)
        target, target_error = _video_observation(video_info, as_of)
        if target_error:
            return {"status": "unavailable", "is_outlier": None, "reason": target_error}
        if performance_curve is None and self.storage is not None:
            channel_id = video_info.get("channel_id") or video_info.get("channelId")
            if channel_id:
                performance_curve = self.storage.get_channel_performance_curve(channel_id)
        curve_point = _select_curve_point(performance_curve, target["age_hours"])
        if curve_point is not None:
            if target["views"] < 1000:
                return {
                    "status": "unavailable",
                    "metric": "vidiq_client_curve_estimate_v1",
                    "is_outlier": None,
                    "median_multiple": None,
                    "reason": "minimum_1000_views",
                }
            baseline = (curve_point["perc30"] + curve_point["perc70"]) / 2
            if baseline <= 0:
                return {
                    "status": "unavailable",
                    "metric": "vidiq_client_curve_estimate_v1",
                    "is_outlier": None,
                    "median_multiple": None,
                    "reason": "performance_curve_baseline_is_zero",
                }
            raw_multiple = target["views"] / baseline
            if target["age_hours"] < 24 and raw_multiple <= 1:
                return {
                    "status": "unavailable",
                    "metric": "vidiq_client_curve_estimate_v1",
                    "is_outlier": None,
                    "median_multiple": None,
                    "reason": "suppressed_first_24_hours_at_or_below_1x",
                }
            score = round(raw_multiple) if raw_multiple >= 10 else round(raw_multiple, 2)
            return {
                "status": "ok",
                "metric": "vidiq_client_curve_estimate_v1",
                "score_label": "client estimate",
                "is_outlier": raw_multiple >= 3.0,
                "video_views": target["views"],
                "baseline_views": baseline,
                "baseline_perc30": curve_point["perc30"],
                "baseline_perc70": curve_point["perc70"],
                "curve_age_hours": curve_point["age_hours"],
                "median_multiple": score,
                "display_multiple": ">100x" if raw_multiple > 100 else f"{score}x",
                "cohort": {
                    "format": target["format"],
                    "age_bucket_hours": curve_point["age_hours"],
                },
                "disclaimer": (
                    "Client estimate from stored public performance curves; "
                    "not a production score."
                ),
            }
        eligible = []
        excluded = {"target": 0, "invalid": 0, "format": 0, "age_bucket": 0}
        for raw in channel_videos:
            candidate, error = _video_observation(raw, as_of)
            if error:
                excluded["invalid"] += 1
            elif candidate["video_id"] == target["video_id"]:
                excluded["target"] += 1
            elif candidate["format"] != target["format"]:
                excluded["format"] += 1
            elif candidate["age_bucket_hours"] != target["age_bucket_hours"]:
                excluded["age_bucket"] += 1
            else:
                eligible.append(candidate)
        cohort = {"format": target["format"], "age_bucket_hours": target["age_bucket_hours"]}
        if len(eligible) < 3:
            return {
                "status": "unavailable",
                "is_outlier": None,
                "reason": "Need at least 3 comparable baseline videos",
                "baseline_eligible_count": len(eligible),
                "baseline_excluded": excluded,
                "cohort": cohort,
            }
        baseline_views = [item["views"] for item in eligible]
        median_views = statistics.median(baseline_views)
        if median_views <= 0:
            return {
                "status": "unavailable",
                "is_outlier": None,
                "reason": "Comparable baseline median is zero",
            }
        below = sum(value < target["views"] for value in baseline_views)
        tied = sum(value == target["views"] for value in baseline_views)
        percentile = 100 * (below + 0.5 * tied) / len(baseline_views)
        multiple = target["views"] / median_views
        return {
            "status": "ok",
            "metric": "custom_comparable_median_multiple_v1",
            "is_outlier": multiple >= 3.0,
            "video_views": target["views"],
            "baseline_median_views": median_views,
            "median_multiple": round(multiple, 2),
            "percentile_midrank": round(percentile, 1),
            "baseline_eligible_count": len(eligible),
            "baseline_excluded": excluded,
            "cohort": cohort,
            "disclaimer": "Custom comparable-cohort metric; not a vidIQ score.",
        }

    def vidiq_score_client(self, views, facebook_likes=0):
        return {
            "score": vidiq_score_client(views, facebook_likes),
            "label": "client estimate",
            "production_score": False,
        }

    def keyword_competition_signals(
        self, keyword, search_results, calibration=None, demand=None, as_of=None
    ):
        as_of = as_of or datetime.now(UTC)
        if as_of.tzinfo is None:
            return {
                "metric": "keyword_competition_signals_v1",
                "competition_score": None,
                "calibration_status": "invalid",
                "reason": "naive_as_of",
            }
        as_of = as_of.astimezone(UTC)
        rows = []
        excluded = {"missing_channel_id": 0, "invalid_views_or_age": 0}
        for raw in search_results:
            channel_id = raw.get("channelId") or raw.get("channel_id")
            if not channel_id:
                excluded["missing_channel_id"] += 1
                continue
            observed, error = _video_observation(raw, as_of)
            if error or observed["age_hours"] <= 0:
                excluded["invalid_views_or_age"] += 1
                continue
            rows.append(
                {
                    "channel_id": channel_id,
                    "format": observed["format"],
                    "views_per_day": observed["views"] / max(observed["age_hours"] / 24, 1),
                    "relevance": _title_relevance(keyword, raw.get("title", "")),
                }
            )
        relevance = [row["relevance"] for row in rows if row["relevance"] is not None]
        vpd_by_format = {}
        for format_name in ("short", "long_form"):
            values = [row["views_per_day"] for row in rows if row["format"] == format_name]
            vpd_by_format[format_name] = statistics.median(values) if values else None
        features = {
            "sample_size": len(search_results),
            "eligible_sample_size": len(rows),
            "relevance_median": (statistics.median(relevance) if relevance else None),
            "channel_concentration_hhi": _normalized_hhi([row["channel_id"] for row in rows]),
            "median_views_per_day_short": vpd_by_format["short"],
            "median_views_per_day_long_form": vpd_by_format["long_form"],
        }
        result = {
            "metric": "keyword_competition_signals_v1",
            "keyword": keyword,
            "competition_score": None,
            "competition_level": None,
            "demand": demand,
            "opportunity_score": None,
            "calibration_status": "unavailable",
            "features": features,
            "excluded": excluded,
            "uncertainty": {
                "low_sample": len(rows) < 20,
                "missing_fraction": 1 - (len(rows) / max(len(search_results), 1)),
            },
        }
        if calibration is None:
            result["reason"] = "No versioned calibration artifact loaded"
            return result
        if isinstance(calibration, CalibrationRepository):
            repository = calibration
        else:
            schema_path = _reference_path("keyword_competition_calibration.schema.json")
            repository = CalibrationRepository(schema_path)
            repository.validate(calibration)
        if not repository.valid:
            result["reason"] = "Invalid calibration schema"
            result["calibration_status"] = "invalid"
            result["calibration_errors"] = repository.errors
            return result
        artifact = repository.artifact
        required = artifact["required_features"]
        if any(features.get(name) is None for name in required):
            result["reason"] = "Required calibrated features are unavailable"
            return result
        try:
            z = artifact["intercept"]
            for name, coefficient in artifact["coefficients"].items():
                value = features[name]
                if artifact["feature_transforms"][name] == "log1p":
                    value = math.log1p(value)
                z += coefficient * value
            score = round(100 / (1 + math.exp(-z)))
            level = next(label for upper, label in artifact["thresholds"] if score <= upper)
        except (TypeError, ValueError, KeyError, StopIteration, OverflowError):
            result["reason"] = "Invalid calibration schema"
            return result
        result.update(
            {
                "competition_score": score,
                "competition_level": level,
                "calibration_status": "calibrated",
                "calibration_version": artifact["version"],
                "calibration_query_count": artifact["training_query_count"],
            }
        )
        demand_score = demand.get("score") if isinstance(demand, dict) else None
        if (
            isinstance(demand_score, (int, float))
            and not isinstance(demand_score, bool)
            and math.isfinite(demand_score)
            and 0 <= demand_score <= 100
        ):
            result["opportunity_score"] = round(0.6 * demand_score + 0.4 * (100 - score))
        elif demand is not None:
            result["demand_diagnostic"] = "invalid_demand"
        return result

    def keyword_competition_score(self, keyword, search_results, **kwargs):
        result = self.keyword_competition_signals(keyword, search_results, **kwargs)
        result["deprecated_api"] = "Use keyword_competition_signals(); score may be unavailable."
        return result
