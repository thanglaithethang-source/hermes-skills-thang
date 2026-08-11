from datetime import UTC, datetime

import pytest

from scripts.tracking import TrackingModule


class GrowthStorage:
    def __init__(self, rows, lookups):
        self.rows = rows
        self.lookups = list(lookups)

    def get_channel_snapshots(self, *_args, **_kwargs):
        return self.rows

    def get_channel_snapshot_at_or_before(self, *_args, **_kwargs):
        return self.lookups.pop(0)


def test_growth_empty_invalid_and_missing_baseline():
    module = TrackingModule(None, None, None, None, GrowthStorage([], []))
    assert module.channel_growth("x").status == "empty"
    with pytest.raises(ValueError):
        module.channel_growth("x", interval_hours=0)
    naive = TrackingModule(None, None, None, None, GrowthStorage([{}], []))
    assert naive.channel_growth("x", as_of=datetime(2026, 1, 1)).error_code == "invalid_input"
    latest_missing = TrackingModule(None, None, None, None, GrowthStorage([{}], [None]))
    assert (
        latest_missing.channel_growth("x", as_of=datetime(2026, 1, 1, tzinfo=UTC)).status == "empty"
    )
    latest = {
        "id": 2,
        "snapshot_at": "2026-01-01T01:00:00Z",
        "subscriber_count": 2,
        "video_count": 2,
    }
    no_baseline = TrackingModule(None, None, None, None, GrowthStorage([latest], [latest, None]))
    assert (
        no_baseline.channel_growth(
            "x",
            interval_hours=1,
            as_of=datetime(2026, 1, 1, 1, tzinfo=UTC),
        ).status
        == "partial"
    )
