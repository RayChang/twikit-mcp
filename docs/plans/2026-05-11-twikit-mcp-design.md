# Twikit MCP Design

**Date:** 2026-05-11

## Goal

Build a local single-user MCP server on top of `twikit` for querying X posts in a way that is reliable for LLM analysis workflows.

## Product Boundary

- Local single-user only
- `stdio` transport only in v1
- Tools only; no MCP resources or prompts
- Read-focused scope
- No posting, likes, retweets, follows, DMs, or account management

## Supported Modes

### Guest mode

- Backed by `twikit.GuestClient`
- Default mode when no cookie config is present
- Supports:
  - `x_search_posts`
  - `x_get_post`

### Cookie-auth mode

- Backed by authenticated `twikit.Client`
- Activated when valid cookie configuration is present
- Supports:
  - `x_search_posts`
  - `x_get_post`
  - `x_get_bookmarks`

### Explicit non-goals

- No username/password login
- No 2FA handling
- No browser automation
- No shared multi-user deployment

## Authentication

The server accepts only `auth_token` and `ct0`.

### Cookie file

Path:

`~/.config/twikit-mcp/cookies.json`

Format:

```json
{
  "auth_token": "...",
  "ct0": "..."
}
```

### Environment variables

- `TWIKIT_MCP_AUTH_TOKEN`
- `TWIKIT_MCP_CT0`

### Startup behavior

- Read local config only
- Validate shape locally
- Do not call X during startup
- If cookie config is absent, fall back to guest mode
- If cookie config is malformed, fail startup with a clear config error
- If cookie config is well-formed but expired, detect on first authenticated request and return `AUTH_EXPIRED`

## Tool Surface

### `x_search_posts`

Purpose:
Search X posts by keyword or hashtag for initial retrieval and ranking by the upstream X search surface.

Input:

- `query: string`
- `author?: string`
- `sort?: "top" | "latest" | "media"`
- `since?: string`
- `until?: string`
- `lang?: string`
- `limit?: integer`
- `cursor?: string`

Rules:

- `author` accepts either `@handle` or an X/Twitter profile URL
- No raw X query DSL is exposed in v1
- `since` and `until` accept `YYYY-MM-DD` or ISO 8601 input
- `limit` default is `20`
- `limit` max is `50`
- Results use cursor-based pagination only
- Sorting maps directly to X/twikit behavior; no custom re-ranking

Output shape:

- `items`
- `next_cursor`
- `count`
- `mode`

Each item includes:

- `id`
- `url`
- `text`
- `created_at`
- `lang`
- `author`
- `favorite_count`
- `retweet_count`
- `reply_count`
- `quote_count`
- `has_media`
- `is_reply`
- `is_quote`
- `is_retweet`

### `x_get_post`

Purpose:
Return a single LLM-friendly post analysis package from a post URL or ID.

Input:

- `url?: string`
- `id?: string`

Rules:

- Exactly one of `url` or `id` should be provided
- URL normalization supports:
  - `https://x.com/...`
  - `https://www.x.com/...`
  - `https://twitter.com/...`
  - `https://www.twitter.com/...`
  - URLs with query strings

Output shape:

- `id`
- `url`
- `text`
- `created_at`
- `lang`
- `author`
- `favorite_count`
- `retweet_count`
- `reply_count`
- `quote_count`
- `view_count` when available
- `hashtags`
- `urls`
- `mentions`
- `media`
- `is_reply`
- `in_reply_to_status_id`
- `in_reply_to_user`
- `is_quote`
- `quoted_post`
- `is_retweet`
- `retweeted_post`

Behavior notes:

- Return full post text, not truncated text
- Expand quoted post one level only
- Include reply context identifiers, but do not expand full conversation threads
- Include media summary data suitable for downstream LLM interpretation

### `x_get_bookmarks`

Purpose:
Retrieve bookmarked posts for the authenticated user with local filtering.

Input:

- `query?: string`
- `author?: string`
- `since?: string`
- `until?: string`
- `lang?: string`
- `limit?: integer`
- `cursor?: string`

Rules:

