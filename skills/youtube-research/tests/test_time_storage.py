import sqlite3

import pytest

from scripts.storage import Storage
from scripts.time_utils import parse_utc


def test_naive_rejected_and_offset_ordering(tmp_path):
    with pytest.raises(ValueError):
        parse_utc("2026-01-01T00:00:00")
    storage = Storage(str(tmp_path / "offset.db"))
    with sqlite3.connect(storage.db_path) as connection:
        connection.execute(
            "INSERT INTO video_snapshots(video_id,view_count,snapshot_at) VALUES (?,?,?)",
            ("video000001", 1, "2026-01-01T02:00:00+02:00"),
        )
        connection.execute(
            "INSERT INTO video_snapshots(video_id,view_count,snapshot_at) VALUES (?,?,?)",
            ("video000001", 2, "2026-01-01T00:30:00Z"),
        )
    rows = storage.get_video_snapshots("video000001")
    assert [row["view_count"] for row in rows] == [1, 2]
