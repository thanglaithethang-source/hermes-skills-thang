import sqlite3
from datetime import UTC, datetime, timedelta

from scripts.report import ReportModule
from scripts.result import Result
from scripts.storage import Storage
from scripts.tracking import TrackingModule


class Stub:
    def __init__(self, result):
        self.result = result

    def channel_info(self, value):
        return self.result

    def video_info(self, value):
        return self.result

    def search(self, value, limit=20):
        return self.result


def tracking(db, result):
    stub = Stub(result)
    return TrackingModule(stub, stub, stub, None, db)


def insert_channel(db, channel_id, subscribers, videos, observed):
    with sqlite3.connect(db.db_path) as conn:
        conn.execute(
            "INSERT INTO channel_snapshots "
            "(channel_id, subscriber_count, video_count, snapshot_at) "
            "VALUES (?, ?, ?, ?)",
            (channel_id, subscribers, videos, observed),
        )


def test_live_channel_snapshot_fetches_and_persists(tmp_path):
    db = Storage(str(tmp_path / "tracking.db"))
    result = Result(
        status="ok",
        items=[
            {
                "channel_id": "UC1",
                "name": "One",
                "subscriber_count": 10,
                "video_count": 2,
            }
        ],
    )
    fetched = tracking(db, result).snapshot_channel_live("UC1")
    assert fetched.status == "ok"
    assert db.get_channel_snapshots("UC1")[0]["subscriber_count"] == 10


def test_growth_requested_interval_and_missing_count(tmp_path):
    db = Storage(str(tmp_path / "growth.db"))
    now = datetime(2026, 7, 27, tzinfo=UTC)
    insert_channel(db, "UC1", None, 10, (now - timedelta(days=7)).isoformat())
    insert_channel(db, "UC1", None, 17, now.isoformat())
    result = tracking(db, Result(status="ok", items=[{}])).channel_growth(
        "UC1", interval_hours=168, as_of=now
    )
    growth = result.items[0]
    assert growth["interval_hours_observed"] == 168
    assert growth["subscriber_delta"] is None
    assert growth["video_delta"] == 7


def test_compare_competitors_structured_failures(tmp_path):
    db = Storage(str(tmp_path / "compare.db"))
    module = tracking(db, Result.error("fetch failed"))
    result = module.compare_competitors(["UC1", "UC2"], refresh=True)
    assert result.status == "error"
    assert len(result.metadata["failures"]) == 2


def test_keyword_snapshot_and_no_storage():
    search = Result(status="ok", items=[{"videoId": "v", "views": 42}])
    module = tracking(None, search)
    assert module.snapshot_keyword_live("ai").error_code == "storage_unavailable"


def test_report_result_and_markdown_partial_warning():
    report_module = ReportModule.__new__(ReportModule)
    partial = Result(
        status="partial",
        items=[
            {
                "report_type": "keyword",
                "keyword": "ai",
                "collection_status": "partial",
                "avg_views": None,
                "keyword_signals": {
                    "competition_score": None,
                    "calibration_status": "unavailable",
                    "demand": None,
                    "reason": "No versioned calibration artifact loaded",
                },
            }
        ],
        reason="Report contains unavailable inputs",
    )
    markdown = report_module.to_markdown(partial)
    assert "PARTIAL REPORT" in markdown
    assert "unavailable" in markdown
    assert "No versioned calibration artifact loaded" in markdown
