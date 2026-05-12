from tweety_mcp.media_fetcher import _detect_format


def test_detect_format_from_extension_jpg():
    assert _detect_format("/media/abc.jpg", None) == "jpeg"


def test_detect_format_from_extension_with_query_string():
    assert _detect_format("/media/abc.png?name=large", None) == "png"


def test_detect_format_falls_back_to_content_type():
    assert _detect_format("/media/no-ext", "image/gif") == "gif"
    assert _detect_format("/media/no-ext", "image/jpeg; charset=binary") == "jpeg"


def test_detect_format_returns_none_for_unknown():
    assert _detect_format("/media/no-ext", "application/octet-stream") is None
    assert _detect_format("/media/no-ext", None) is None
