"""
Pure media-URL helpers extracted from the download tab.

These are stateless classifiers/formatters (no widget or ``self`` dependency), so they live
in core where they can be unit-tested in isolation and reused by any surface. ``download_tab``
keeps thin static-method delegators for backward compatibility with existing callers/tests.
"""

from __future__ import annotations

from typing import Any

_KNOWN_VIDEO_DOMAINS = (
    "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
    "twitch.tv", "soundcloud.com", "facebook.com", "twitter.com",
    "tiktok.com", "instagram.com", "bilibili.com", "nicovideo.jp",
)


def detect_url_protocol(url: str) -> str:
    """Return 'magnet', 'torrent_file', or 'standard'."""
    lowered = (url or "").strip().lower()
    if lowered.startswith("magnet:?"):
        return "magnet"
    if lowered.endswith(".torrent"):
        return "torrent_file"
    return "standard"


def is_supported_video_url(url: str) -> bool:
    """True for an http(s) URL on a known supported media domain."""
    if not url:
        return False
    lowered = url.lower()
    if not (lowered.startswith("http://") or lowered.startswith("https://")):
        return False
    return any(domain in lowered for domain in _KNOWN_VIDEO_DOMAINS)


def looks_like_playlist_url(url: str) -> bool:
    """True when the URL carries a playlist/set/collection marker."""
    lowered = (url or "").lower()
    return (
        "list=" in lowered
        or "/playlist" in lowered
        or "/sets/" in lowered
        or "/collection/" in lowered
    )


def format_duration(seconds: Any) -> str:
    """Format a seconds count as H:MM:SS / M:SS; empty string for non-positive/invalid."""
    if not isinstance(seconds, (int, float)) or seconds <= 0:
        return ""
    seconds = int(seconds)
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:d}:{sec:02d}"


def format_size_from_mb(size_mb: float) -> str:
    """Format a size given in MB as a human-readable MB/GB string."""
    if size_mb >= 1024:
        return f"{size_mb / 1024:.1f} GB"
    return f"{size_mb:.1f} MB"
