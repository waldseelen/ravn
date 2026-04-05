"""Internal row-loading helpers for the media library."""

from __future__ import annotations

import sqlite3
from typing import Any, Callable, Iterable


class MediaLibraryRowMapper:
    """Load media rows and bulk-associated tag state from SQLite."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        record_builder: Callable[[sqlite3.Row, dict[int, list[str]]], Any],
    ) -> None:
        self._conn = conn
        self._record_builder = record_builder

    def load_rows(self, query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        cursor = self._conn.cursor()
        cursor.execute(query, tuple(params))
        return cursor.fetchall()

    def load_tags_by_media_id(self, media_ids: Iterable[int]) -> dict[int, list[str]]:
        normalized_ids = [int(media_id) for media_id in media_ids if media_id is not None]
        if not normalized_ids:
            return {}

        placeholders = ",".join("?" for _ in normalized_ids)
        cursor = self._conn.cursor()
        cursor.execute(
            f"SELECT media_id, tag FROM tags WHERE media_id IN ({placeholders}) ORDER BY media_id ASC, tag ASC",
            normalized_ids,
        )
        tags_by_media_id: dict[int, list[str]] = {media_id: [] for media_id in normalized_ids}
        for row in cursor.fetchall():
            tags_by_media_id.setdefault(int(row["media_id"]), []).append(row["tag"])
        return tags_by_media_id

    def map_rows_to_records(self, rows: Iterable[sqlite3.Row]) -> list[Any]:
        row_list = list(rows)
        if not row_list:
            return []

        tags_by_media_id = self.load_tags_by_media_id(
            row["id"] for row in row_list if row["id"] is not None
        )
        return [self._record_builder(row, tags_by_media_id) for row in row_list]
