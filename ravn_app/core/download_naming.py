"""Filename template presets and safe post-download renaming helpers."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from ravn_app.utils.file_utils import sanitize_filename

logger = logging.getLogger(__name__)

_TEMPLATE_TOKEN_RE = re.compile(r"{([a-z_]+)}")
_ALLOWED_TEMPLATE_TOKENS = {
    "title",
    "uploader",
    "playlist",
    "upload_date",
    "resolution",
}
_DEFAULT_TEMPLATE = "{title}"


@dataclass(frozen=True)
class DownloadNamingPreset:
    """Named filename-template preset."""

    key: str
    template: str


NAMING_PRESETS: Dict[str, DownloadNamingPreset] = {
    "standard": DownloadNamingPreset("standard", "{title}"),
    "clean": DownloadNamingPreset("clean", "{uploader} - {title}"),
    "playlist": DownloadNamingPreset("playlist", "{playlist}/{upload_date} - {title}"),
}

_PRESET_ALIASES = {
    "playlist_structured": "playlist",
    "playlist-structured": "playlist",
    "playliststructured": "playlist",
}


def normalize_naming_preset(value: Optional[str]) -> str:
    """Normalize naming preset IDs and lightweight aliases."""
    raw_value = str(value or "standard").strip().lower().replace(" ", "_")
    normalized = _PRESET_ALIASES.get(raw_value, raw_value)
    if normalized in NAMING_PRESETS:
        return normalized
    return "standard"


def get_naming_template(
    naming_preset: Optional[str] = None,
    custom_template: Optional[str] = None,
) -> str:
    """Resolve the effective template from a preset + optional override."""
    template = str(custom_template or "").strip()
    if template:
        return template
    preset_id = normalize_naming_preset(naming_preset)
    return NAMING_PRESETS[preset_id].template


def uses_custom_naming(
    naming_preset: Optional[str] = None,
    custom_template: Optional[str] = None,
) -> bool:
    """Return True when naming differs from the current title-only baseline."""
    return get_naming_template(naming_preset, custom_template) != _DEFAULT_TEMPLATE


def template_needs_video_info(
    naming_preset: Optional[str] = None,
    custom_template: Optional[str] = None,
) -> bool:
    """Return True when uploader/playlist/date tokens require richer metadata."""
    tokens = extract_template_tokens(get_naming_template(naming_preset, custom_template))
    return bool(tokens & {"uploader", "playlist", "upload_date"})


def extract_template_tokens(template: str) -> set[str]:
    """Return supported token names used inside a user template."""
    return {
        match.group(1)
        for match in _TEMPLATE_TOKEN_RE.finditer(str(template or ""))
        if match.group(1) in _ALLOWED_TEMPLATE_TOKENS
    }


def _sanitize_token_value(value: Any) -> str:
    """Make token values safe for filename/path-segment usage."""
    text = str(value or "").strip()
    text = sanitize_filename(text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .-_")


def _format_upload_date(value: Any) -> str:
    """Format yt-dlp upload dates (YYYYMMDD) into a readable filename token."""
    text = str(value or "").strip()
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return _sanitize_token_value(text)


def build_naming_context(
    video_info: Optional[Dict[str, Any]],
    *,
    fallback_title: str = "",
    resolution: str = "",
) -> Dict[str, str]:
    """Build a sanitized naming-token context from yt-dlp metadata."""
    info = video_info if isinstance(video_info, dict) else {}

    title = (
        info.get("track")
        or info.get("title")
        or fallback_title
        or "download"
    )
    uploader = (
        info.get("artist")
        or info.get("album_artist")
        or info.get("uploader")
        or info.get("channel")
        or info.get("creator")
        or ""
    )
    playlist = (
        info.get("playlist_title")
        or info.get("playlist")
        or info.get("album")
        or ""
    )

    if not resolution:
        explicit_resolution = info.get("resolution")
        if explicit_resolution:
            resolution = str(explicit_resolution)
        else:
            width = info.get("width")
            height = info.get("height")
            if width and height:
                resolution = f"{width}x{height}"

    context = {
        "title": _sanitize_token_value(title) or "download",
        "uploader": _sanitize_token_value(uploader),
        "playlist": _sanitize_token_value(playlist),
        "upload_date": _format_upload_date(info.get("upload_date")),
        "resolution": _sanitize_token_value(resolution),
    }
    return context


def render_template_path(
    template: str,
    *,
    context: Dict[str, str],
    fallback_title: str,
) -> Path:
    """Render a template into a safe relative path without file extension."""
    raw_template = str(template or "").strip() or _DEFAULT_TEMPLATE
    expanded = _TEMPLATE_TOKEN_RE.sub(
        lambda match: context.get(match.group(1), ""),
        raw_template,
    )
    expanded = expanded.replace("\\", "/")

    segments = []
    for raw_segment in expanded.split("/"):
        cleaned_segment = _sanitize_token_value(raw_segment)
        if cleaned_segment in {"", ".", ".."}:
            continue
        segments.append(cleaned_segment)

    if not segments:
        segments = [_sanitize_token_value(fallback_title) or "download"]

    return Path(*segments)


def _compound_suffix(path: Path) -> str:
    """Preserve sidecar-style compound suffixes such as .en.vtt."""
    suffixes = path.suffixes
    if suffixes:
        return "".join(suffixes)
    return path.suffix


def _ensure_unique_target(target_path: Path, reserved_paths: set[str]) -> Path:
    """Avoid clobbering existing files when the rendered name already exists."""
    key = str(target_path).lower()
    if key not in reserved_paths and not target_path.exists():
        reserved_paths.add(key)
        return target_path

    suffix = _compound_suffix(target_path)
    stem = target_path.name[:-len(suffix)] if suffix else target_path.name
    parent = target_path.parent

    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        candidate_key = str(candidate).lower()
        if candidate_key not in reserved_paths and not candidate.exists():
            reserved_paths.add(candidate_key)
            return candidate
        counter += 1


def apply_naming_template(
    downloaded_files: Iterable[str],
    *,
    output_dir: str,
    naming_preset: Optional[str] = None,
    custom_template: Optional[str] = None,
    video_info: Optional[Dict[str, Any]] = None,
    resolution: str = "",
) -> list[str]:
    """Rename downloaded files from the baseline title.ext pattern into a preset/template."""
    files = [str(path) for path in downloaded_files if path]
    if not files:
        return []

    if not uses_custom_naming(naming_preset, custom_template):
        return files

    fallback_title = next((Path(path).stem for path in files if Path(path).stem), "download")
    template_path = render_template_path(
        get_naming_template(naming_preset, custom_template),
        context=build_naming_context(
            video_info,
            fallback_title=fallback_title,
            resolution=resolution,
        ),
        fallback_title=fallback_title,
    )

    renamed_files: list[str] = []
    reserved_paths: set[str] = set()
    base_output_dir = Path(output_dir)

    for file_path in files:
        source_path = Path(file_path)
        if not source_path.exists():
            renamed_files.append(str(source_path))
            continue

        target_name = f"{template_path.name}{_compound_suffix(source_path)}"
        desired_target = base_output_dir / template_path.parent / target_name

        try:
            if source_path.resolve() == desired_target.resolve():
                reserved_paths.add(str(desired_target).lower())
                renamed_files.append(str(source_path))
                continue
        except OSError:
            pass

        desired_target.parent.mkdir(parents=True, exist_ok=True)
        final_target = _ensure_unique_target(desired_target, reserved_paths)

        try:
            source_path.rename(final_target)
            logger.info("Renamed downloaded file %s -> %s", source_path, final_target)
            renamed_files.append(str(final_target))
        except OSError as exc:
            logger.warning("Could not rename %s to %s: %s", source_path, final_target, exc)
            renamed_files.append(str(source_path))

    return renamed_files
