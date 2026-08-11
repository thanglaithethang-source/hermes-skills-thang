import json

import pytest

from scripts.exceptions import AuthUnavailableError
from scripts.innertube import InnerTubeClient


def test_strict_auth_and_explicit_downgrade(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(AuthUnavailableError):
        InnerTubeClient(str(missing), authenticated=True)
    downgraded = InnerTubeClient(str(missing), authenticated=True, strict_auth=False)
    assert downgraded.auth_status == "downgraded"
    assert downgraded.cookies == {}


def test_valid_auth_hash_and_cookie_whitelist(tmp_path):
    path = tmp_path / "context.json"
    path.write_text(
        json.dumps(
            {
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": "1.0",
                        "hl": "en",
                        "gl": "VN",
                    }
                },
                "api_key": "test",
                "cookies": {
                    "SAPISID": "cookie-value",
                    "unrelated": "must-not-leak",
                },
            }
        ),
        encoding="utf-8",
    )
    client = InnerTubeClient(
        str(path),
        authenticated=True,
        clock=lambda: 1_000,
        rate_limit_seconds=0,
    )
    headers = client._build_headers()
    assert headers["Authorization"].startswith("SAPISIDHASH 1000_")
    assert client.cookies == {"SAPISID": "cookie-value"}
