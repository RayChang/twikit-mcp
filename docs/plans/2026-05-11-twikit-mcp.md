# Twikit MCP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local single-user Python MCP server for querying X posts and bookmarks through `twikit`, using `stdio` transport and a JSON-first schema optimized for LLM analysis.

**Architecture:** The server is a thin `FastMCP` wrapper around a small service layer that normalizes inputs, selects guest or authenticated `twikit` clients, maps upstream data into stable JSON schemas, and converts failures into explicit MCP error codes. The implementation stays intentionally narrow: three tools, bounded filtering, short-lived in-memory cache, and no persistent state.

**Tech Stack:** Python 3.11+, `twikit`, `mcp` Python SDK, `pytest`, `pytest-asyncio`, `pydantic`

---

### Task 1: Scaffold package and test harness

**Files:**
- Create: `pyproject.toml`
- Create: `src/twikit_mcp/__init__.py`
- Create: `src/twikit_mcp/server.py`
- Create: `tests/conftest.py`
- Create: `tests/test_smoke_import.py`

**Step 1: Write the failing test**

```python
def test_server_module_imports():
    from twikit_mcp.server import build_mcp

    assert callable(build_mcp)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_smoke_import.py -v`
Expected: FAIL with import error for `twikit_mcp`

**Step 3: Write minimal implementation**

- Add package metadata and dependencies in `pyproject.toml`
- Add a `twikit-mcp` console script entrypoint
- Add `build_mcp()` placeholder in `server.py`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_smoke_import.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml src/twikit_mcp/__init__.py src/twikit_mcp/server.py tests/conftest.py tests/test_smoke_import.py
git commit -m "chore: scaffold twikit mcp package"
```

### Task 2: Implement config loading and auth mode detection

**Files:**
- Create: `src/twikit_mcp/config.py`
- Create: `src/twikit_mcp/auth.py`
- Create: `tests/test_config.py`

**Step 1: Write the failing test**

```python
def test_guest_mode_when_no_cookie_sources(monkeypatch, tmp_path):
    from twikit_mcp.config import load_runtime_config

    monkeypatch.delenv("TWIKIT_MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWIKIT_MCP_CT0", raising=False)

    config = load_runtime_config(config_dir=tmp_path)
    assert config.mode == "guest"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL because `load_runtime_config` does not exist

**Step 3: Write minimal implementation**

- Read env vars first
- Fallback to `cookies.json`
- Validate `auth_token` and `ct0` shape
- Return normalized runtime config with `mode in {"guest", "cookie-auth"}`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/twikit_mcp/config.py src/twikit_mcp/auth.py tests/test_config.py
git commit -m "feat: add config and auth mode detection"
```

### Task 3: Define errors and shared schemas

**Files:**
- Create: `src/twikit_mcp/errors.py`
- Create: `src/twikit_mcp/models.py`
- Create: `tests/test_models.py`

**Step 1: Write the failing test**

```python
def test_search_post_summary_uses_iso_utc_timestamp():
    from twikit_mcp.models import SearchPostSummary

    item = SearchPostSummary(
        id="1",
        url="https://x.com/a/status/1",
        text="hello",
        created_at="2026-05-11T00:00:00Z",
        lang="en",
        favorite_count=1,
        retweet_count=2,
        reply_count=3,
        quote_count=4,
        has_media=False,
        is_reply=False,
        is_quote=False,
        is_retweet=False,
        author={"name": "A", "handle": "a", "verified": False},
    )

    assert item.created_at.endswith("Z")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL because schema classes do not exist

**Step 3: Write minimal implementation**

- Define Pydantic models for:
  - author
  - search result item
  - bookmark listing item
  - full post payload
  - list responses
