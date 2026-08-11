"""Concurrency-safe SQLite snapshot storage with normalized epoch ordering."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from numbers import Integral
from typing import Any

from .exceptions import StorageError
from .time_utils import parse_utc

DEFAULT_DB_PATH = os.path.join(
    os.environ.get("HERMES_HOME", os.path.expanduser("~")),
    "youtube_research.db",
)
PERFORMANCE_AGE_BUCKETS_HOURS = (1, 6, 24, 72, 168, 672)


def _count(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer or None")
    return int(value)


def _epoch_ms(value: datetime) -> int:
    if value.tzinfo is None:
        raise ValueError("snapshot time must be timezone-aware")
    return round(value.astimezone(UTC).timestamp() * 1000)


def _datetime(value: str | datetime) -> datetime:
    parsed = value if isinstance(value, datetime) else parse_utc(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _percentile(values: list[int], fraction: float) -> float:
    """Return a linearly interpolated percentile for an already validated sample."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


class Storage:
    def __init__(
        self,
        db_path: str | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.clock = clock or (lambda: datetime.now(UTC))
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        if self.db_path != ":memory:":
            connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        try:
            with closing(self._connect()) as connection:
                yield connection
        except sqlite3.Error as exc:
            raise StorageError(str(exc)) from exc

    def _init_db(self) -> None:
        tables = {
            "video_snapshots": """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL, channel_id TEXT, title TEXT,
                view_count INTEGER, like_count INTEGER, comment_count INTEGER,
                published_at TEXT, is_live INTEGER NOT NULL DEFAULT 0,
                snapshot_at TEXT NOT NULL, snapshot_epoch_ms INTEGER,
                UNIQUE(video_id, snapshot_at)
            """,
            "channel_snapshots": """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL, name TEXT,
                subscriber_count INTEGER, video_count INTEGER,
                snapshot_at TEXT NOT NULL, snapshot_epoch_ms INTEGER,
                UNIQUE(channel_id, snapshot_at)
            """,
            "keyword_snapshots": """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL, result_count INTEGER,
                top_video_id TEXT, top_video_views INTEGER,
                snapshot_at TEXT NOT NULL, snapshot_epoch_ms INTEGER,
                UNIQUE(keyword, snapshot_at)
            """,
            "performance_curve_snapshots": """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL, video_id TEXT NOT NULL,
                age_hours INTEGER NOT NULL, view_count INTEGER NOT NULL,
                observed_age_hours REAL NOT NULL, snapshot_at TEXT NOT NULL,
                snapshot_epoch_ms INTEGER,
                UNIQUE(channel_id, video_id, age_hours)
            """,
        }
        with self._connection() as connection, connection:
            for table, definition in tables.items():
                connection.execute(f"CREATE TABLE IF NOT EXISTS {table} ({definition})")
                columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
                if table == "video_snapshots":
                    if "published_at" not in columns:
                        connection.execute(
                            "ALTER TABLE video_snapshots ADD COLUMN published_at TEXT"
                        )
                    if "is_live" not in columns:
                        connection.execute(
                            "ALTER TABLE video_snapshots ADD COLUMN is_live "
                            "INTEGER NOT NULL DEFAULT 0"
                        )
                if "snapshot_epoch_ms" not in columns:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN snapshot_epoch_ms INTEGER")
                rows = connection.execute(
                    f"SELECT id, snapshot_at FROM {table} WHERE snapshot_epoch_ms IS NULL"
                ).fetchall()
                for row in rows:
                    try:
                        epoch = _epoch_ms(parse_utc(row["snapshot_at"]))
                    except (TypeError, ValueError):
                        continue
                    connection.execute(
                        f"UPDATE {table} SET snapshot_epoch_ms=? WHERE id=?",
                        (epoch, row["id"]),
                    )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_video_snapshot_epoch "
                "ON video_snapshots(video_id, snapshot_epoch_ms DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_channel_snapshot_epoch "
                "ON channel_snapshots(channel_id, snapshot_epoch_ms DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_keyword_snapshot_epoch "
                "ON keyword_snapshots(keyword, snapshot_epoch_ms DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_performance_curve_channel_age "
                "ON performance_curve_snapshots(channel_id, age_hours)"
            )

    def _observed(self) -> tuple[str, int]:
        observed = self.clock()
        if observed.tzinfo is None:
            raise ValueError("storage clock must return an aware datetime")
        normalized = observed.astimezone(UTC)
        return normalized.isoformat(), _epoch_ms(normalized)

    def snapshot_video(
        self,
        video_id: str,
        channel_id: str | None = None,
        title: str | None = None,
        view_count: Any = None,
        like_count: Any = None,
        comment_count: Any = None,
        published_at: str | datetime | None = None,
        is_live: bool = False,
    ) -> None:
        observed, epoch = self._observed()
        normalized_published = None
        if published_at is not None:
            normalized_published = _datetime(published_at).isoformat()
        if not isinstance(is_live, bool):
            raise ValueError("is_live must be a boolean")
        normalized_views = _count(view_count, "view_count")
        values = (
            video_id,
            channel_id,
            title,
            normalized_views,
            _count(like_count, "like_count"),
            _count(comment_count, "comment_count"),
            normalized_published,
            int(is_live),
            observed,
            epoch,
        )
        with self._connection() as connection, connection:
            connection.execute(
                "INSERT OR REPLACE INTO video_snapshots "
                "(video_id,channel_id,title,view_count,like_count,comment_count,"
                "published_at,is_live,snapshot_at,snapshot_epoch_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                values,
            )
        if (
            channel_id
            and normalized_published
            and normalized_views is not None
            and not is_live
        ):
            self.snapshot_performance_curve(
                video_id=video_id,
                channel_id=channel_id,
                published_at=normalized_published,
                view_count=normalized_views,
                observed_at=observed,
            )

    def snapshot_performance_curve(
        self,
        *,
        video_id: str,
        channel_id: str,
        published_at: str | datetime,
        view_count: Any,
        observed_at: str | datetime | None = None,
    ) -> int:
        """Store one observation in the nearest standard video-age bucket."""
        views = _count(view_count, "view_count")
        if views is None:
            raise ValueError("view_count is required")
        published = _datetime(published_at)
        observed = _datetime(observed_at) if observed_at is not None else self.clock()
        if observed.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        observed = observed.astimezone(UTC)
        age_hours = (observed - published).total_seconds() / 3600
        if age_hours < 0:
            raise ValueError("observed_at cannot precede published_at")
        bucket = min(
            PERFORMANCE_AGE_BUCKETS_HOURS,
            key=lambda candidate: (abs(candidate - age_hours), candidate),
        )
        with self._connection() as connection, connection:
            connection.execute(
                "INSERT OR REPLACE INTO performance_curve_snapshots "
                "(channel_id,video_id,age_hours,view_count,observed_age_hours,"
                "snapshot_at,snapshot_epoch_ms) VALUES (?,?,?,?,?,?,?)",
                (
                    channel_id,
                    video_id,
                    bucket,
                    views,
                    age_hours,
                    observed.isoformat(),
                    _epoch_ms(observed),
                ),
            )
        return bucket

    def snapshot_channel(
        self,
        channel_id: str,
        name: str | None = None,
        subscriber_count: Any = None,
        video_count: Any = None,
    ) -> None:
        observed, epoch = self._observed()
        with self._connection() as connection, connection:
            connection.execute(
                "INSERT OR REPLACE INTO channel_snapshots "
                "(channel_id,name,subscriber_count,video_count,snapshot_at,"
                "snapshot_epoch_ms) VALUES (?,?,?,?,?,?)",
                (
                    channel_id,
                    name,
                    _count(subscriber_count, "subscriber_count"),
                    _count(video_count, "video_count"),
                    observed,
                    epoch,
                ),
            )

    def snapshot_keyword(
        self,
        keyword: str,
        result_count: Any = None,
        top_video_id: str | None = None,
        top_video_views: Any = None,
    ) -> None:
        observed, epoch = self._observed()
        with self._connection() as connection, connection:
            connection.execute(
                "INSERT OR REPLACE INTO keyword_snapshots "
                "(keyword,result_count,top_video_id,top_video_views,snapshot_at,"
                "snapshot_epoch_ms) VALUES (?,?,?,?,?,?)",
                (
                    keyword,
                    _count(result_count, "result_count"),
                    top_video_id,
                    _count(top_video_views, "top_video_views"),
                    observed,
                    epoch,
                ),
            )

    @staticmethod
    def _limit(limit: Any) -> int:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        return limit

    def _history(self, table: str, field: str, value: str, limit: int) -> list[dict[str, Any]]:
        limit = self._limit(limit)
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM (SELECT * FROM {table} WHERE {field}=? "
                "ORDER BY COALESCE(snapshot_epoch_ms,"
                "CAST((julianday(snapshot_at)-2440587.5)*86400000 AS INTEGER)) DESC LIMIT ?) "
                "ORDER BY COALESCE(snapshot_epoch_ms,"
                "CAST((julianday(snapshot_at)-2440587.5)*86400000 AS INTEGER)) ASC",
                (value, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_video_snapshots(self, video_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self._history("video_snapshots", "video_id", video_id, limit)

    def get_channel_snapshots(self, channel_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self._history("channel_snapshots", "channel_id", channel_id, limit)

    def get_keyword_snapshots(self, keyword: str, limit: int = 100) -> list[dict[str, Any]]:
        return self._history("keyword_snapshots", "keyword", keyword, limit)

    def get_channel_performance_curve(self, channel_id: str) -> list[dict[str, Any]]:
        """Return age-bucket perc30/perc70/median values for a channel."""
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT age_hours, view_count FROM performance_curve_snapshots "
                "WHERE channel_id=? ORDER BY age_hours, video_id",
                (channel_id,),
            ).fetchall()
        grouped: dict[int, list[int]] = {}
        for row in rows:
            grouped.setdefault(int(row["age_hours"]), []).append(int(row["view_count"]))
        return [
            {
                "age_hours": age_hours,
                "perc30": _percentile(values, 0.30),
                "perc70": _percentile(values, 0.70),
                "median": _percentile(values, 0.50),
            }
            for age_hours, values in sorted(grouped.items())
        ]

    def compare_video_to_performance_curve(
        self,
        channel_id: str,
        current_views: Any,
        age_hours: float,
    ) -> dict[str, Any] | None:
        """Compare current views with the vidIQ-style expected-view curve midpoint."""
        views = _count(current_views, "current_views")
        if views is None or age_hours < 0:
            return None
        curve = self.get_channel_performance_curve(channel_id)
        if not curve:
            return None
        by_age = {round(row["age_hours"]): row for row in curve}
        exact_hour = round(age_hours)
        day_hour = round(age_hours / 24) * 24
        selected = (
            by_age.get(exact_hour)
            or by_age.get(day_hour)
            or (by_age.get(168) if age_hours <= 168 else None)
            or by_age[max(by_age)]
        )
        baseline = (selected["perc30"] + selected["perc70"]) / 2
        if baseline <= 0:
            return None
        score = views / baseline
        display_score = round(score) if score >= 10 else round(score, 2)
        return {
            "channel_id": channel_id,
            "video_views": views,
            "age_hours": age_hours,
            "curve_age_hours": selected["age_hours"],
            "perc30": selected["perc30"],
            "perc70": selected["perc70"],
            "median": selected["median"],
            "baseline_views": baseline,
            "score": display_score,
            "display": ">100x" if score > 100 else f"{display_score}x",
        }

    def get_channel_snapshot_at_or_before(
        self, channel_id: str, observed_at: str | datetime | int
    ) -> dict[str, Any] | None:
        if isinstance(observed_at, int) and not isinstance(observed_at, bool):
            epoch = observed_at
        else:
            parsed = observed_at if isinstance(observed_at, datetime) else parse_utc(observed_at)
            epoch = _epoch_ms(parsed)
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM channel_snapshots WHERE channel_id=? AND "
                "COALESCE(snapshot_epoch_ms,"
                "CAST((julianday(snapshot_at)-2440587.5)*86400000 AS INTEGER))<=? "
                "ORDER BY COALESCE(snapshot_epoch_ms,"
                "CAST((julianday(snapshot_at)-2440587.5)*86400000 AS INTEGER)) DESC LIMIT 1",
                (channel_id, epoch),
            ).fetchone()
        return dict(row) if row else None

    def get_all_channel_ids(self) -> list[str]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT DISTINCT channel_id FROM channel_snapshots"
            ).fetchall()
        return [row[0] for row in rows]
