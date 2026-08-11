from scripts.report import ReportModule
from scripts.result import Result


class Search:
    def __init__(self, result):
        self.result = result

    def search(self, *_args, **_kwargs):
        return self.result

    def search_suggestions(self, *_args, **_kwargs):
        return Result(status="ok", items=["ai tool"])


class Enricher:
    def enrich(self, rows, **_kwargs):
        enriched = [dict(row, publish_date="2026-07-20T00:00:00Z") for row in rows]
        return Result(status="ok", items=enriched)


class Video:
    def video_info(self, video_id):
        return Result(
            status="ok",
            items=[
                {
                    "video_id": video_id,
                    "title": "AI",
                    "view_count": 100,
                    "duration_seconds": 120,
                    "publish_date": "2026-07-20T00:00:00Z",
                    "tags": [],
                }
            ],
        )


class Analytics:
    def estimate_ctr(self, *_args, **_kwargs):
        return {"estimable": False}

    def estimate_rpm(self, *_args, **_kwargs):
        return {"estimable": False}

    def keyword_competition_signals(self, *_args, **_kwargs):
        return {"competition_score": None, "calibration_status": "unavailable"}


def test_keyword_report_dependency_integration():
    module = ReportModule.__new__(ReportModule)
    module.search_mod = Search(
        Result(
            status="ok",
            items=[
                {
                    "videoId": "video000001",
                    "video_id": "video000001",
                    "title": "AI",
                    "channel": "One",
                    "channelId": "UC12345678901234567890",
                    "views": 100,
                    "duration_seconds": 120,
                }
            ],
        )
    )
    module.publish_date_enricher = Enricher()
    module.video_mod = Video()
    module.analytics_mod = Analytics()
    module.storage = None
    result = module.keyword_report("ai", limit=1)
    assert result.status == "partial"
    assert "history" in result.reason
    assert result.metadata["dependencies"]["search"]["status"] == "ok"


def test_keyword_report_error_and_empty_passthrough():
    module = ReportModule.__new__(ReportModule)
    module.search_mod = Search(Result.error("bad"))
    assert module.keyword_report("ai").status == "error"
    module.search_mod = Search(Result(status="empty", reason="none"))
    assert module.keyword_report("ai").status == "empty"
