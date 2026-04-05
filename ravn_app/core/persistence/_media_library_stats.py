"""Internal statistics cache helpers for the media library."""

from __future__ import annotations

import sqlite3
from typing import Any, Callable


class MediaLibraryStatsCache:
    """Cache aggregate media-library statistics with explicit invalidation."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        duplicate_group_counter: Callable[[], int],
    ) -> None:
        self._conn = conn
        self._duplicate_group_counter = duplicate_group_counter
        self._stats: dict[str, Any] | None = None
        self._dirty = True

    def get(self, *, force_refresh: bool = False) -> dict[str, Any]:
        if not force_refresh and not self._dirty and self._stats is not None:
            return self._copy(self._stats)

        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(size), 0), COALESCE(SUM(duration), 0) FROM media_items")
        total_items, total_size, total_duration = cursor.fetchone()
        cursor.execute(
            "SELECT format, COUNT(*) AS count FROM media_items GROUP BY format ORDER BY count DESC, format ASC"
        )
        formats = {row["format"]: row["count"] for row in cursor.fetchall()}
        cursor.execute("SELECT COUNT(*) FROM collections")
        collection_count = cursor.fetchone()[0]

        stats = {
            "total_items": int(total_items or 0),
            "total_size": int(total_size or 0),
            "total_duration": float(total_duration or 0.0),
            "formats": formats,
            "collections": int(collection_count or 0),
            "duplicate_groups": self._duplicate_group_counter(),
        }
        self._stats = stats
        self._dirty = False
        return self._copy(stats)

    def invalidate(self) -> None:
        self._stats = None
        self._dirty = True

    @staticmethod
    def _copy(stats: dict[str, Any]) -> dict[str, Any]:
        copied = dict(stats)
        copied["formats"] = dict(stats.get("formats", {}))
        return copied
