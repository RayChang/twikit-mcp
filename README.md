# twikit-mcp

Local single-user MCP server for querying X posts and authenticated bookmarks through `twikit`.

## Install

```bash
pipx install .
```

For local development:

```bash
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/twikit-mcp
```

## Authentication

Guest mode is used when no cookie config is present. To enable bookmark access, provide `auth_token` and `ct0` without storing an X password.

Cookie file:

```json
{
  "auth_token": "...",
  "ct0": "..."
}
```

Path:

```text
~/.config/twikit-mcp/cookies.json
```

Environment variables override the file:

```bash
export TWIKIT_MCP_AUTH_TOKEN="..."
export TWIKIT_MCP_CT0="..."
```

## Tools

- `x_search_posts`
- `x_get_post`
- `x_get_bookmarks`

`x_get_bookmarks` requires cookie-auth mode. Search and post lookup can run in guest mode when X allows the public request.

## MCP Host Configuration

Use stdio transport:

```json
{
  "mcpServers": {
    "twikit-mcp": {
      "command": "twikit-mcp",
      "args": []
    }
  }
}
```

## Smoke Flow

1. Start without cookie config and call `x_search_posts` with `query="Taylor Swift"` and `limit=5`.
2. Call `x_get_post` with a post URL returned by search.
3. Add `~/.config/twikit-mcp/cookies.json`.
4. Restart the MCP host and call `x_get_bookmarks` with `query`, `author`, `since`, `until`, or `lang` filters.

## Notes

- Timestamps returned by schemas are ISO 8601 UTC.
- Bookmark `since` and `until` filter by the post creation time, not the time the bookmark was added.
- Filtered bookmark search is best effort and scans at most five pages per request.
