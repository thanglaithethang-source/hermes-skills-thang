import sqlite3
from datetime import UTC, datetime, timedelta

from scripts.analytics_estimate import AnalyticsEstimateModule
from scripts.storage import Storage


def insert_video(db, video_id, count, observed):
    with sqlite3.connect(db.db_path) as conn:
        conn.execute(
            "INSERT INTO video_snapshots (video_id, view_count, snapshot_at) VALUES (?, ?, ?)",
            (video_id, count, observed),
        )


def test_newest_limit_is_returned_ascending(tmp_path):
    db = Storage(str(tmp_path / "history.db"))
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for index in range(101):
        insert_video(db, "v", index, (base + timedelta(hours=index)).isoformat())
    rows = db.get_video_snapshots("v", limit=100)
    assert rows[0]["view_count"] == 1
    assert rows[-1]["view_count"] == 100


def test_vph_strict_counts_window_and_counter_decrease(tmp_path):
    db = Storage(str(tmp_path / "vph.db"))
    now = datetime(2026, 1, 2, tzinfo=UTC)
    insert_video(db, "ok", None, (now - timedelta(hours=3)).isoformat())
    insert_video(db, "ok", 100, (now - timedelta(hours=2)).isoformat())
    insert_video(db, "ok", 130, now.isoformat())
    result = AnalyticsEstimateModule(storage=db).calculate_vph("ok")
    assert result["status"] == "ok" and result["vph"] == 15
    assert result["invalid_observations"] == 1
    insert_video(db, "down", 200, (now - timedelta(hours=1)).isoformat())
    insert_video(db, "down", 100, now.isoformat())
    assert AnalyticsEstimateModule(storage=db).calculate_vph("down")["status"] == "counter_decrease"


def test_vph_minimum_interval(tmp_path):
    db = Storage(str(tmp_path / "close.db"))
    now = datetime(2026, 1, 2, tzinfo=UTC)
    insert_video(db, "v", 1, now.isoformat())
    insert_video(db, "v", 2, (now + timedelta(minutes=1)).isoformat())
    assert AnalyticsEstimateModule(storage=db).calculate_vph("v")["status"] == "unavailable"