- Define structured error helpers for required error codes

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/twikit_mcp/errors.py src/twikit_mcp/models.py tests/test_models.py
git commit -m "feat: add shared schemas and error codes"
```

### Task 4: Build normalization and query composition helpers

**Files:**
- Create: `src/twikit_mcp/normalize.py`
- Create: `src/twikit_mcp/query.py`
- Create: `tests/test_normalize.py`
- Create: `tests/test_query.py`

**Step 1: Write the failing tests**

```python
def test_extract_post_id_from_twitter_url():
    from twikit_mcp.normalize import extract_post_id

    assert extract_post_id("https://twitter.com/user/status/12345?ref=share") == "12345"


def test_compose_query_with_author():
    from twikit_mcp.query import compose_search_query

    assert compose_search_query(query="AI", author="@sama") == "AI from:sama"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_normalize.py tests/test_query.py -v`
Expected: FAIL because helper modules do not exist

**Step 3: Write minimal implementation**

- Normalize author input from `@handle` or profile URL
- Normalize post URLs from X/Twitter variants
- Validate `since <= until`
- Compose internal query strings without exposing raw query DSL in tool inputs

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_normalize.py tests/test_query.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/twikit_mcp/normalize.py src/twikit_mcp/query.py tests/test_normalize.py tests/test_query.py
git commit -m "feat: add query and url normalization helpers"
```

### Task 5: Add client factory and lightweight cache

**Files:**
- Create: `src/twikit_mcp/cache.py`
- Create: `src/twikit_mcp/client_factory.py`
- Create: `tests/test_cache.py`
- Create: `tests/test_client_factory.py`

**Step 1: Write the failing test**

```python
def test_cache_entry_expires_after_ttl():
    from twikit_mcp.cache import TTLCache

    cache = TTLCache(default_ttl_seconds=1)
    cache.set("key", "value")
    assert cache.get("key") == "value"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cache.py tests/test_client_factory.py -v`
Expected: FAIL because cache and factory classes do not exist

**Step 3: Write minimal implementation**

- Add small in-memory TTL cache abstraction
- Build guest vs auth `twikit` clients from runtime config
- Translate config/auth failures into internal service exceptions

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cache.py tests/test_client_factory.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/twikit_mcp/cache.py src/twikit_mcp/client_factory.py tests/test_cache.py tests/test_client_factory.py
git commit -m "feat: add twikit client factory and cache"
```

### Task 6: Implement upstream mapping service

**Files:**
- Create: `src/twikit_mcp/service.py`
- Create: `tests/test_service_mapping.py`
- Create: `tests/test_error_mapping.py`

**Step 1: Write the failing test**

```python
def test_map_tweet_to_search_summary():
    from twikit_mcp.service import map_tweet_to_search_summary

    tweet = type("Tweet", (), {})()
    tweet.id = "1"
    tweet.text = "hello"

    result = map_tweet_to_search_summary(tweet)
    assert result.id == "1"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_service_mapping.py tests/test_error_mapping.py -v`
Expected: FAIL because service helpers do not exist

**Step 3: Write minimal implementation**

- Map `twikit` tweet-like objects into stable JSON schemas
- Normalize timestamps to ISO 8601 UTC
- Map upstream exceptions to:
  - `AUTH_REQUIRED`
  - `AUTH_EXPIRED`
  - `INVALID_POST_URL`
  - `INVALID_ARGUMENT`
  - `RATE_LIMITED`
  - `NOT_FOUND`
  - `UPSTREAM_CHANGED`
  - `PARTIAL_RESULTS`
  - `INTERNAL_ERROR`

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_service_mapping.py tests/test_error_mapping.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/twikit_mcp/service.py tests/test_service_mapping.py tests/test_error_mapping.py
git commit -m "feat: add twikit service layer and error mapping"
```

### Task 7: Implement `x_search_posts`

**Files:**
- Modify: `src/twikit_mcp/service.py`
- Modify: `src/twikit_mcp/server.py`
- Create: `tests/test_x_search_posts.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_x_search_posts_returns_summary_listing():
    from twikit_mcp.service import SearchService

    service = SearchService(...)
    result = await service.search_posts(query="AI", limit=20)

    assert "items" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_x_search_posts.py -v`
