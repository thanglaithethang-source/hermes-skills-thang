from scripts.parsers import (
    extract_continuation_token,
    parse_any_video,
    parse_lockup_video,
    parse_video_page,
)


def lockup():
    return {
        "contentType": "LOCKUP_CONTENT_TYPE_VIDEO",
        "contentId": "video000001",
        "metadata": {
            "lockupMetadataViewModel": {
                "title": {"content": "Vietnam AI"},
                "metadata": {
                    "contentMetadataViewModel": {
                        "metadataRows": [
                            {
                                "metadataParts": [
                                    {"text": {"content": "Channel"}},
                                    {"text": {"content": "1,2 Tr lượt xem"}},
                                    {"text": {"content": "2 tuần trước"}},
                                ]
                            }
                        ]
                    }
                },
                "image": {
                    "decoratedAvatarViewModel": {
                        "rendererContext": {
                            "commandContext": {
                                "onTap": {
                                    "innertubeCommand": {
                                        "browseEndpoint": {"browseId": "UC12345678901234567890"}
                                    }
                                }
                            }
                        }
                    }
                },
            }
        },
        "contentImage": {
            "thumbnailViewModel": {
                "overlays": [
                    {
                        "thumbnailBottomOverlayViewModel": {
                            "badges": [{"thumbnailBadgeViewModel": {"text": "12:34"}}]
                        }
                    }
                ]
            }
        },
    }


def test_lockup_and_renderer_variants():
    row = parse_lockup_video(lockup())
    assert row["view_count"] == 1_200_000
    assert row["duration_seconds"] == 754
    assert row["published_raw"] == "2 tuần trước"
    assert parse_lockup_video({"contentType": "PLAYLIST"}) is None
    assert parse_any_video({"futureRenderer": {}}) is None
    grid = parse_any_video(
        {
            "gridVideoRenderer": {
                "videoId": "video000002",
                "title": {"simpleText": "Grid"},
                "viewCountText": {"simpleText": "0 views"},
                "lengthText": {"simpleText": "1:00"},
            }
        }
    )
    assert grid["views"] == 0


def test_continuation_action_variants():
    data = {
        "onResponseReceivedActions": [
            {
                "reloadContinuationItemsCommand": {
                    "continuationItems": [
                        {
                            "continuationItemRenderer": {
                                "continuationEndpoint": {"continuationCommand": {"token": "NEXT"}}
                            }
                        }
                    ]
                }
            }
        ]
    }
    page = parse_video_page(data, surface="search")
    assert page.diagnostics.response_kind == "continuation"
    assert page.continuation_token == "NEXT"
    assert extract_continuation_token(data) == "NEXT"
