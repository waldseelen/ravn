"""Download metadata normalization and enrichment helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse


_BRACKETED_SEGMENT_RE = re.compile(r"\s*([\[(])([^\])]+)([\])])\s*")
_MULTI_SPACE_RE = re.compile(r"\s+")
_SEPARATOR_RE = re.compile(r"\s*[-–—|]+\s*")
_NOISE_TERMS = {
    "official",
    "official video",
    "official music video",
    "official audio",
    "music video",
    "lyric video",
    "lyrics",
    "audio",
    "video",
    "visualizer",
    "hd",
    "4k",
    "hq",
    "remastered",
    "remaster",
    "mv",
    "pv",
}


def _clean_whitespace(value: Any) -> str:
    text = str(value or "").replace("_", " ").strip()
    return _MULTI_SPACE_RE.sub(" ", text)


def _slugify_tag(value: Any) -> str:
    text = _clean_whitespace(value).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def normalize_media_title(value: Any) -> str:
    """Normalize download titles for history/library usage."""
    text = _clean_whitespace(value)
    if not text:
        return ""

    def _replace_bracketed(match: re.Match[str]) -> str:
        content = _clean_whitespace(match.group(2)).lower()
        content = re.sub(r"[^a-z0-9 ]+", " ", content)
        content = _clean_whitespace(content)
        if content in _NOISE_TERMS:
            return " "
        return f" {match.group(0).strip()} "

    text = _BRACKETED_SEGMENT_RE.sub(_replace_bracketed, text)
    text = re.sub(r"\s+[\-–—|:]\s*$", "", text)
    text = _MULTI_SPACE_RE.sub(" ", text).strip(" -–—|:")
    return text


def normalize_uploader_name(value: Any) -> str:
    """Normalize uploader/channel names for metadata and tags."""
    text = _clean_whitespace(value).lstrip("@")
    if not text:
        return ""
    if text.lower().endswith(" - topic"):
        text = text[:-8].rstrip()
    text = _MULTI_SPACE_RE.sub(" ", text)
    return text.strip(" -–—|:")


def normalize_collection_name(value: Any) -> str:
    """Normalize playlist/album style labels."""
    return _clean_whitespace(value).strip(" -–—|:")


def detect_source_platform(url: str, video_info: Optional[Dict[str, Any]] = None) -> str:
    """Resolve a compact platform identifier from URL or yt-dlp info."""
    info = video_info if isinstance(video_info, dict) else {}
    for key in ("extractor_key", "extractor"):
        raw = _slugify_tag(info.get(key))
        if raw:
            return raw

    hostname = urlparse(str(url or "")).hostname or ""
    hostname = hostname.lower().replace("www.", "")
    if hostname.startswith("m."):
        hostname = hostname[2:]
    if not hostname:
        return "download"
    parts = [part for part in hostname.split(".") if part]
    return parts[-2] if len(parts) >= 2 else parts[0]


def build_library_tags(
    *,
    url: str,
    video_info: Optional[Dict[str, Any]] = None,
    format_name: str = "",
    quality_name: str = "",
    normalized_uploader: str = "",
    normalized_collection: str = "",
) -> List[str]:
    """Build normalized tags for MediaLibrary registration."""
    info = video_info if isinstance(video_info, dict) else {}
    tags: List[str] = ["downloaded", "acquired"]

    for candidate in (
        detect_source_platform(url, info),
        format_name,
        quality_name,
        f"creator-{_slugify_tag(normalized_uploader)}" if normalized_uploader else "",
        f"collection-{_slugify_tag(normalized_collection)}" if normalized_collection else "",
    ):
        normalized = _slugify_tag(candidate)
        if normalized and normalized not in tags:
            tags.append(normalized)

    return tags


def build_enriched_download_metadata(
    *,
    url: str,
    video_info: Optional[Dict[str, Any]],
    output_files: Iterable[str],
    supporting_files: Iterable[str],
    format_name: str,
    quality_name: str,
    postprocess_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build structured metadata suitable for history and MediaLibrary persistence."""
    info = video_info if isinstance(video_info, dict) else {}
    resolved_title = normalize_media_title(info.get("track") or info.get("title") or Path(next(iter(output_files), "download")).stem)
    resolved_uploader = normalize_uploader_name(
        info.get("artist")
        or info.get("album_artist")
        or info.get("uploader")
        or info.get("channel")
        or info.get("creator")
    )
    resolved_collection = normalize_collection_name(
        info.get("playlist_title") or info.get("playlist") or info.get("album")
    )
    platform = detect_source_platform(url, info)
    library_tags = build_library_tags(
        url=url,
        video_info=info,
        format_name=format_name,
        quality_name=quality_name,
        normalized_uploader=resolved_uploader,
        normalized_collection=resolved_collection,
    )

    metadata: Dict[str, Any] = {
        "source_url": str(url or ""),
        "platform": platform,
        "normalized": {
            "title": resolved_title,
            "uploader": resolved_uploader,
            "collection": resolved_collection,
        },
        "raw": {
            "title": info.get("title") or "",
            "uploader": info.get("uploader") or info.get("channel") or "",
            "collection": info.get("playlist_title") or info.get("playlist") or info.get("album") or "",
        },
        "acquisition": {
            "webpage_url": info.get("webpage_url") or str(url or ""),
            "extractor": info.get("extractor") or "",
            "extractor_key": info.get("extractor_key") or "",
            "upload_date": info.get("upload_date") or "",
            "duration": float(info.get("duration") or 0.0),
            "view_count": int(info.get("view_count") or 0),
            "like_count": int(info.get("like_count") or 0),
            "format": str(format_name or "").lower(),
            "quality": str(quality_name or ""),
        },
        "output_files": [str(path) for path in output_files if str(path).strip()],
        "supporting_files": [str(path) for path in supporting_files if str(path).strip()],
        "library_tags": library_tags,
    }
    if postprocess_metadata:
        metadata["postprocess"] = dict(postprocess_metadata)
    return metadata
