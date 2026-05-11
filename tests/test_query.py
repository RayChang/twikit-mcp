import pytest


def test_compose_query_with_author():
    from twikit_mcp.query import compose_search_query

    assert compose_search_query(query="AI", author="@sama") == "AI from:sama"


def test_compose_query_with_optional_filters():
    from twikit_mcp.query import compose_search_query

    assert (
        compose_search_query(
            query="#WWDC",
            author="https://x.com/apple",
            since="2026-06-01",
            until="2026-06-08",
            lang="en",
        )
        == "#WWDC from:apple since:2026-06-01 until:2026-06-08 lang:en"
    )


def test_compose_query_normalizes_iso_datetime_filters_to_dates():
    from twikit_mcp.query import compose_search_query

    assert (
        compose_search_query(
            query="Taylor Swift",
            since="2026-05-01T12:30:00+08:00",
            until="2026-05-08T00:00:00Z",
        )
        == "Taylor Swift since:2026-05-01 until:2026-05-08"
    )


def test_validate_time_range_rejects_since_after_until():
    from twikit_mcp.query import QueryError, compose_search_query

    with pytest.raises(QueryError):
        compose_search_query(query="AI", since="2026-06-08", until="2026-06-01")


def test_validate_time_range_rejects_invalid_dates():
    from twikit_mcp.query import QueryError, compose_search_query

    with pytest.raises(QueryError):
        compose_search_query(query="AI", since="not-a-date", until="2026-06-01")


def test_normalize_sort_maps_to_twikit_search_modes():
    from twikit_mcp.query import normalize_sort

    assert normalize_sort(None) == "Latest"
    assert normalize_sort("latest") == "Latest"
    assert normalize_sort("top") == "Top"
    assert normalize_sort("media") == "Media"


def test_normalize_sort_rejects_unknown_values():
    from twikit_mcp.query import QueryError, normalize_sort

    with pytest.raises(QueryError):
        normalize_sort("popular")