- Auth-required tool
- `since` and `until` filter on bookmarked post `created_at`
- No support for "bookmark added at" in v1
- Local best-effort filtering across bookmark pages
- If any filter is present, scan up to 5 bookmark pages internally
- Return partial metadata when scan limits are hit

Output shape:

- `items`
- `next_cursor`
- `count`
- `partial`
- `scanned_pages`
- `mode`

Each bookmark item uses the same summary-oriented shape as `x_search_posts`.

## Query Normalization

Natural-language-friendly MCP usage is the design goal, so the server should expose structured parameters instead of raw X query syntax.

Internal normalization rules:

- `author="@sama"` -> `sama`
- `author="https://x.com/sama"` -> `sama`
- hashtag input stays in `query`
- search text is internally composed with X syntax only inside the implementation layer

Example:

- `query="AI"`
- `author="@sama"`
- composed query becomes `AI from:sama`

## Data Conventions

### Time

- All returned timestamps must be normalized to ISO 8601 UTC
- Preserve raw upstream time only if needed for debug internals, not as primary schema

### JSON-first output

- MCP responses are structured JSON only
- No server-side summarization
- No natural-language report generation in tool output

## Error Model

All tool failures should map into structured MCP errors with stable codes.

Required codes:

- `AUTH_REQUIRED`
- `AUTH_EXPIRED`
- `INVALID_POST_URL`
- `INVALID_ARGUMENT`
- `RATE_LIMITED`
- `NOT_FOUND`
- `UPSTREAM_CHANGED`
- `PARTIAL_RESULTS`
- `INTERNAL_ERROR`

Expected semantics:

- `AUTH_REQUIRED`: user called auth-only tool without authenticated mode
- `AUTH_EXPIRED`: configured cookie session is no longer valid
- `INVALID_ARGUMENT`: bad parameters such as `since > until`
- `RATE_LIMITED`: upstream rate-limited request; do not long-wait in tool execution
- `PARTIAL_RESULTS`: request succeeded, but only a bounded scan was completed

## Retry and Rate Limiting

Documented `twikit` search requests are rate-limited on a 15-minute window. The MCP server should therefore remain conservative.

Behavior:

- Retry short-lived network failures at most 2 times with exponential backoff
- Do not long-wait on upstream rate limits
- Return `RATE_LIMITED` immediately when the server can infer that state
- Do not retry `AUTH_EXPIRED`
- Do not retry `UPSTREAM_CHANGED`

## Caching

Only light in-memory caching is in scope.

Rules:

- Process-local only
- No persistent disk cache
- No bookmark index
- Short TTL, roughly 30-120 seconds
- Safe targets:
  - repeated `x_get_post(id)`
  - repeated identical `x_search_posts(...)`

## Logging and Secret Handling

Default logging must be conservative.

Rules:

- Default level `INFO`
- Never log:
  - `auth_token`
  - `ct0`
  - raw cookie file contents
  - full bookmark payloads
- Redact values for:
  - `auth_token`
  - `ct0`
  - `Authorization`
  - `Cookie`
- Permit more detail only in debug mode, while preserving redaction

## Package and Runtime Layout

v1 should ship as an installable Python package with a single CLI entrypoint:

- package name: `twikit-mcp`
- executable: `twikit-mcp`

Planned top-level structure:

- `pyproject.toml`
- `src/twikit_mcp/`
- `tests/`
- `docs/plans/`

## Recommended Internal Modules

- `config.py`
- `auth.py`
- `models.py`
- `errors.py`
- `cache.py`
- `query.py`
- `normalize.py`
- `client_factory.py`
- `service.py`
- `server.py`

## Testing Baseline

Minimum v1 test coverage:

- URL normalization tests
- query composition tests
- auth mode tests
- response schema tests
- error mapping tests

Manual smoke checks should be documented, but CI should rely primarily on deterministic unit tests with mocks and fixtures rather than live X calls.

## Non-Goals for v1

- Remote HTTP transport
- Shared server mode
- Raw X search DSL exposure
- Conversation thread expansion
- True bookmark-added timestamp
- Full bookmark indexing
- Write actions on X

## Recommended Next Step

Use this design as the basis for an implementation plan and keep the first release intentionally thin: one server, three tools, strict auth boundaries, strong schema discipline, and no unnecessary product surface.
