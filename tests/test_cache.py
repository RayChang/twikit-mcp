from datetime import timedelta


def test_cache_entry_expires_after_ttl():
    from twikit_mcp.cache import TTLCache

    now = [1000.0]
    cache = TTLCache(default_ttl_seconds=1, clock=lambda: now[0])

    cache.set("key", "value")
    assert cache.get("key") == "value"

    now[0] += 1.1

    assert cache.get("key") is None


def test_cache_supports_custom_ttl():
    from twikit_mcp.cache import TTLCache

    now = [1000.0]
    cache = TTLCache(default_ttl_seconds=30, clock=lambda: now[0])

    cache.set("key", "value", ttl=timedelta(seconds=5))
    now[0] += 6

    assert cache.get("key") is None


def test_cache_can_clear_entries():
    from twikit_mcp.cache import TTLCache

    cache = TTLCache(default_ttl_seconds=30)
    cache.set("key", "value")

    cache.clear()

    assert cache.get("key") is None
