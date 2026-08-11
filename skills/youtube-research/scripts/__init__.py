"""Public YouTube Research package."""

from typing import TYPE_CHECKING, Any

from .models import CanonicalVideo, ParseDiagnostics, ParsedPage, ParsedValue
from .result import Result

if TYPE_CHECKING:
    from .youtube_research import YouTubeResearch

__all__ = [
    "CanonicalVideo",
    "ParseDiagnostics",
    "ParsedPage",
    "ParsedValue",
    "Result",
    "YouTubeResearch",
]


def __getattr__(name: str) -> Any:
    if name == "YouTubeResearch":
        from .youtube_research import YouTubeResearch

        return YouTubeResearch
    raise AttributeError(name)
