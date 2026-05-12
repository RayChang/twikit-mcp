# tweety-mcp

Local single-user MCP server for querying X posts and authenticated bookmarks through [`tweety-ns`](https://github.com/mahrtayyab/tweety).

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
uvx --from "git+https://github.com/RayChang/tweety-mcp.git" tweety-mcp
```

This does not install a persistent `tweety-mcp` command. `uvx` downloads/builds the package on first run, stores it in uv's cache, and runs the MCP stdio server.

`tweety-mcp` is an MCP stdio server, so running it directly will wait for MCP JSON-RPC messages on stdin. Use it through an MCP host rather than as an interactive CLI.

## Optional Persistent Install

If you prefer a persistent local command:

```bash
pipx install "git+https://github.com/RayChang/tweety-mcp.git"
```

Or with `uv`:

```bash
uv tool install "git+https://github.com/RayChang/tweety-mcp.git"
```

Or with `pip`:

```bash
python -m pip install "git+https://github.com/RayChang/tweety-mcp.git"
```

For local development from a checkout:

```bash
git clone https://github.com/RayChang/tweety-mcp.git
cd tweety-mcp
python -m pip install -e .
```

If you use a persistent install, verify that the command is available:

```bash
which tweety-mcp
```

## Authentication

All three tools currently require cookie-auth mode. `tweety-ns` decorates `search`, `get_bookmarks`, and similar endpoints as `@AuthRequired`, and X is increasingly hostile to unauthenticated access. Guest mode is accepted by the config layer but most endpoints will reject the request.

The server only reads `auth_token` and `ct0`. It does not ask for your X username, password, or 2FA code.

Create:

```text
~/.config/tweety-mcp/cookies.json
```

With:

```json
{
  "auth_token": "...",
  "ct0": "..."
}
```

`chmod 600` the file so other users on the machine cannot read it.

Environment variables override the file:

```bash
export TWEETY_MCP_AUTH_TOKEN="..."
export TWEETY_MCP_CT0="..."
```

The file approach is preferred because env vars registered with `claude mcp add -e ...` end up in `~/.claude.json` in plaintext.

If cookies expire, grab fresh `auth_token` and `ct0` from your browser DevTools (`Application → Storage → Cookies → https://x.com`) and update the file. No server restart is needed — values are re-read on each tool invocation.

## Agent CLI Setup

The examples below use `uvx`, so users do not need to install `tweety-mcp` first. If you use a persistent install instead, set `command` to `tweety-mcp` and set `args` to `[]`.

### Codex CLI

Codex can run the server from `~/.codex/config.toml`:

```toml
[mcp_servers.tweety-mcp]
command = "uvx"
args = ["--from", "git+https://github.com/RayChang/tweety-mcp.git", "tweety-mcp"]
```

With cookie environment variables:

```toml
[mcp_servers.tweety-mcp]
command = "uvx"
args = ["--from", "git+https://github.com/RayChang/tweety-mcp.git", "tweety-mcp"]
env = { TWEETY_MCP_AUTH_TOKEN = "...", TWEETY_MCP_CT0 = "..." }
```

If your Codex CLI accepts full command strings, this command-line registration is also possible:

```bash
codex mcp add tweety-mcp --transport stdio --command "uvx --from git+https://github.com/RayChang/tweety-mcp.git tweety-mcp"
```

Check registration:

```bash
codex mcp list
```

Remove it:

```bash
codex mcp remove tweety-mcp
```

### Claude Code

Add a local stdio MCP server entry. For project-local configuration, create or edit `.mcp.json` in the project where Claude Code should use the server:

```json
{
  "tweety-mcp": {
    "command": "uvx",
    "args": ["--from", "git+https://github.com/RayChang/tweety-mcp.git", "tweety-mcp"]
  }
}
```

If you prefer environment variables instead of `~/.config/tweety-mcp/cookies.json`:

```json
{
  "tweety-mcp": {
    "command": "uvx",
    "args": ["--from", "git+https://github.com/RayChang/tweety-mcp.git", "tweety-mcp"],
    "env": {
      "TWEETY_MCP_AUTH_TOKEN": "${TWEETY_MCP_AUTH_TOKEN}",
      "TWEETY_MCP_CT0": "${TWEETY_MCP_CT0}"
    }
  }
}
```

Restart Claude Code after changing MCP config.

### Gemini CLI

Gemini CLI supports adding a local stdio MCP server from the command line:

```bash
gemini mcp add tweety-mcp uvx --from "git+https://github.com/RayChang/tweety-mcp.git" tweety-mcp
```

Or configure it in Gemini CLI `settings.json`:

```json
{
  "mcpServers": {
    "tweety-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/RayChang/tweety-mcp.git", "tweety-mcp"],
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
    "tweety-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/RayChang/tweety-mcp.git", "tweety-mcp"],
      "env": {
        "TWEETY_MCP_AUTH_TOKEN": "$TWEETY_MCP_AUTH_TOKEN",
        "TWEETY_MCP_CT0": "$TWEETY_MCP_CT0"
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
    "tweety-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/RayChang/tweety-mcp.git", "tweety-mcp"]
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
- Search ranking is delegated to X/tweety. The server does not re-rank "top" results.
- Cursor state is in memory and is lost when the MCP server restarts.
- Guest mode may fail when X changes public access behavior. Cookie-auth mode is usually more capable but depends on valid browser cookies.

## Upstream Patches

The package ships two runtime monkey-patches in `src/tweety_mcp/_tweety_patch.py` that port unreleased fixes from `tweety-ns` `main` onto the PyPI 2.4.1 release:

- **`ondemand.s.js` regex** — X changed its frontend bundle layout around 2026-03-18, breaking the regex tweety uses to derive the `ClientTransaction` animation key. Tweety PR #288 merged on 2026-03-22 but has not been released. Without this patch every request raises `Couldn't get animation key indices`.
- **`SearchTimeline` GraphQL endpoint** — X migrated `SearchTimeline` from `GET` to `POST` (with a new `queryId`) around the same time. Tweety issue #292 tracks the migration but no fix is on `main`. Without this patch `x_search_posts` returns `404 Page not Found`.

Both patches are removed automatically once a tweety release that contains the upstream fixes is published — delete `_tweety_patch.py` and drop the import from `src/tweety_mcp/__init__.py`.

## Development

Set up local development:

```bash
git clone https://github.com/RayChang/tweety-mcp.git
cd tweety-mcp
python -m venv .venv
.venv/bin/pip install -e .
```

Run tests:

```bash
.venv/bin/python -m pytest -v
```

Current test coverage uses fake clients and does not make live X requests.
