from scripts.result import Result
from scripts.youtube_research import YouTubeResearch


class Enricher:
    def __init__(self, partial=False):
        self.partial_value = partial

    def enrich(self, rows, **_kwargs):
        enriched = [dict(row, publish_date="2026-07-20T00:00:00Z") for row in rows]
        if self.partial_value:
            return Result(
                status="partial",
                items=enriched,
                reason="one missing",
                metadata={"failed": 1},
            )
        return Result(status="ok", items=enriched)


class Analytics:
    def detect_outlier(self, *_args, **_kwargs):
        return {"status": "ok"}

    def keyword_competition_signals(self, *_args, **_kwargs):
        return {"competition_score": None}


def test_facade_outlier_and_keyword_enrichment_paths():
    yt = YouTubeResearch.__new__(YouTubeResearch)
    yt.publish_date_enricher = Enricher(partial=True)
    yt.analytics_mod = Analytics()
    outlier = yt.detect_outlier({"videoId": "video000001"}, [{"videoId": "video000002"}])
    assert outlier["status"] == "partial"
    signals = yt.keyword_competition_signals("ai", [{"videoId": "video000001"}])
    assert signals["collection_status"] == "partial"
    no_enrichment = yt.keyword_competition_signals(
        "ai",
        [{"videoId": "video000001"}],
        enrich_publish_dates=False,
    )
    assert no_enrichment["collection_status"] == "ok"
