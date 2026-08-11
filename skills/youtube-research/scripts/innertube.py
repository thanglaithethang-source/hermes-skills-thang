"""Hardened InnerTube transport with immutable per-instance context."""

from __future__ import annotations

import email.utils
import hashlib
import importlib
import json
import logging
import os
import random
import re
import time
from collections.abc import Callable, Iterator, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import requests

from .client_profile import KNOWN_GOOD_PROFILE
from .exceptions import AuthUnavailableError
from .validation import validate_locale, validate_query, validate_region, validate_video_id

logger = logging.getLogger(__name__)
INNERTUBE_BASE = "https://www.youtube.com/youtubei/v1"
DEFAULT_CONTEXT_PATH = os.environ.get("YT_CONTEXT_PATH", "")
INNERTUBE_API_KEY = KNOWN_GOOD_PROFILE.api_key
USER_AGENT = KNOWN_GOOD_PROFILE.user_agent
DEFAULT_CONTEXT = KNOWN_GOOD_PROFILE.context.payload()
RETRYABLE_CODES = {429, 500, 502, 503, 504}
ALLOWED_AUTH_COOKIES = {
    "SAPISID",
    "__Secure-3PAPISID",
    "__Secure-1PAPISID",
    "SID",
    "HSID",
    "SSID",
}


