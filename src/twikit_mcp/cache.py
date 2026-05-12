"""Small in-memory TTL cache."""

from __future__ import annotations

from collections.abc import Callable, Hashable
from dataclasses import dataclass
from datetime import timedelta
import time
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """Process-local TTL cache for short-lived repeated requests."""

    def __init__(
        self,
        *,
        default_ttl_seconds: float,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds must be positive")
        self._default_ttl_seconds = default_ttl_seconds
        self._clock = clock or time.monotonic
        self._items: dict[Hashable, _CacheEntry[T]] = {}

    def set(self, key: Hashable, value: T, *, ttl: timedelta | float | None = None) -> None:
        ttl_seconds = self._ttl_to_seconds(ttl)
        self._items[key] = _CacheEntry(
            value=value,
            expires_at=self._clock() + ttl_seconds,
        )

    def get(self, key: Hashable) -> T | None:
        entry = self._items.get(key)
        if entry is None:
            return None

        if entry.expires_at <= self._clock():
            self._items.pop(key, None)
            return None

        return entry.value

    def clear(self) -> None:
        self._items.clear()

    def _ttl_to_seconds(self, ttl: timedelta | float | None) -> float:
        if ttl is None:
            return self._default_ttl_seconds
        if isinstance(ttl, timedelta):
            seconds = ttl.total_seconds()
        else:
            seconds = float(ttl)
        if seconds <= 0:
            raise ValueError("ttl must be positive")
        return seconds