Expected: FAIL because `search_posts` is not implemented

**Step 3: Write minimal implementation**

- Compose normalized query
- Call guest or auth client search
- Map sort values to upstream search modes
- Return summary items plus cursor metadata
- Register the tool in `FastMCP`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_x_search_posts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/twikit_mcp/service.py src/twikit_mcp/server.py tests/test_x_search_posts.py
git commit -m "feat: add x_search_posts tool"
```

### Task 8: Implement `x_get_post`

**Files:**
- Modify: `src/twikit_mcp/service.py`
- Modify: `src/twikit_mcp/server.py`
- Create: `tests/test_x_get_post.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_x_get_post_accepts_twitter_url():
    from twikit_mcp.service import PostService

    service = PostService(...)
    result = await service.get_post(url="https://twitter.com/user/status/123")

    assert result["id"] == "123"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_x_get_post.py -v`
Expected: FAIL because `get_post` is not implemented

**Step 3: Write minimal implementation**

- Accept URL or ID
- Normalize post ID
- Fetch the target post
- Map one-level quote and reply context
- Return the full analysis-oriented schema
- Register the tool in `FastMCP`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_x_get_post.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/twikit_mcp/service.py src/twikit_mcp/server.py tests/test_x_get_post.py
git commit -m "feat: add x_get_post tool"
```

### Task 9: Implement `x_get_bookmarks`

**Files:**
- Modify: `src/twikit_mcp/service.py`
- Modify: `src/twikit_mcp/server.py`
- Create: `tests/test_x_get_bookmarks.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_x_get_bookmarks_requires_auth():
    from twikit_mcp.service import BookmarkService
    from twikit_mcp.errors import AuthRequiredError

    service = BookmarkService(mode="guest", ...)

    with pytest.raises(AuthRequiredError):
        await service.get_bookmarks(limit=20)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_x_get_bookmarks.py -v`
Expected: FAIL because bookmark service is not implemented

**Step 3: Write minimal implementation**

- Gate tool to authenticated mode
- Page through bookmarks
- Apply local filters:
  - query
  - author
  - since
  - until
  - lang
- Cap filtered scans at 5 pages
- Return `partial` and `scanned_pages`
- Register the tool in `FastMCP`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_x_get_bookmarks.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/twikit_mcp/service.py src/twikit_mcp/server.py tests/test_x_get_bookmarks.py
git commit -m "feat: add x_get_bookmarks tool"
```

### Task 10: Add CLI entrypoint, logging, and smoke verification

**Files:**
- Modify: `src/twikit_mcp/server.py`
- Create: `src/twikit_mcp/logging_utils.py`
- Create: `tests/test_logging.py`
- Create: `README.md`

**Step 1: Write the failing test**

```python
def test_logging_redacts_auth_token():
    from twikit_mcp.logging_utils import redact_secrets

    redacted = redact_secrets({"auth_token": "secret"})
    assert redacted["auth_token"] == "***REDACTED***"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_logging.py -v`
Expected: FAIL because redaction helpers do not exist

**Step 3: Write minimal implementation**

- Add redaction helpers
- Add CLI `main()` that runs `FastMCP` with `stdio`
- Document installation and MCP host configuration examples
- Document a manual smoke flow:
  - start in guest mode
  - call `x_search_posts`
  - call `x_get_post`
  - start in cookie-auth mode
  - call `x_get_bookmarks`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_logging.py -v`
Expected: PASS

**Step 5: Run the full test suite**

Run: `pytest -v`
Expected: PASS for the complete suite

**Step 6: Commit**

```bash
git add src/twikit_mcp/server.py src/twikit_mcp/logging_utils.py tests/test_logging.py README.md
git commit -m "feat: finalize stdio server entrypoint and docs"
```

Plan complete and saved to `docs/plans/2026-05-11-twikit-mcp.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
