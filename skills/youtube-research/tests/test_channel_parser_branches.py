from scripts.channel import ChannelModule


def test_new_channel_header_and_metadata_paths():
    payload = {
        "header": {
            "pageHeaderRenderer": {
                "content": {
                    "pageHeaderViewModel": {
                        "title": {"dynamicTextViewModel": {"text": {"content": "Channel Name"}}},
                        "metadata": {
                            "contentMetadataViewModel": {
                                "metadataRows": [
                                    {
                                        "metadataParts": [
                                            {"text": {"content": "1,2 Tr người đăng ký"}},
                                            {"text": {"content": "1.234 videos"}},
                                        ]
                                    }
                                ]
                            }
                        },
                    }
                }
            }
        },
        "metadata": {
            "channelMetadataRenderer": {
                "externalId": "UC12345678901234567890",
                "description": "Description",
                "country": "VN",
                "keywords": "ai, tools",
            }
        },
    }
    item = ChannelModule.__new__(ChannelModule)._parse_channel_browse(
        payload, "UC12345678901234567890"
    )
    assert item["name"] == "Channel Name"
    assert item["subscriber_count"] == 1_200_000
    assert item["video_count"] == 1234
    assert item["tags"] == ["ai", "tools"]


def test_old_header_and_tab_video_count_fallback():
    payload = {
        "header": {
            "c4TabbedHeaderRenderer": {
                "title": "Old Channel",
                "subscriberCountText": {"simpleText": "10 subscribers"},
            }
        },
        "contents": {
            "twoColumnBrowseResultsRenderer": {
                "tabs": [
                    {
                        "tabRenderer": {
                            "title": "Videos",
                            "content": {
                                "richGridRenderer": {
                                    "header": {
                                        "feedFilterChipBarRenderer": {
                                            "contents": [
                                                {
                                                    "chipCloudChipRenderer": {
                                                        "text": {"simpleText": "25 videos"}
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            },
                        }
                    }
                ]
            }
        },
    }
    item = ChannelModule.__new__(ChannelModule)._parse_channel_browse(
        payload, "UC12345678901234567890"
    )
    assert item["name"] == "Old Channel"
    assert item["subscriber_count"] == 10
    assert item["video_count"] == 25
