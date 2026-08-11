"""Immutable known-good InnerTube client profile."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True)
class ClientContext:
    client_name: str = "WEB"
    client_version: str = "2.20260724.01.01"
    hl: str = "en"
    gl: str = "VN"
    visitor_data: str = ""

    def payload(self) -> dict[str, dict[str, str]]:
        client = {
            "clientName": self.client_name,
            "clientVersion": self.client_version,
            "hl": self.hl,
            "gl": self.gl,
        }
        if self.visitor_data:
            client["visitorData"] = self.visitor_data
        return {"client": client}


@dataclass(frozen=True)
class AuthConfig:
    authenticated: bool = False
    strict: bool = True
    cookies: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True)
class ClientProfile:
    profile_id: str
    context: ClientContext
    api_key: str
    user_agent: str
    search_sort_params: Mapping[str, str]
    channel_videos_params: str
    browse_ids: Mapping[str, str]


KNOWN_GOOD_PROFILE = ClientProfile(
    profile_id="web-2026-07-24-v1",
    context=ClientContext(),
    api_key=os.environ.get(
        "YT_INNERTUBE_KEY",
        "<set-via-YT_INNERTUBE_KEY>",
    ),
    user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
    ),
    search_sort_params=MappingProxyType({"views": "CAMSAhAB", "date": "CAISAhAB"}),
    channel_videos_params="EgZ2aWRlb3PyBgQKAjoA",
    browse_ids=MappingProxyType({"trending": "FEtrending", "home": "FEwhat_to_watch"}),
)
