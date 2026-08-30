"""
SQLite-backed media library persistence for Phase 7 media-management features.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from ravn_app.core.config_paths import ensure_directories_exist, get_media_library_file_path
from ravn_app.core.persistence._media_library_export import MediaLibraryExporter
from ravn_app.core.persistence._media_library_rows import MediaLibraryRowMapper
from ravn_app.core.persistence._media_library_stats import MediaLibraryStatsCache
from ravn_app.utils.metadata_handler import MetadataHandler

logger = logging.getLogger(__name__)

DEFAULT_SEARCH_HISTORY_LIMIT = 100
DEFAULT_EXPORT_BATCH_SIZE = 500


@dataclass
class MediaItemRecord:
    """Stored media item model."""

    id: Optional[int] = None
    file_path: str = ""
    title: str = ""
    format: str = ""
    duration: float = 0.0
    size: int = 0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    sample_rate: int = 0
    codec: str = ""
    bitrate: int = 0
    created_at: str = ""
    added_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    thumbnail: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class CollectionRecord:
    """Stored media collection model."""

    id: Optional[int] = None
    name: str = ""
    description: str = ""
    created_at: str = ""
    thumbnail: str = ""


@dataclass
class MediaSearchFilters:
    """Search filters for media library queries."""

    format: Optional[str] = None
    duration_min: Optional[float] = None
    duration_max: Optional[float] = None
    size_min: Optional[int] = None
    size_max: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    sort_by: str = "added_at"
    sort_desc: bool = True
    limit: int = 100


class MediaLibrary:
    """Manage a searchable SQLite media library."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        metadata_handler: Optional[MetadataHandler] = None,
        *,
        search_history_limit: int = DEFAULT_SEARCH_HISTORY_LIMIT,
        export_batch_size: int = DEFAULT_EXPORT_BATCH_SIZE,
    ) -> None:
        ensure_directories_exist()
        self.db_path = str(Path(db_path) if db_path else get_media_library_file_path())
        self.metadata_handler = metadata_handler or MetadataHandler()
        self.search_history_limit = max(int(search_history_limit or 0), 0)
        self.export_batch_size = max(int(export_batch_size or 1), 1)

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        self._row_mapper = MediaLibraryRowMapper(self.conn, self._build_media_record)
        self._stats_cache = MediaLibraryStatsCache(self.conn, self._count_duplicate_groups)
        self._exporter = MediaLibraryExporter(self.iter_media, self.list_collections, self.get_statistics)

    def _create_tables(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS media_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                title TEXT,
                format TEXT,
                duration REAL,
                size INTEGER,
                width INTEGER,
                height INTEGER,
                fps REAL,
                sample_rate INTEGER,
                codec TEXT,
                bitrate INTEGER,
                created_at TEXT,
                added_at TEXT,
                metadata TEXT,
                thumbnail TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                media_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                UNIQUE(media_id, tag),
                FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL,
                thumbnail TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS collection_items (
                collection_id INTEGER NOT NULL,
                media_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                UNIQUE(collection_id, media_id),
                FOREIGN KEY(collection_id) REFERENCES collections(id) ON DELETE CASCADE,
                FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT,
                filters_json TEXT,
                result_count INTEGER NOT NULL,
                searched_at TEXT NOT NULL
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_items_format ON media_items(format)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_items_added_at ON media_items(added_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_items_size ON media_items(size)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_items_duration ON media_items(duration)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_media_id_tag ON tags(media_id, tag)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_collection_items_collection_position ON collection_items(collection_id, position)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_search_history_searched_at ON search_history(searched_at DESC, id DESC)"
        )
        self.conn.commit()

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def add_media(
        self,
        file_path: str,
        title: Optional[str] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        thumbnail: Optional[str] = None,
    ) -> int:
        """Add a media file to the library."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Media file not found: {file_path}")

        extracted = metadata or self.metadata_handler.extract_metadata(str(path))
        stat = path.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat()
        added_at = self._utc_now_iso()
        normalized_title = title or extracted.get("title") or path.stem
        normalized_tags = self._normalize_tags(tags or [])

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO media_items (
                file_path, title, format, duration, size, width, height, fps,
                sample_rate, codec, bitrate, created_at, added_at, metadata, thumbnail
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(path.resolve()),
                normalized_title,
                (extracted.get("format") or path.suffix.lstrip(".")).lower(),
                float(extracted.get("duration") or 0.0),
                int(extracted.get("size") or stat.st_size),
                int(extracted.get("width") or 0),
                int(extracted.get("height") or 0),
                float(extracted.get("fps") or 0.0),
                int(extracted.get("sample_rate") or 0),
                str(extracted.get("codec") or extracted.get("video_codec") or extracted.get("audio_codec") or ""),
                int(extracted.get("bitrate") or 0),
                created_at,
                added_at,
                json.dumps(extracted, ensure_ascii=False),
                thumbnail or extracted.get("thumbnail") or "",
            ),
        )
        media_id = int(cursor.lastrowid or 0)
        self._replace_tags(media_id, normalized_tags)
        self.conn.commit()
        self._invalidate_stats_cache()
        return media_id

    def get_media(self, media_id: int) -> Optional[MediaItemRecord]:
        """Fetch a single media item by id."""
        rows = self._load_media_rows("SELECT * FROM media_items WHERE id = ?", (media_id,))
        items = self._map_media_rows_to_records(rows)
        return items[0] if items else None

    def get_media_by_path(self, file_path: str) -> Optional[MediaItemRecord]:
        """Fetch a single media item by file path."""
        rows = self._load_media_rows(
            "SELECT * FROM media_items WHERE file_path = ?",
            (str(Path(file_path).resolve()),),
        )
        items = self._map_media_rows_to_records(rows)
        return items[0] if items else None

    def list_media(self, limit: int = 100, offset: int = 0) -> list[MediaItemRecord]:
        """List media items ordered by most recently added."""
        rows = self._load_media_rows(
            "SELECT * FROM media_items ORDER BY added_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return self._map_media_rows_to_records(rows)

    def iter_media(self, *, batch_size: Optional[int] = None) -> Iterable[MediaItemRecord]:
        """Yield media items in batches to avoid large one-shot materialization."""
        page_size = max(int(batch_size or self.export_batch_size), 1)
        offset = 0
        while True:
            batch = self.list_media(limit=page_size, offset=offset)
            if not batch:
                return
            for item in batch:
                yield item
            if len(batch) < page_size:
                return
            offset += len(batch)

    def update_media(
        self,
        media_id: int,
        *,
        title: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        thumbnail: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> bool:
        """Update media metadata, title, thumbnail, and tags."""
        updates: list[str] = []
        params: list[Any] = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata, ensure_ascii=False))
        if thumbnail is not None:
            updates.append("thumbnail = ?")
            params.append(thumbnail)

        cursor = self.conn.cursor()
        if updates:
            params.append(media_id)
            # Safe: `updates` only ever holds fixed literal fragments ("title = ?", …) built
            # above — never user input. All user values flow through parameterized `?` binds.
            cursor.execute(f"UPDATE media_items SET {', '.join(updates)} WHERE id = ?", params)
        if tags is not None:
            self._replace_tags(media_id, self._normalize_tags(tags))
        self.conn.commit()

        changed = cursor.rowcount > 0 or tags is not None
        if changed:
            self._invalidate_stats_cache()
        return changed

    def delete_media(self, media_id: int) -> bool:
        """Delete a media item from the library."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM media_items WHERE id = ?", (media_id,))
        self.conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            self._invalidate_stats_cache()
        return deleted

    def search_media(
        self,
        query: str = "",
        filters: Optional[MediaSearchFilters] = None,
    ) -> list[MediaItemRecord]:
        """Search media items using text and structured filters."""
        filters = filters or MediaSearchFilters()
        conditions: list[str] = []
        params: list[Any] = []
        normalized_filter_tags = self._normalize_tags(filters.tags)

        if query:
            like_value = f"%{query}%"
            conditions.append("(m.title LIKE ? OR m.file_path LIKE ?)")
            params.extend([like_value, like_value])
        if filters.format:
            conditions.append("LOWER(m.format) = LOWER(?)")
            params.append(filters.format)
        if filters.duration_min is not None:
            conditions.append("m.duration >= ?")
            params.append(filters.duration_min)
        if filters.duration_max is not None:
            conditions.append("m.duration <= ?")
            params.append(filters.duration_max)
        if filters.size_min is not None:
            conditions.append("m.size >= ?")
            params.append(filters.size_min)
        if filters.size_max is not None:
            conditions.append("m.size <= ?")
            params.append(filters.size_max)
        if filters.date_from:
            conditions.append("m.added_at >= ?")
            params.append(filters.date_from)
        if filters.date_to:
            conditions.append("m.added_at <= ?")
            params.append(filters.date_to)
        if normalized_filter_tags:
            placeholders = ",".join("?" for _ in normalized_filter_tags)
            conditions.append(
                f"EXISTS (SELECT 1 FROM tags t WHERE t.media_id = m.id AND t.tag IN ({placeholders}))"
            )
            params.extend(normalized_filter_tags)

        sort_columns = {
            "added_at": "m.added_at",
            "date": "m.added_at",
            "duration": "m.duration",
            "name": "LOWER(m.title)",
            "size": "m.size",
            "title": "LOWER(m.title)",
        }
        order_column = sort_columns.get(filters.sort_by, "m.added_at")
        order_direction = "DESC" if filters.sort_desc else "ASC"
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(filters.limit)

        rows = self._load_media_rows(
            f"""
            SELECT m.*
            FROM media_items m
            {where_clause}
            ORDER BY {order_column} {order_direction}
            LIMIT ?
            """,
            params,
        )
        items = self._map_media_rows_to_records(rows)
        self._record_search(query=query, filters=filters, result_count=len(items))
        return items

    def add_tag(self, media_id: int, tag: str) -> bool:
        """Add a tag to a media item."""
        normalized_tag = self._normalize_tags([tag])
        if not normalized_tag:
            return False
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO tags (media_id, tag) VALUES (?, ?)",
            (media_id, normalized_tag[0]),
        )
        self.conn.commit()
        added = cursor.rowcount > 0
        if added:
            self._invalidate_stats_cache()
        return added

    def remove_tag(self, media_id: int, tag: str) -> bool:
        """Remove a tag from a media item."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tags WHERE media_id = ? AND tag = ?", (media_id, tag.strip().lower()))
        self.conn.commit()
        removed = cursor.rowcount > 0
        if removed:
            self._invalidate_stats_cache()
        return removed

    def create_collection(
        self,
        name: str,
        description: str = "",
        thumbnail: str = "",
    ) -> int:
        """Create a new media collection."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO collections (name, description, created_at, thumbnail) VALUES (?, ?, ?, ?)",
            (name, description, self._utc_now_iso(), thumbnail),
        )
        self.conn.commit()
        self._invalidate_stats_cache()
        return int(cursor.lastrowid or 0)

    def rename_collection(self, collection_id: int, new_name: str) -> bool:
        """Rename an existing collection."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE collections SET name = ? WHERE id = ?", (new_name, collection_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_collection(self, collection_id: int) -> bool:
        """Delete a collection and its ordering rows."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
        self.conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            self._invalidate_stats_cache()
        return deleted

    def list_collections(self) -> list[CollectionRecord]:
        """Return all collections ordered by name."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM collections ORDER BY LOWER(name) ASC")
        rows = cursor.fetchall()
        return [CollectionRecord(**dict(row)) for row in rows]

    def add_to_collection(self, media_id: int, collection_id: int, position: Optional[int] = None) -> bool:
        """Add a media item to a collection."""
        cursor = self.conn.cursor()
        if position is None:
            cursor.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM collection_items WHERE collection_id = ?",
                (collection_id,),
            )
            position = int(cursor.fetchone()[0])
        cursor.execute(
            "INSERT OR REPLACE INTO collection_items (collection_id, media_id, position) VALUES (?, ?, ?)",
            (collection_id, media_id, position),
        )
        self.conn.commit()
        changed = cursor.rowcount > 0
        if changed:
            self._invalidate_stats_cache()
        return changed

    def get_collection_items(self, collection_id: int) -> list[MediaItemRecord]:
        """Return media items for a collection in stored order."""
        rows = self._load_media_rows(
            """
            SELECT m.*
            FROM collection_items ci
            JOIN media_items m ON m.id = ci.media_id
            WHERE ci.collection_id = ?
            ORDER BY ci.position ASC
            """,
            (collection_id,),
        )
        return self._map_media_rows_to_records(rows)

    def detect_duplicates(self) -> list[list[MediaItemRecord]]:
        """Detect likely duplicate media groups by size, duration, and format."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT size, ROUND(COALESCE(duration, 0), 3) AS duration_key, format, COUNT(*) AS item_count
            FROM media_items
            GROUP BY size, duration_key, format
            HAVING COUNT(*) > 1
            ORDER BY item_count DESC, size DESC
            """
        )
        duplicate_groups: list[list[MediaItemRecord]] = []
        for row in cursor.fetchall():
            rows = self._load_media_rows(
                """
                SELECT * FROM media_items
                WHERE size = ? AND ROUND(COALESCE(duration, 0), 3) = ? AND format = ?
                ORDER BY added_at DESC
                """,
                (row["size"], row["duration_key"], row["format"]),
            )
            items = self._map_media_rows_to_records(rows)
            if len(items) > 1:
                duplicate_groups.append(items)
        return duplicate_groups

    def get_statistics(self, *, force_refresh: bool = False) -> dict[str, Any]:
        """Return aggregate library statistics."""
        return self._stats_cache.get(force_refresh=force_refresh)

    def export_library(self, export_format: str, output_file: str) -> bool:
        """Export library data as JSON or CSV."""
        return self._exporter.export(export_format, output_file)

    def get_recent_searches(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent search history rows."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM search_history ORDER BY searched_at DESC, id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        """Close the SQLite connection."""
        if self.conn:
            self.conn.close()

    def _replace_tags(self, media_id: int, tags: list[str]) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tags WHERE media_id = ?", (media_id,))
        for tag in tags:
            cursor.execute(
                "INSERT OR IGNORE INTO tags (media_id, tag) VALUES (?, ?)",
                (media_id, tag),
            )

    @staticmethod
    def _normalize_tags(tags: list[str]) -> list[str]:
        normalized: list[str] = []
        for tag in tags:
            candidate = str(tag).strip().lower()
            if candidate and candidate not in normalized:
                normalized.append(candidate)
        return normalized

    def _load_media_rows(self, query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        return self._row_mapper.load_rows(query, params)

    def _load_tags_for_media_ids(self, media_ids: Iterable[int]) -> dict[int, list[str]]:
        return self._row_mapper.load_tags_by_media_id(media_ids)

    def _map_media_rows_to_records(self, rows: Iterable[sqlite3.Row]) -> list[MediaItemRecord]:
        return self._row_mapper.map_rows_to_records(rows)

    @staticmethod
    def _deserialize_media_metadata(metadata_raw: str) -> dict[str, Any]:
        try:
            return json.loads(metadata_raw or "{}")
        except json.JSONDecodeError:
            return {}

    def _build_media_record(
        self,
        row: sqlite3.Row,
        tags_by_media_id: dict[int, list[str]],
    ) -> MediaItemRecord:
        media_id = int(row["id"])
        metadata = self._deserialize_media_metadata(row["metadata"])
        return MediaItemRecord(
            id=media_id,
            file_path=row["file_path"],
            title=row["title"] or "",
            format=row["format"] or "",
            duration=float(row["duration"] or 0.0),
            size=int(row["size"] or 0),
            width=int(row["width"] or 0),
            height=int(row["height"] or 0),
            fps=float(row["fps"] or 0.0),
            sample_rate=int(row["sample_rate"] or 0),
            codec=row["codec"] or "",
            bitrate=int(row["bitrate"] or 0),
            created_at=row["created_at"] or "",
            added_at=row["added_at"] or "",
            metadata=metadata,
            thumbnail=row["thumbnail"] or "",
            tags=list(tags_by_media_id.get(media_id, [])),
        )

    def _record_search(self, query: str, filters: MediaSearchFilters, result_count: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO search_history (query_text, filters_json, result_count, searched_at) VALUES (?, ?, ?, ?)",
            (
                query,
                json.dumps(asdict(filters), ensure_ascii=False),
                result_count,
                self._utc_now_iso(),
            ),
        )
        self._prune_search_history(cursor)
        self.conn.commit()

    def _prune_search_history(self, cursor: sqlite3.Cursor) -> None:
        if self.search_history_limit <= 0:
            cursor.execute("DELETE FROM search_history")
            return
        cursor.execute(
            """
            DELETE FROM search_history
            WHERE id NOT IN (
                SELECT id
                FROM search_history
                ORDER BY searched_at DESC, id DESC
                LIMIT ?
            )
            """,
            (self.search_history_limit,),
        )

    def _count_duplicate_groups(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT 1
                FROM media_items
                GROUP BY size, ROUND(COALESCE(duration, 0), 3), format
                HAVING COUNT(*) > 1
            ) duplicate_groups
            """
        )
        row = cursor.fetchone()
        return int(row[0] or 0) if row else 0

    def _invalidate_stats_cache(self) -> None:
        self._stats_cache.invalidate()
