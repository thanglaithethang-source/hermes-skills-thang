import pytest

from scripts.exceptions import StorageError
from scripts.storage import Storage


def test_storage_pragmas_counts_and_error_translation(tmp_path):
    storage = Storage(str(tmp_path / "safe.db"))
    with storage._connection() as connection:
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    with pytest.raises(ValueError):
        storage.snapshot_video("video000001", view_count=True)
    storage.db_path = str(tmp_path / "missing" / "db.sqlite")
    with pytest.raises(StorageError):
        storage.get_all_channel_ids()
