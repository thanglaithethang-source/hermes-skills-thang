import sys

from scripts import youtube_research as facade_module
from scripts.youtube_research import YouTubeResearch


class Client:
    def refresh_context(self):
        self.refreshed = True


def test_facade_initialization_and_refresh(monkeypatch):
    monkeypatch.setattr(facade_module, "InnerTubeClient", lambda *a, **k: Client())
    yt = YouTubeResearch()
    assert yt.storage is None
    yt.refresh_context()
    assert yt.client.refreshed is True


def test_show_profile_cli(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["youtube-research", "--show-profile"])
    facade_module.main()
    output = capsys.readouterr().out
    assert "web-2026-07-24-v1" in output
    assert "api_key" not in output
