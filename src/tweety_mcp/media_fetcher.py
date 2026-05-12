"""Async fetcher that turns X CDN image URLs into FastMCP ``Image`` blocks.

Tweets and articles expose media as URLs. To let the model actually see
the pixels we download the bytes here and wrap them in ``Image`` so
FastMCP serializes them as MCP ``ImageContent``.
"""

from __future__ import annotations

import asyncio
from typing import Iterable
from urllib.parse import urlparse

import httpx
from mcp.server.fastmcp import Image


DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_IMAGE_BYTES = 10 * 1024 * 1024
_KNOWN_EXTENSIONS = {
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
    ".gif": "gif",
    ".webp": "webp",
}
_KNOWN_CONTENT_TYPES = {
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


async def fetch_images(urls: Iterable[str]) -> list[Image]:
    """Download multiple media URLs concurrently and skip silent failures."""
    tasks = [fetch_image(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return [image for image in results if image is not None]


async def fetch_image(url: str | None) -> Image | None:
    """Fetch a single image URL into a FastMCP ``Image``. Returns ``None`` on failure."""
    if not url or not isinstance(url, str):
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS, follow_redirects=True) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException):
            return None

    data = response.content
    if not data or len(data) > MAX_IMAGE_BYTES:
        return None

    fmt = _detect_format(parsed.path, response.headers.get("content-type"))
    if fmt is None:
        return None
    return Image(data=data, format=fmt)


def _detect_format(path: str, content_type: str | None) -> str | None:
    suffix = ""
    if "." in path:
        suffix = "." + path.rsplit(".", 1)[-1].lower().split("?")[0]
    if suffix in _KNOWN_EXTENSIONS:
        return _KNOWN_EXTENSIONS[suffix]
    if content_type:
        normalized = content_type.split(";", 1)[0].strip().lower()
        if normalized in _KNOWN_CONTENT_TYPES:
            return _KNOWN_CONTENT_TYPES[normalized]
    return None