def _walk_dicts(node: Any) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_dicts(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_dicts(value)


def _bridge_value(response: Any) -> Any:
    """Unwrap common Hermes bridge Runtime.evaluate response envelopes."""
    current = response
    for _ in range(5):
        if not isinstance(current, dict):
            return current
        if current.get("type") == "error" or current.get("error"):
            return None
        if "value" in current:
            current = current["value"]
            continue
        if "result" in current:
            current = current["result"]
            continue
        if "tabs" in current:
            return current["tabs"]
        return current
    return current


def sanitize_error_message(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", text)
    text = re.sub(r"https?://\S+", "[url]", text, flags=re.I)
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[email]", text)
    text = re.sub(
        r"(?i)\b(?:bearer|api[_-]?key|token|cookie)\s*[:=]?\s*\S+",
        "[credential]",
        text,
    )
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())[:200]


class InnerTubeClient:
    def __init__(
        self,
        context_path: str | None = None,
        authenticated: bool = False,
        *,
        strict_auth: bool = True,
        session: Any = None,
        sleep: Callable[[float], None] = time.sleep,
        random_uniform: Callable[[float, float], float] = random.uniform,
        clock: Callable[[], float] = time.time,
        max_retries: int = 2,
        rate_limit_seconds: float = 0.3,
        bridge_send: Callable[[dict[str, Any]], Any] | None = None,
    ):
        self.context_path = context_path or DEFAULT_CONTEXT_PATH
        self.authenticated = authenticated
        self.strict_auth = strict_auth
        self.session = session or requests.Session()
        self.sleep = sleep
        self.random_uniform = random_uniform
        self.clock = clock
        self.max_retries = max(0, max_retries)
        self.rate_limit_seconds = max(0.0, rate_limit_seconds)
        self._bridge_send = bridge_send
        self.context = KNOWN_GOOD_PROFILE.context.payload()
        self.api_key = KNOWN_GOOD_PROFILE.api_key
        self.cookies: dict[str, str] = {}
        self.auth_status = "public"
        self._load_context(initial=True)

    def _validated_saved(self, saved: Any) -> tuple[dict[str, Any], str, dict[str, str]]:
        if not isinstance(saved, Mapping):
            raise ValueError("context file root must be an object")
        context = saved.get("context")
        if not isinstance(context, Mapping) or not isinstance(context.get("client"), Mapping):
            raise ValueError("context.client must be an object")
        client = context["client"]
        required = ("clientName", "clientVersion", "hl", "gl")
        if any(not isinstance(client.get(key), str) or not client[key].strip() for key in required):
            raise ValueError("context client fields must be non-empty strings")
        if len(client["clientName"]) > 40 or len(client["clientVersion"]) > 80:
            raise ValueError("context client fields exceed bounds")
        api_key = saved.get("api_key", KNOWN_GOOD_PROFILE.api_key)
        if not isinstance(api_key, str) or not api_key:
            raise ValueError("api_key must be non-empty")
        cookies = saved.get("cookies", {})
        if not isinstance(cookies, Mapping) or any(
            not isinstance(key, str) or not isinstance(value, str) for key, value in cookies.items()
        ):
            raise ValueError("cookies must be string pairs")
        clean_cookies = {
            key: value for key, value in cookies.items() if key in ALLOWED_AUTH_COOKIES
        }
        return deepcopy(dict(context)), api_key, clean_cookies

    def _load_context(self, *, initial: bool = False) -> None:
        if not self.context_path or not Path(self.context_path).is_file():
            if self.authenticated and self.strict_auth:
                raise AuthUnavailableError("Authenticated context file is unavailable")
            if self.authenticated:
                self.authenticated = False
                self.auth_status = "downgraded"
            return
        try:
            saved = json.loads(Path(self.context_path).read_text(encoding="utf-8"))
            context, api_key, cookies = self._validated_saved(saved)
            if self.authenticated and not (
                cookies.get("SAPISID") or cookies.get("__Secure-3PAPISID")
            ):
                raise AuthUnavailableError("Authenticated context has no SAPISID cookie")
        except (OSError, ValueError, json.JSONDecodeError, AuthUnavailableError) as exc:
            if self.authenticated and self.strict_auth:
                raise AuthUnavailableError(str(exc)) from exc
            if self.authenticated:
                self.authenticated = False
                self.auth_status = "downgraded"
                self.cookies = {}
            elif not initial:
                raise
            return
        self.context, self.api_key = context, api_key
        self.cookies = cookies if self.authenticated else {}
        self.auth_status = "authenticated" if self.authenticated else "public"

    def _context_payload(self) -> dict[str, Any]:
        return deepcopy(self.context)

    def _build_headers(self) -> dict[str, str]:
        origin = "https://www.youtube.com"
        headers = {
            "Content-Type": "application/json",
            "X-Origin": origin,
            "X-Youtube-Client-Name": "1",
            "X-Youtube-Client-Version": self.context["client"]["clientVersion"],
            "User-Agent": USER_AGENT,
            "Referer": f"{origin}/",
            "Origin": origin,
        }
        if not self.authenticated:
            return headers
        sapisid = self.cookies.get("SAPISID") or self.cookies.get("__Secure-3PAPISID")
        if not sapisid:
            return headers
        timestamp = int(self.clock())
        digest = hashlib.sha1(f"{timestamp} {sapisid} {origin}".encode()).hexdigest()
        headers["Authorization"] = f"SAPISIDHASH {timestamp}_{digest}"
        headers["X-Goog-AuthUser"] = "0"
        visitor = self.context["client"].get("visitorData")
        if visitor:
            headers["X-Goog-Visitor-Id"] = visitor
        return headers

    def _retry_after(self, response: Any) -> float | None:
        raw = response.headers.get("Retry-After") if hasattr(response, "headers") else None
        if not raw:
            return None
        try:
            return min(30.0, max(0.0, float(raw)))
        except ValueError:
            try:
                parsed = email.utils.parsedate_to_datetime(raw)
                return min(30.0, max(0.0, parsed.timestamp() - self.clock()))
            except (TypeError, ValueError):
                return None

    def _error_envelope(
        self,
        status: Any,
        message: Any,
        endpoint: str,
        attempts: int,
        delays: list[float],
        reason_codes: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "_error": True,
            "_status": status,
            "_message": sanitize_error_message(message),
            "_endpoint": endpoint,
            "_attempts": attempts,
            "_retry_delays": delays,
            "_reason_codes": list(reason_codes or []),
        }

    def _post(
        self,
        endpoint: str,
        body: Mapping[str, Any] | None = None,
        extra_params: Mapping[str, Any] | None = None,
        *,
        context_override: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{INNERTUBE_BASE}/{endpoint}"
        params = {"key": self.api_key, **dict(extra_params or {})}
        payload = {"context": deepcopy(context_override or self._context_payload())}
        payload.update(dict(body or {}))
        delays: list[float] = []
        attempts = 0
        for attempt in range(self.max_retries + 1):
            attempts += 1
            try:
                response = self.session.post(
                    url,
                    headers=self._build_headers(),
                    cookies=self.cookies,
                    json=payload,
                    params=params,
                    timeout=(5, 20),
                )
            except requests.RequestException as exc:
                status = (
                    "timeout"
                    if isinstance(exc, requests.Timeout)
                    else "connection_error"
                    if isinstance(exc, requests.ConnectionError)
                    else "request_error"
                )
                if attempt < self.max_retries:
                    delay = min(30.0, 2**attempt + self.random_uniform(0, 1))
                    delays.append(delay)
                    self.sleep(delay)
                    continue
                return self._error_envelope(status, exc, endpoint, attempts, delays)
            if response.status_code in RETRYABLE_CODES and attempt < self.max_retries:
                delay = self._retry_after(response)
                if delay is None:
                    delay = min(30.0, 2**attempt + self.random_uniform(0, 1))
                delays.append(delay)
                self.sleep(delay)
                continue
            if response.status_code != 200:
                code, message, reasons = response.status_code, response.text, []
                try:
                    error = response.json().get("error", {})
                    code = error.get("status") or error.get("code") or code
                    message = error.get("message") or message
                    reasons = [
                        item.get("reason")
                        for item in error.get("errors", [])
                        if isinstance(item, Mapping) and item.get("reason")
                    ]
                except (ValueError, AttributeError):
                    pass
                return self._error_envelope(code, message, endpoint, attempts, delays, reasons)
            try:
                decoded = response.json()
            except (ValueError, requests.JSONDecodeError) as exc:
                return self._error_envelope("invalid_json", exc, endpoint, attempts, delays)
            if not isinstance(decoded, dict):
                return self._error_envelope(
                    "invalid_payload_type",
                    "Decoded response must be an object",
                    endpoint,
                    attempts,
                    delays,
                )
            if self.rate_limit_seconds:
                self.sleep(self.rate_limit_seconds)
            return decoded
        raise AssertionError("retry loop exhausted unexpectedly")

    def _get(self, url: str, *, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = self.session.get(
                url,
                params=dict(params or {}),
                headers={"User-Agent": USER_AGENT},
                cookies=self.cookies,
                timeout=(5, 20),
            )
        except requests.RequestException as exc:
            status = (
                "timeout"
                if isinstance(exc, requests.Timeout)
                else "connection_error"
                if isinstance(exc, requests.ConnectionError)
                else "request_error"
            )
            return self._error_envelope(status, exc, "get", 1, [])
        if response.status_code != 200:
            return self._error_envelope(response.status_code, response.text, "get", 1, [])
        return {"_response": response, "text": response.text}

    def search(self, query=None, params=None, continuation=None):
        body = {}
        if query:
            body["query"] = query
        if params:
            body["params"] = params
        if continuation:
            body["continuation"] = continuation
        return self._post("search", body)

    def browse(self, browse_id=None, params=None, continuation=None):
        body = {}
        if browse_id:
            body["browseId"] = browse_id
        if params:
            body["params"] = params
        if continuation:
            body["continuation"] = continuation
        return self._post("browse", body)

    def next(self, video_id=None, continuation=None):
        body = {}
        if video_id:
            body["videoId"] = video_id
        if continuation:
            body["continuation"] = continuation
        return self._post("next", body)

    def player(self, video_id):
        response = self._post("player", {"videoId": video_id})
        if not response.get("_error") or not self.authenticated:
            return response
        fallback = self.page_state(video_id)
        return fallback if fallback is not None else response

    def _resolve_bridge_send(self):
        if self._bridge_send is not None:
            return self._bridge_send
        candidates = []
        configured = os.environ.get("HERMES_CHROME_BRIDGE_PATH")
        if configured:
            candidates.append(Path(configured))
        candidates.append(
            Path.home() / "Downloads" / "_projects" / "hermes-chrome-extension" / "chrome_send.py"
        )
        try:
            self._bridge_send = importlib.import_module("chrome_send").send_command
            return self._bridge_send
        except ImportError:
            pass
        for path in candidates:
            if not path.is_file():
                continue
            try:
                spec = importlib.util.spec_from_file_location("_hermes_chrome_send", path)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self._bridge_send = module.send_command
                return self._bridge_send
            except (AttributeError, ImportError, OSError):
                continue
        return None

    def page_state(self, video_id):
        """Extract watch-page state through the optional authenticated Chrome bridge."""
        if not self.authenticated:
            return None
        try:
            video_id = validate_video_id(video_id)
        except ValueError:
            return None
        send = self._resolve_bridge_send()
        if send is None:
            return None
        try:
            tabs_response = send({"type": "list_tabs"})
        except Exception:
            return None
        tabs = _bridge_value(tabs_response)
        if isinstance(tabs, dict):
            tabs = tabs.get("tabs") or tabs.get("items") or []
        if not isinstance(tabs, list):
            return None
        tab_id = None
        marker = f"watch?v={video_id}"
        for tab in tabs:
            if isinstance(tab, dict) and marker in str(tab.get("url", "")):
                tab_id = tab.get("id", tab.get("tabId"))
                break
        if tab_id is None:
            return None
        code = """
(() => {
  const findRenderer = (node) => {
    if (!node || typeof node !== "object") return null;
    if (node.videoPrimaryInfoRenderer) return node.videoPrimaryInfoRenderer;
    for (const value of Object.values(node)) {
      const found = findRenderer(value);
      if (found) return found;
    }
    return null;
  };
  const initial = window.ytInitialData || null;
  const player = window.ytInitialPlayerResponse || null;
  return JSON.stringify({
    ytInitialData: initial ? {
      videoPrimaryInfoRenderer: findRenderer(initial)
    } : null,
    ytInitialPlayerResponse: player ? {
      videoDetails: player.videoDetails || null,
      microformat: player.microformat || null
    } : null
  });
})()
"""
        try:
            raw = _bridge_value(
                send(
                    {
                        "type": "execute_js",
                        "tabId": tab_id,
                        "code": code,
                    }
                )
            )
            state = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError, json.JSONDecodeError, Exception):
            return None
        if not isinstance(state, dict):
            return None
        player = state.get("ytInitialPlayerResponse")
        player = deepcopy(player) if isinstance(player, dict) else {}
        details = player.get("videoDetails")
        details = deepcopy(details) if isinstance(details, dict) else {}
        renderer = None
        initial = state.get("ytInitialData")
        for node in _walk_dicts(initial):
            candidate = node.get("videoPrimaryInfoRenderer")
            if isinstance(candidate, dict):
                renderer = candidate
                break
        if renderer:
            title = renderer.get("title", {})
            if isinstance(title, dict):
                title_text = title.get("simpleText")
                if not title_text:
                    runs = title.get("runs")
                    if isinstance(runs, list) and runs and isinstance(runs[0], dict):
                        title_text = runs[0].get("text")
                if title_text and not details.get("title"):
                    details["title"] = title_text
            view_renderer = (
                renderer.get("viewCount", {}).get("videoViewCountRenderer", {})
                if isinstance(renderer.get("viewCount"), dict)
                else {}
            )
            view_text = (
                view_renderer.get("viewCount", {})
                if isinstance(view_renderer, dict)
                else {}
            )
            if isinstance(view_text, dict):
                raw_views = view_text.get("simpleText")
                if not raw_views:
                    runs = view_text.get("runs")
                    if isinstance(runs, list) and runs and isinstance(runs[0], dict):
                        raw_views = runs[0].get("text")
                digits = re.sub(r"\D", "", str(raw_views or ""))
                if digits and not details.get("viewCount"):
                    details["viewCount"] = digits
            if view_renderer.get("isLive"):
                details["isLiveContent"] = True
        if not details:
            return None
        player["videoDetails"] = details
        player["_page_state_fallback"] = True
        return player

    def complete(self, q, hl="en", gl="VN"):
        try:
            query = validate_query(q)
            locale = validate_locale(hl)
            region = validate_region(gl)
        except ValueError as exc:
            return {"_error": True, "_status": "invalid_input", "_message": str(exc)}
        response = self._get(
            "https://suggestqueries.google.com/complete/search",
            params={
                "client": "firefox",
                "ds": "yt",
                "q": query,
                "hl": locale,
                "gl": region,
            },
        )
        if response.get("_error"):
            return response
        text = response["text"].strip()
        try:
            if text.startswith("["):
                data = json.loads(text)
            else:
                match = re.fullmatch(r"\s*window\.google\.ac\.h\((\[.*\])\);\s*", text, re.S)
                if not match:
                    raise ValueError("invalid autocomplete JSONP wrapper")
                data = json.loads(match.group(1))
            if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list):
                raise ValueError("invalid autocomplete payload")
            return [
                item[0]
                for item in data[1]
                if isinstance(item, list) and item and isinstance(item[0], str)
            ]
        except (ValueError, json.JSONDecodeError) as exc:
            return {
                "_error": True,
                "_status": "invalid_jsonp",
                "_message": sanitize_error_message(exc),
            }

    def get_trending(self, region="VN"):
        effective = validate_region(region)
        context = self._context_payload()
        context["client"]["gl"] = effective
        return self._post(
            "browse",
            {"browseId": KNOWN_GOOD_PROFILE.browse_ids["trending"]},
            context_override=context,
        )

    def refresh_context(self):
        previous = (
            deepcopy(self.context),
            self.api_key,
            dict(self.cookies),
            self.authenticated,
            self.auth_status,
        )
        try:
            self._load_context()
        except Exception:
            (
                self.context,
                self.api_key,
                self.cookies,
                self.authenticated,
                self.auth_status,
            ) = previous
            raise
