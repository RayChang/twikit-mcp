import pytest


def test_extract_post_id_from_twitter_url():
    from twikit_mcp.normalize import extract_post_id

    assert extract_post_id("https://twitter.com/user/status/12345?ref=share") == "12345"


def test_extract_post_id_from_x_url_variants():
    from twikit_mcp.normalize import extract_post_id

    assert extract_post_id("https://x.com/user/status/12345") == "12345"
    assert extract_post_id("https://www.x.com/user/status/67890?s=20") == "67890"
    assert extract_post_id("https://www.twitter.com/user/status/13579") == "13579"


def test_extract_post_id_accepts_plain_id():
    from twikit_mcp.normalize import extract_post_id

    assert extract_post_id("12345") == "12345"


def test_extract_post_id_rejects_invalid_url():
    from twikit_mcp.normalize import NormalizationError, extract_post_id

    with pytest.raises(NormalizationError):
        extract_post_id("https://example.com/user/status/12345")


def test_normalize_author_accepts_handle_and_profile_url():
    from twikit_mcp.normalize import normalize_author

    assert normalize_author("@sama") == "sama"
    assert normalize_author("https://x.com/sama") == "sama"
    assert normalize_author("https://twitter.com/sama?lang=en") == "sama"


def test_normalize_author_rejects_display_name_like_input():
    from twikit_mcp.normalize import NormalizationError, normalize_author

    with pytest.raises(NormalizationError):
        normalize_author("Sam Altman")
