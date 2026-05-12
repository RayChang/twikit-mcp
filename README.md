# twikit-mcp

Local single-user MCP server for querying X posts and authenticated bookmarks through [`twikit`](https://github.com/d60/twikit).

This server is designed for local agent workflows. It exposes read-only tools over MCP `stdio`:

- `x_search_posts`
- `x_get_post`
- `x_get_bookmarks`

It does not post, like, retweet, follow, send DMs, or store X passwords.

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) for no-install `uvx` usage
- A local MCP host that supports `stdio`
- Optional: X browser cookies `auth_token` and `ct0` for bookmark access

## Run Without Installing

Recommended for MCP hosts:

```bash
uvx --from "git+https://github.com/RayChang/twikit-mcp.git" twikit-mcp
```

This does not install a persistent `twikit-mcp` command. `uvx` downloads/builds the package on first run, stores it in uv's cache, and runs the MCP stdio server.

`twikit-mcp` is an MCP stdio server, so running it directly will wait for MCP JSON-RPC messages on stdin. Use it through an MCP host rather than as an interactive CLI.

## Optional Persistent Install

If you prefer a persistent local command:

```bash
pipx install "git+https://github.com/RayChang/twikit-mcp.git"
```

Or with `uv`:

```bash
uv tool install "git+https://github.com/RayChang/twikit-mcp.git"
```

Or with `pip`:

```bash
python -m pip install "git+https://github.com/RayChang/twikit-mcp.git"
```

For local development from a checkout:

```bash
git clone https://github.com/RayChang/twikit-mcp.git
cd twikit-mcp
python -m pip install -e .
```

If you use a persistent install, verify that the command is available:

```bash
which twikit-mcp
```

## Authentication

The server starts in guest mode when no cookies are configured. Guest mode can use:

- `x_search_posts`
- `x_get_post`

Bookmark access requires cookie-auth mode:

- `x_get_bookmarks`

The server only reads `auth_token` and `ct0`. It does not ask for your X username, password, or 2FA code.

Create:

```text
~/.config/twikit-mcp/cookies.json
```

With:

```json
{
  "auth_token": "...",
  "ct0": "..."
}
```

Environment variables override the file:

```bash
export TWIKIT_MCP_AUTH_TOKEN="..."
export TWIKIT_MCP_CT0="..."
```

If cookies expire, grab fresh `auth_token` and `ct0` from your browser DevTools and update the file or environment variables.

## Agent CLI Setup

The examples below use `uvx`, so users do not need to install `twikit-mcp` first. If you use a persistent install instead, set `command` to `twikit-mcp` and set `args` to `[]`.

### Codex CLI

Codex can run the server from `~/.codex/config.toml`:

```toml
[mcp_servers.twikit-mcp]
command = "uvx"
args = ["--from", "git+https://github.com/RayChang/twikit-mcp.git", "twikit-mcp"]
```

With cookie environment variables:

```toml
[mcp_servers.twikit-mcp]
command = "uvx"
args = ["--from", "git+https://github.com/RayChang/twikit-mcp.git", "twikit-mcp"]
env = { TWIKIT_MCP_AUTH_TOKEN = "...", TWIKIT_MCP_CT0 = "..." }
```

If your Codex CLI accepts full command strings, this command-line registration is also possible:

```bash
codex mcp add twikit-mcp --transport stdio --command "uvx --from git+https://github.com/RayChang/twikit-mcp.git twikit-mcp"
```

Check registration:

```bash
codex mcp list
```

Remove it:

```bash
codex mcp remove twikit-mcp
```

### Claude Code

Add a local stdio MCP server entry. For project-local configuration, create or edit `.mcp.json` in the project where Claude Code should use the server:

```json
{
  "twikit-mcp": {
    "command": "uvx",
    "args": ["--from", "git+https://github.com/RayChang/twikit-mcp.git", "twikit-mcp"]
  }
}
```

If you prefer environment variables instead of `~/.config/twikit-mcp/cookies.json`:

