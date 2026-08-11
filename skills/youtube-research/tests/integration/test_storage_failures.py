from scripts.exceptions import StorageError
from scripts.result import Result
from scripts.tracking import TrackingModule


class BrokenStorage:
    def snapshot_channel(self, *_args, **_kwargs):
        raise StorageError("locked")


class Channel:
    def channel_info(self, _value):
        return Result(
            status="ok",
            items=[
                {
                    "channel_id": "UC12345678901234567890",
                    "name": "Channel",
                    "subscriber_count": 1,
                    "video_count": 1,
                }
            ],
        )


def test_storage_failure_is_typed_exception():
    module = TrackingModule(Channel(), None, None, None, BrokenStorage())
    result = module.snapshot_channel_live("UC12345678901234567890")
    assert result.status == "partial"
    assert result.error_code == "storage_error"
