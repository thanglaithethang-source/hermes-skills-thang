from scripts.innertube import sanitize_error_message


def test_error_message_removes_sensitive_material():
    unsafe = (
        "Bearer secret-token cookie=session123 api_key=key123 "
        "person@example.com https://example.com/path?q=secret "
        "<b>failure</b>\x00" + "x" * 500
    )
    safe = sanitize_error_message(unsafe)
    for secret in (
        "secret-token",
        "session123",
        "key123",
        "person@example.com",
        "example.com",
        "<b>",
        "\x00",
    ):
        assert secret not in safe
    assert len(safe) <= 200