```json
{
  "twikit-mcp": {
    "command": "uvx",
    "args": ["--from", "git+https://github.com/RayChang/twikit-mcp.git", "twikit-mcp"],
    "env": {
      "TWIKIT_MCP_AUTH_TOKEN": "${TWIKIT_MCP_AUTH_TOKEN}",
      "TWIKIT_MCP_CT0": "${TWIKIT_MCP_CT0}"
    }
  }
}
```

Restart Claude Code after changing MCP config.

### Gemini CLI

Gemini CLI supports adding a local stdio MCP server from the command line:

```bash
gemini mcp add twikit-mcp uvx --from "git+https://github.com/RayChang/twikit-mcp.git" twikit-mcp
```

Or configure it in Gemini CLI `settings.json`:

```json
{
  "mcpServers": {
    "twikit-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/RayChang/twikit-mcp.git", "twikit-mcp"],
      "timeout": 30000,
      "trust": false
    }
  }
}
```

With cookie environment variables:

```json
{
  "mcpServers": {
    "twikit-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/RayChang/twikit-mcp.git", "twikit-mcp"],
      "env": {
        "TWIKIT_MCP_AUTH_TOKEN": "$TWIKIT_MCP_AUTH_TOKEN",
        "TWIKIT_MCP_CT0": "$TWIKIT_MCP_CT0"
      },
      "timeout": 30000,
      "trust": false
    }
  }
}
```

### Generic MCP Stdio Hosts

For MCP hosts that accept an `mcpServers` JSON block:

```json
{
  "mcpServers": {
    "twikit-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/RayChang/twikit-mcp.git", "twikit-mcp"]
    }
  }
}
```

For hosts that only support remote HTTP MCP servers, this project will not work directly until an HTTP transport is added.

## Tools

### `x_search_posts`

Search public X posts by keyword or hashtag.

Inputs:

- `query`: keyword, phrase, or hashtag
- `author`: optional `@handle` or profile URL
- `sort`: optional `latest`, `top`, or `media`
- `since`: optional `YYYY-MM-DD` or ISO 8601
- `until`: optional `YYYY-MM-DD` or ISO 8601
- `lang`: optional language code such as `en`, `ja`, or `zh`
- `limit`: optional, default `20`, max `50`
- `cursor`: optional cursor returned by a previous call

Example prompts:

```text
Search X for top posts from the last week about Taylor Swift.
```

```text
Find recent posts about #WWDC from @apple.
```

### `x_get_post`

Fetch a single post as an LLM-friendly JSON object.

Inputs:

- `url`: X/Twitter post URL
- `id`: X post ID

Provide exactly one of `url` or `id`.

Example prompts:

```text
Read and analyze this X post: https://x.com/user/status/1234567890
```

```text
Fetch post ID 1234567890 and summarize the author's claim.
```

### `x_get_bookmarks`

Fetch authenticated user's bookmarks with best-effort local filtering.

Requires cookie-auth mode.

Inputs:

- `query`: optional text filter
- `author`: optional `@handle` or profile URL
- `since`: optional post creation date lower bound
- `until`: optional post creation date upper bound
- `lang`: optional language code
- `limit`: optional, default `20`, max `50`
- `cursor`: optional cursor returned by a previous call

Example prompts:

```text
Search my X bookmarks for posts about AI from the last month.
```

```text
Find my bookmarked posts from @sama about OpenAI.
```

## Behavior Notes

- All timestamps returned by schemas are ISO 8601 UTC.
- Bookmark `since` and `until` filter by the post creation time, not the time the bookmark was added.
- Filtered bookmark search scans at most five pages per request and may return partial results.
- Search ranking is delegated to X/twikit. The server does not re-rank "top" results.
- Cursor state is in memory and is lost when the MCP server restarts.
- Guest mode may fail when X changes public access behavior. Cookie-auth mode is usually more capable but depends on valid browser cookies.

## Development

Set up local development:

```bash
git clone https://github.com/RayChang/twikit-mcp.git
cd twikit-mcp
python -m venv .venv
.venv/bin/pip install -e .
```

Run tests:

```bash
.venv/bin/python -m pytest -v
```

Current test coverage uses fake twikit clients and does not make live X requests.
