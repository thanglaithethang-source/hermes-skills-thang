"""Shared content-format classification."""

from __future__ import annotations

from numbers import Integral
from typing import Literal

ContentFormat = Literal["short", "long_form", "live", "unknown"]


def classify_content_format(duration: object, is_live: bool = False) -> ContentFormat:
    if is_live:
        return "live"
    if isinstance(duration, bool) or not isinstance(duration, Integral) or duration <= 0:
        return "unknown"
    return "short" if int(duration) <= 180 else "long_form"
