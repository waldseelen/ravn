"""Internal batch-registration helpers for media-library auto-add flows."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ravn_app.core.persistence.media_library import MediaLibrary

logger = logging.getLogger(__name__)


@dataclass
class LibraryRegistrationResult:
    """Outcome of attempting to register a file in the media library."""

    file_path: str
    source_type: str
    media_id: Optional[int] = None
    added: bool = False
    skipped_reason: str = ""
    error_message: str = ""


class LibraryRegistrationBatch:
    """Register a batch of output files against one shared MediaLibrary session."""

    def __init__(
        self,
        library: MediaLibrary,
        *,
        source_type: str,
        title: Optional[str],
        tags: list[str],
        metadata: dict[str, Any],
    ) -> None:
        self.library = library
        self.source_type = source_type
        self.title = title
        self.tags = list(tags)
        self.metadata = dict(metadata)

    def register_path(self, file_path: str | Path) -> LibraryRegistrationResult:
        path = Path(file_path).expanduser().resolve()
        result = LibraryRegistrationResult(file_path=str(path), source_type=self.source_type)

        if not path.exists() or not path.is_file():
            result.skipped_reason = "missing"
            return result

        try:
            existing = self.library.get_media_by_path(str(path))
            if existing is not None:
                self._update_existing_media(existing, result)
                return result

            result.media_id = self.library.add_media(
                file_path=str(path),
                title=self.title,
                tags=self.tags,
                metadata=self._build_new_media_metadata(str(path)),
            )
            result.added = True
            return result
        except sqlite3.IntegrityError:
            logger.debug("Media already registered in library: %s", path)
            existing = self.library.get_media_by_path(str(path))
            result.media_id = existing.id if existing else None
            result.skipped_reason = "exists"
            return result
        except Exception as exc:
            logger.warning("Auto-add to media library failed for %s: %s", path, exc)
            result.error_message = str(exc)
            result.skipped_reason = "error"
            return result

    def _build_new_media_metadata(self, file_path: str) -> dict[str, Any]:
        extracted_metadata = dict(self.library.metadata_handler.extract_metadata(file_path) or {})
        extracted_metadata.update(self.metadata)
        return extracted_metadata

    def _update_existing_media(self, existing: Any, result: LibraryRegistrationResult) -> None:
        result.media_id = existing.id
        merged_metadata = dict(existing.metadata or {})
        merged_metadata.update(self.metadata)
        merged_tags = sorted(set((existing.tags or []) + self.tags))
        self.library.update_media(
            int(existing.id),
            title=self.title if self.title and self.title != existing.title else None,
            metadata=merged_metadata,
            tags=merged_tags,
        )
        result.skipped_reason = "exists"
