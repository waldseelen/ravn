"""Reusable intent-driven download profile definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class DownloadProfile:
    """Preset that bundles format, naming, output, and automation choices."""

    key: str
    preferred_surface: str = "video"
    format_key: str = ""
    quality_label: str = ""
    audio_bitrate: str = ""
    naming_preset: str = "standard"
    filename_template: str = ""
    output_subdir: str = ""
    embed_metadata: Optional[bool] = None
    auto_sort_enabled: Optional[bool] = None
    auto_sort_mode: str = "artist"
    auto_subtitle_download: Optional[bool] = None
    preferred_subtitle_language: str = "tr"
    subtitle_fallback_language: str = "en"
    subtitle_include_auto_generated: Optional[bool] = None
    auto_embed_subtitles: Optional[bool] = None
    postprocess_profile: Dict[str, Any] = field(default_factory=dict)


DOWNLOAD_PROFILES: dict[str, DownloadProfile] = {
    "custom": DownloadProfile(key="custom"),
    "music": DownloadProfile(
        key="music",
        preferred_surface="audio",
        format_key="MP3",
        quality_label="Sadece Ses",
        audio_bitrate="320K",
        naming_preset="clean",
        output_subdir="Music",
        embed_metadata=True,
        auto_sort_enabled=True,
        auto_sort_mode="artist",
        auto_subtitle_download=False,
        auto_embed_subtitles=False,
        postprocess_profile={},
    ),
    "podcast": DownloadProfile(
        key="podcast",
        preferred_surface="audio",
        format_key="MP3",
        quality_label="Sadece Ses",
        audio_bitrate="128K",
        naming_preset="standard",
        output_subdir="Podcasts",
        embed_metadata=True,
        auto_sort_enabled=False,
        auto_subtitle_download=False,
        auto_embed_subtitles=False,
        postprocess_profile={},
    ),
    "archive": DownloadProfile(
        key="archive",
        preferred_surface="video",
        format_key="MKV",
        quality_label="En İyi",
        naming_preset="playlist",
        output_subdir="Archive",
        auto_subtitle_download=True,
        subtitle_include_auto_generated=True,
        auto_embed_subtitles=False,
        postprocess_profile={"embed_subtitles": True},
    ),
    "social_clip": DownloadProfile(
        key="social_clip",
        preferred_surface="video",
        format_key="MP4",
        quality_label="720p",
        naming_preset="clean",
        output_subdir="Clips",
        auto_subtitle_download=False,
        auto_embed_subtitles=False,
        postprocess_profile={},
    ),
}


def get_download_profile(profile_key: Optional[str]) -> DownloadProfile:
    """Resolve a download profile or fall back to the custom profile."""
    normalized = str(profile_key or "custom").strip().lower().replace("-", "_").replace(" ", "_")
    return DOWNLOAD_PROFILES.get(normalized, DOWNLOAD_PROFILES["custom"])


def apply_profile_overrides(base_settings: Dict[str, Any], profile: DownloadProfile) -> Dict[str, Any]:
    """Merge a preset on top of existing settings-derived download behavior."""
    merged = dict(base_settings)
    if profile.key == "custom":
        return merged

    merged["naming_preset"] = profile.naming_preset or merged.get("naming_preset", "standard")
    if profile.filename_template:
        merged["filename_template"] = profile.filename_template
    if profile.embed_metadata is not None:
        merged["embed_metadata"] = profile.embed_metadata
    if profile.auto_sort_enabled is not None:
        merged["auto_sort_enabled"] = profile.auto_sort_enabled
        merged["auto_sort_mode"] = profile.auto_sort_mode or merged.get("auto_sort_mode", "artist")
    if profile.auto_subtitle_download is not None:
        merged["auto_subtitle_download"] = profile.auto_subtitle_download
        merged["preferred_subtitle_language"] = profile.preferred_subtitle_language or merged.get("preferred_subtitle_language", "tr")
        merged["subtitle_fallback_language"] = profile.subtitle_fallback_language or merged.get("subtitle_fallback_language", "en")
    if profile.subtitle_include_auto_generated is not None:
        merged["subtitle_include_auto_generated"] = profile.subtitle_include_auto_generated
    if profile.auto_embed_subtitles is not None:
        merged["auto_embed_subtitles"] = profile.auto_embed_subtitles
    if profile.audio_bitrate:
        merged["audio_bitrate"] = profile.audio_bitrate
    if profile.postprocess_profile:
        current_postprocess = dict(merged.get("postprocess_profile", {}) or {})
        current_postprocess.update(profile.postprocess_profile)
        merged["postprocess_profile"] = current_postprocess
    return merged


def resolve_profile_output_dir(base_output_dir: str, profile: DownloadProfile) -> str:
    """Apply a profile-specific output subdirectory when configured."""
    base_path = Path(base_output_dir)
    if not profile.output_subdir:
        return str(base_path)
    return str(base_path / profile.output_subdir)
