"""Automatic MediaLibrary registration helpers for generated output files."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from ravn_app.core.persistence._library_registration_batch import (
    LibraryRegistrationBatch,
    LibraryRegistrationResult,
)
from ravn_app.core.persistence.media_library import MediaLibrary
from ravn_app.utils.metadata_handler import MetadataHandler


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
        normalized_paths = self._normalize_registration_paths(file_paths)
        if not normalized_paths:
            return []

        normalized_source = self._normalize_source_type(source_type)
        if not self.is_enabled(normalized_source):
            return [
                LibraryRegistrationResult(
                    file_path=str(Path(path).expanduser().resolve()),
                    source_type=normalized_source,
                    skipped_reason="disabled",
                )
                for path in normalized_paths
            ]

        resolved_title = title if len(normalized_paths) == 1 else None
        metadata_payload = self._build_registration_metadata_payload(normalized_source, metadata)
        tag_payload = self._build_registration_tag_payload(normalized_source, tags)
        library = self._open_library_session()
        batch = LibraryRegistrationBatch(
            library,
            source_type=normalized_source,
            title=resolved_title,
            tags=tag_payload,
            metadata=metadata_payload,
        )

        try:
            return [batch.register_path(path) for path in normalized_paths]
        finally:
            library.close()

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
        results = self.register_outputs(
            file_path,
            source_type=source_type,
            title=title,
            tags=tags,
            metadata=metadata,
        )
        if results:
            return results[0]
        normalized_source = self._normalize_source_type(source_type)
        return LibraryRegistrationResult(
            file_path=str(Path(file_path).expanduser().resolve()),
            source_type=normalized_source,
            skipped_reason="missing",
        )


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

    def _open_library_session(self) -> MediaLibrary:
        return MediaLibrary(
            db_path=self.db_path,
            metadata_handler=self._metadata_handler_factory(),
        )

    @classmethod
    def _normalize_source_type(cls, source_type: str) -> str:
        normalized = str(source_type or "generic").strip().lower()
        return cls._SOURCE_ALIASES.get(normalized, normalized)

    @staticmethod
    def _normalize_registration_paths(file_paths: str | Path | Iterable[str | Path] | None) -> list[str]:
        if file_paths is None:
            return []
        if isinstance(file_paths, (str, Path)):
            return [str(file_paths)]
        return [str(path) for path in file_paths if str(path).strip()]

    def _build_registration_metadata_payload(
        self,
        source_type: str,
        metadata: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = dict(metadata or {})
        payload.setdefault("source_type", source_type)
        payload["auto_added_to_library"] = True
        payload.setdefault("auto_added_at", datetime.now(timezone.utc).isoformat())
        return payload

    def _build_registration_tag_payload(self, source_type: str, tags: Optional[list[str]]) -> list[str]:
        normalized_tags: list[str] = []
        for candidate in self._TAG_MAP.get(source_type, []) + list(tags or []):
            normalized = str(candidate).strip().lower()
            if normalized and normalized not in normalized_tags:
                normalized_tags.append(normalized)
        return normalized_tags
