import sqlite3
from datetime import UTC, datetime, timedelta

from scripts.storage import Storage
from scripts.tracking import TrackingModule


def test_growth_requires_distinct_fifteen_minute_snapshots(tmp_path):
    db = Storage(str(tmp_path / "growth-contract.db"))
    observed = datetime(2026, 7, 27, tzinfo=UTC)
    with sqlite3.connect(db.db_path) as conn:
        conn.execute(
            "INSERT INTO channel_snapshots "
            "(channel_id, subscriber_count, video_count, snapshot_at) VALUES (?,?,?,?)",
            ("UC1", 1, 1, observed.isoformat()),
        )
    module = TrackingModule(None, None, None, None, db)
    one = module.channel_growth("UC1", interval_hours=1, as_of=observed)
    assert one.status == "partial"
    assert "subscriber_delta" not in one.items[0]

    with sqlite3.connect(db.db_path) as conn:
        conn.execute(
            "INSERT INTO channel_snapshots "
            "(channel_id, subscriber_count, video_count, snapshot_at) VALUES (?,?,?,?)",
            ("UC1", 2, 2, (observed + timedelta(minutes=15)).isoformat()),
        )
    valid = module.channel_growth(
        "UC1", interval_hours=0.25, as_of=observed + timedelta(minutes=15)
    )
    assert valid.status == "ok"
    assert valid.items[0]["subscriber_delta"] == 1
