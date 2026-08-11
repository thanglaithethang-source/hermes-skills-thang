from scripts.video import VideoModule


def test_like_and_comment_structured_extractors():
    module = VideoModule.__new__(VideoModule)
    entity = {
        "frameworkUpdates": {
            "entityBatchUpdate": {
                "mutations": [
                    {"payload": {"likeCountEntity": {"likeCountIfIndifferentNumber": "123"}}}
                ]
            }
        }
    }
    assert module._extract_like_count(entity) == 123
    fallback = {"button": {"iconName": "LIKE", "title": "456"}}
    assert module._extract_like_count(fallback) == 456
    comments = {
        "engagementPanels": [
            {
                "engagementPanelSectionListRenderer": {
                    "panelIdentifier": "engagement-panel-comments-section",
                    "header": {
                        "engagementPanelTitleHeaderRenderer": {
                            "contextualInfo": {"runs": [{"text": "1,2 Tr"}]}
                        }
                    },
                }
            }
        ]
    }
    assert module._extract_comment_count(comments) == 1_200_000
    assert module._extract_comment_count({"engagementPanels": []}) is None
