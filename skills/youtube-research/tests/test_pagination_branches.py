from scripts.models import ParseDiagnostics, ParsedPage
from scripts.pagination import collect_pages


def page(
    items=None,
    token=None,
    *,
    recognized=True,
    candidates=None,
    parsed=None,
    invalid=0,
    unknown=(),
    truncated=False,
):
    items = items or []
    return ParsedPage(
        items,
        token,
        ParseDiagnostics(
            surface="search",
            response_kind="initial",
            recognized_container=recognized,
            container_path="path" if recognized else None,
            candidate_nodes=len(items) if candidates is None else candidates,
            parsed_nodes=len(items) if parsed is None else parsed,
            invalid_nodes=invalid,
            unknown_renderer_types=tuple(unknown),
            continuation_token_present=bool(token),
            shape_fingerprint="abc",
        ),
        truncated,
    )


def test_paginator_malformed_repeated_coverage_and_caps():
    malformed = collect_pages(
        lambda _token: [],
        lambda _data: page(),
        limit=1,
        max_pages=1,
        identity=lambda row: row["id"],
    )
    assert malformed.status == "error"
    unsupported = collect_pages(
        lambda _token: {},
        lambda _data: page(recognized=True, candidates=1, parsed=0),
        limit=1,
        max_pages=1,
        identity=lambda row: row["id"],
    )
    assert unsupported.status == "unsupported"
    coverage = collect_pages(
        lambda _token: {},
        lambda _data: page([{"id": "one"}], token="next", invalid=1, truncated=True),
        limit=2,
        max_pages=2,
        identity=lambda row: row["id"],
    )
    assert coverage.status == "partial"
    assert coverage.metadata["parser_diagnostics"][0]["fingerprint_truncated"]

    calls = 0

    def repeated_fetch(_token):
        return {}

    def repeated_parse(_data):
        nonlocal calls
        calls += 1
        return page(
            [{"id": str(calls)}] if calls == 1 else [{"id": "two"}],
            token="same",
        )

    repeated = collect_pages(
        repeated_fetch,
        repeated_parse,
        limit=5,
        max_pages=5,
        identity=lambda row: row["id"],
    )
    assert repeated.metadata["stop_reason"] == "repeated_token"
    capped = collect_pages(
        lambda _token: {},
        lambda _data: page([{"id": "one"}], token="next"),
        limit=5,
        max_pages=1,
        identity=lambda row: row["id"],
    )
    assert capped.metadata["stop_reason"] == "page_cap"
    limited = collect_pages(
        lambda _token: {},
        lambda _data: page([{"id": "one"}], token="next"),
        limit=1,
        max_pages=2,
        identity=lambda row: row["id"],
    )
    assert limited.metadata["stop_reason"] == "limit"
