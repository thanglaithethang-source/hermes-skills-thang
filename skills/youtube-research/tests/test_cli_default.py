import sys

from scripts import youtube_research as facade_module
from scripts.result import Result


class FakeResearch:
    def search(self, *_args, **_kwargs):
        return Result(status="ok", items=[{"title": "One"}])


def test_default_cli_smoke(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["youtube-research"])
    monkeypatch.setattr(facade_module, "YouTubeResearch", FakeResearch)
    facade_module.main()
    assert "One" in capsys.readouterr().out
