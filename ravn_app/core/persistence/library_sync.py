"""Automatic MediaLibrary registration helpers for generated output files."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from ravn_app.core.persistence.media_library import MediaLibrary
from ravn_app.utils.metadata_handler import MetadataHandler


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


class MediaLibraryAutoAdder:
    """Register generated output files in the Phase 7 media library."""

    _SOURCE_ALIASES = {
        "convert": "conversion",
        "converted": "conversion",
        "downloads": "download",
        "mix": "mixer",
        "filter": "filters",
    }

    _FLAG_MAP = {
        "download": "auto_add_downloads",
        "conversion": "auto_add_converted_files",
        "mixer": "auto_add_mixer_output",
        "filters": "auto_add_filter_output",
    }

    _TAG_MAP = {
        "download": ["downloaded"],
        "conversion": ["converted"],
        "mixer": ["mixed"],
        "filters": ["filtered"],
    }

    def __init__(
        self,
        config_manager: Any | None = None,
        *,
        db_path: Optional[str] = None,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        metadata_handler_factory: Optional[Callable[[], MetadataHandler]] = None,
    ) -> None:
        self.config_manager = config_manager
        self.db_path = db_path
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self._metadata_handler_factory = metadata_handler_factory or (
            lambda: MetadataHandler(ffmpeg_path=self.ffmpeg_path, ffprobe_path=self.ffprobe_path)
        )

    def register_outputs(
        self,
        file_paths: str | Path | Iterable[str | Path],
        *,
        source_type: str,
        title: Optional[str] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[LibraryRegistrationResult]:
        """Register one or more output files in the media library."""
        normalized_paths = self._normalize_paths(file_paths)
        if not normalized_paths:
            return []

        resolved_title = title if len(normalized_paths) == 1 else None
        return [
            self.register_output(
                file_path=path,
                source_type=source_type,
                title=resolved_title,
                tags=tags,
                metadata=metadata,
            )
            for path in normalized_paths
        ]

    def register_output(
        self,
        file_path: str | Path,
        *,
        source_type: str,
        title: Optional[str] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> LibraryRegistrationResult:
        """Register a single output file in the media library."""
        normalized_source = self._normalize_source_type(source_type)
        path = Path(file_path).expanduser().resolve()
        result = LibraryRegistrationResult(file_path=str(path), source_type=normalized_source)

        if not self.is_enabled(normalized_source):
            result.skipped_reason = "disabled"
            return result

        if not path.exists() or not path.is_file():
            result.skipped_reason = "missing"
            return result

        metadata_payload = self._build_metadata_payload(normalized_source, metadata)
        tag_payload = self._build_tag_payload(normalized_source, tags)
        library = MediaLibrary(db_path=self.db_path, metadata_handler=self._metadata_handler_factory())

        try:
            existing = library.get_media_by_path(str(path))
            if existing:
                result.media_id = existing.id
                merged_metadata = dict(existing.metadata or {})
                merged_metadata.update(metadata_payload)
                merged_tags = sorted(set((existing.tags or []) + tag_payload))
                library.update_media(
                    int(existing.id),
                    title=title if title and title != existing.title else None,
                    metadata=merged_metadata,
                    tags=merged_tags,
                )
                result.skipped_reason = "exists"
                return result

            result.media_id = library.add_media(
                file_path=str(path),
                title=title,
                tags=tag_payload,
            )
            created_item = library.get_media(int(result.media_id or 0))
            merged_metadata = dict(created_item.metadata) if created_item else {}
            merged_metadata.update(metadata_payload)
            library.update_media(
                int(result.media_id),
                metadata=merged_metadata,
                tags=sorted(set((created_item.tags if created_item else []) + tag_payload)),
            )
            result.added = True
            return result
        except sqlite3.IntegrityError:
            logger.debug("Media already registered in library: %s", path)
            existing = library.get_media_by_path(str(path))
            result.media_id = existing.id if existing else None
            result.skipped_reason = "exists"
            return result
        except Exception as exc:
            logger.warning("Auto-add to media library failed for %s: %s", path, exc)
            result.error_message = str(exc)
            result.skipped_reason = "error"
            return result
        finally:
            library.close()

    def is_enabled(self, source_type: str) -> bool:
        """Return whether auto-registration is enabled for the given source."""
        normalized_source = self._normalize_source_type(source_type)
        section = self._get_library_section()
        flag_name = self._FLAG_MAP.get(normalized_source)
        if not flag_name:
            return True
        return bool(section.get(flag_name, True))

    def _get_library_section(self) -> dict[str, Any]:
        config_manager = self.config_manager
        if config_manager is None:
            return {}
        if hasattr(config_manager, "get_section"):
            try:
                value = config_manager.get_section("library")
                return dict(value) if isinstance(value, dict) else {}
            except Exception:
                return {}
        if isinstance(config_manager, dict):
            value = config_manager.get("library", {})
            return dict(value) if isinstance(value, dict) else {}
        return {}

    @classmethod
    def _normalize_source_type(cls, source_type: str) -> str:
        normalized = str(source_type or "generic").strip().lower()
        return cls._SOURCE_ALIASES.get(normalized, normalized)

    @staticmethod
    def _normalize_paths(file_paths: str | Path | Iterable[str | Path] | None) -> list[str]:
        if file_paths is None:
            return []
        if isinstance(file_paths, (str, Path)):
            return [str(file_paths)]
        return [str(path) for path in file_paths if str(path).strip()]

    def _build_metadata_payload(
        self,
        source_type: str,
        metadata: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = dict(metadata or {})
        payload.setdefault("source_type", source_type)
        payload["auto_added_to_library"] = True
        payload.setdefault("auto_added_at", datetime.now(timezone.utc).isoformat())
        return payload

    def _build_tag_payload(self, source_type: str, tags: Optional[list[str]]) -> list[str]:
        normalized_tags: list[str] = []
        for candidate in self._TAG_MAP.get(source_type, []) + list(tags or []):
            normalized = str(candidate).strip().lower()
            if normalized and normalized not in normalized_tags:
                normalized_tags.append(normalized)
        return normalized_tags
