"""
RAVN - yt-dlp process runner.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from ravn_app.core.runners.base import BaseRunner, RunnerResult, get_hidden_subprocess_kwargs

logger = logging.getLogger(__name__)

# yt-dlp is a heavy import (~0.5s) and is only needed for the progressive library-based
# preview path -- not for downloads (which always use the self-updating binary). Import it
# lazily on first use so it never taxes app startup, and cache the resolved module (or the
# _UNAVAILABLE sentinel) so a broken/missing install is only probed once.
_UNAVAILABLE = object()
_yt_dlp_lib: Optional[object] = None


def _get_ytdlp_library():
    """Lazily import the yt-dlp Python library; returns the module or None if unavailable."""
    global _yt_dlp_lib
    if _yt_dlp_lib is None:
        try:
            import yt_dlp as module
            _yt_dlp_lib = module
        except Exception:  # pragma: no cover - defensive guard for broken/missing installs
            _yt_dlp_lib = _UNAVAILABLE
    return None if _yt_dlp_lib is _UNAVAILABLE else _yt_dlp_lib


def is_ytdlp_library_available() -> bool:
    """Whether the yt-dlp Python library (not the standalone binary) can be imported."""
    return _get_ytdlp_library() is not None


class YtDlpRunner(BaseRunner):
    """
    Unified yt-dlp subprocess runner.
    Handles all media downloads with consistent error handling,
    progress reporting, and retry logic.
    """

    DEFAULT_RETRIES = 3
    DEFAULT_TIMEOUT = 3600

    def __init__(self, ytdlp_path: str = "yt-dlp"):
        super().__init__(ytdlp_path)
        self._progress_pattern = re.compile(
            r"\[download\]\s+(\d+\.?\d*)%\s+of\s+~?(\d+\.?\d*\w+)"
        )

    def _build_command(
        self,
        url: str,
        output_template: str,
        format_spec: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
    ) -> List[str]:
        """Build yt-dlp command."""
        cmd = [
            self.executable_path,
            "--no-warnings",
            "-o",
            output_template,
            "--newline",
        ]

        if format_spec:
            cmd.extend(["-f", format_spec])

        if extra_args:
            cmd.extend(extra_args)

        cmd.append(url)
        return cmd

    def _parse_error(self, stderr: str) -> str:
        """Parse yt-dlp stderr to extract user-friendly error message."""
        error_patterns = [
            (r"Video unavailable", "Video is unavailable or has been removed"),
            (r"Private video", "This video is private"),
            (r"Sign in to confirm your age", "Age-restricted video requires login"),
            (r"members-only", "Members-only content requires login"),
            (r"This video is available to this channel", "Channel members only"),
            (r"Premiere will begin", "Video is a scheduled premiere"),
            (r"Unable to extract", "Could not extract video information"),
            (r"Unsupported URL", "URL is not supported"),
            (r"No video formats", "No downloadable formats available"),
            (r"HTTP Error 403", "Access denied (403)"),
            (r"HTTP Error 404", "Video not found (404)"),
            (r"HTTP Error 429", "Too many requests - try again later"),
            (r"is not a valid URL", "Invalid URL provided"),
            (r"Unable to download webpage", "Network error - cannot reach server"),
            (r"Geo-restricted", "Content is geo-restricted in your region"),
        ]

        for pattern, message in error_patterns:
            if re.search(pattern, stderr, re.IGNORECASE):
                return message

        lines = [line.strip() for line in stderr.split("\n") if line.strip()]
        for line in reversed(lines):
            if "error" in line.lower():
                return line[:200]

        return "Download failed"

    def download(
        self,
        url: str,
        output_dir: str,
        filename_template: str = "%(title)s.%(ext)s",
        format_spec: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        timeout: Optional[int] = None,
        retries: int = DEFAULT_RETRIES,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Download media from URL.

        Args:
            url: Media URL to download
            output_dir: Output directory path
            filename_template: yt-dlp output template
            format_spec: Format specification (e.g., 'bestvideo+bestaudio/best')
            extra_args: Additional yt-dlp arguments
            timeout: Download timeout in seconds
            retries: Number of retry attempts
            progress_callback: Callback for progress updates

        Returns:
            RunnerResult with download details
        """
        os.makedirs(output_dir, exist_ok=True)
        output_template = os.path.join(output_dir, filename_template)
        command = self._build_command(url, output_template, format_spec, extra_args)

        last_result: Optional[RunnerResult] = None
        for attempt in range(1, retries + 1):
            logger.info("yt-dlp: Download attempt %s/%s for %s", attempt, retries, url)

            result = self._run_process(
                command,
                timeout or self.DEFAULT_TIMEOUT,
                progress_callback,
            )

            if result.success:
                downloaded_files = self._extract_downloaded_files(result.stdout)
                result.metadata["downloaded_files"] = downloaded_files
                result.metadata["archive_skipped"] = self._was_archive_skipped(result.stdout)
                return result

            last_result = result

            if any(
                err in result.error_message.lower()
                for err in ["unavailable", "private", "not found", "invalid url"]
            ):
                break

            if attempt < retries:
                import time

                wait_time = attempt * 2
                logger.info("Retrying in %s seconds...", wait_time)
                time.sleep(wait_time)

        return last_result or RunnerResult(
            success=False,
            return_code=-1,
            error_message="All download attempts failed",
        )

    @staticmethod
    def _was_archive_skipped(stdout: str) -> bool:
        """Return True when yt-dlp reports an already-recorded archive entry."""
        text = str(stdout or "")
        return "already been recorded in the archive" in text.lower()

    def _extract_downloaded_files(self, stdout: str) -> List[str]:
        """Extract list of downloaded files from yt-dlp output."""
        patterns = [
            r"\[download\] Destination: (.+)",
            r"\[Merger\] Merging formats into \"(.+)\"",
            r"\[ExtractAudio\] Destination: (.+)",
        ]

        seen: set[str] = set()
        ordered_files: List[str] = []
        for pattern in patterns:
            matches = re.findall(pattern, stdout)
            for match in matches:
                normalized = str(match).strip()
                if not normalized:
                    continue
                key = normalized.lower()
                if key in seen:
                    continue
                seen.add(key)
                ordered_files.append(normalized)

        return ordered_files

    def extract_info(self, url: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
        """
        Extract video information without downloading.

        Args:
            url: Media URL
            timeout: Request timeout

        Returns:
            Dictionary with video metadata, or None on error
        """
        cmd = [
            self.executable_path,
            "--dump-json",
            "--no-warnings",
            "--no-download",
            url,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                **get_hidden_subprocess_kwargs(),
            )

            if result.returncode == 0:
                return json.loads(result.stdout)

            logger.error("yt-dlp info extraction failed: %s", result.stderr)
            return None

        except subprocess.TimeoutExpired:
            logger.error("yt-dlp info extraction timed out")
            return None
        except json.JSONDecodeError as exc:
            logger.error("yt-dlp output parse error: %s", exc)
            return None
        except Exception as exc:
            logger.error("yt-dlp error: %s", exc)
            return None

    @staticmethod
    def _resolve_playlist_entry_url(entry: Dict[str, Any], playlist_url: str) -> Optional[str]:
        """Resolve playlist entry URL to a downloadable HTTP URL."""
        direct_url = entry.get("webpage_url") or entry.get("url") or entry.get("original_url")
        if isinstance(direct_url, str) and direct_url.startswith(("http://", "https://")):
            return direct_url

        playlist_lower = playlist_url.lower()
        candidate_id = direct_url if isinstance(direct_url, str) and direct_url else entry.get("id")
        if isinstance(candidate_id, str) and candidate_id and "youtube.com" in playlist_lower:
            return f"https://www.youtube.com/watch?v={candidate_id}"

        return None

    @staticmethod
    def _to_float(value: Any) -> float:
        """Convert unknown numeric values to float safely."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _estimate_filesize_mb(cls, fmt: Dict[str, Any], duration: Any) -> float:
        """Calculate filesize in MB; fallback to bitrate estimation when missing."""

        def estimate_single(format_row: Dict[str, Any]) -> float:
            size_bytes = cls._to_float(format_row.get("filesize") or format_row.get("filesize_approx"))
            if size_bytes > 0:
                return size_bytes / (1024 * 1024)

            duration_seconds = cls._to_float(duration)
            tbr_kbps = cls._to_float(format_row.get("tbr"))
            if tbr_kbps <= 0:
                tbr_kbps = cls._to_float(format_row.get("vbr")) + cls._to_float(format_row.get("abr"))

            if duration_seconds > 0 and tbr_kbps > 0:
                estimated_bytes = (duration_seconds * tbr_kbps * 1000) / 8
                return estimated_bytes / (1024 * 1024)

            return 0.0

        total_mb = estimate_single(fmt)
        paired_audio = fmt.get("_paired_audio_format")
        if isinstance(paired_audio, dict):
            total_mb += estimate_single(paired_audio)

        return round(total_mb, 2)

    @classmethod
    def _estimate_filesize_mb_from_quality_hint(
        cls,
        quality_label: str,
        duration: Any,
        selected_format: Optional[Dict[str, Any]],
    ) -> float:
        """Estimate playlist entry size from coarse quality hints when yt-dlp omits exact size/bitrate."""
        duration_seconds = cls._to_float(duration)
        if duration_seconds <= 0:
            return 0.0

        quality = str(quality_label or "En İyi")
        audio_only = quality == "Sadece Ses"
        height = int(cls._to_float((selected_format or {}).get("height")))

        if audio_only:
            target_kbps = 160.0
        else:
            if height >= 1440:
                target_kbps = 9000.0
            elif height >= 1080:
                target_kbps = 5000.0
            elif height >= 720:
                target_kbps = 2800.0
            elif height >= 480:
                target_kbps = 1400.0
            elif height > 0:
                target_kbps = 800.0
            elif quality == "1080p":
                target_kbps = 5000.0
            elif quality == "720p":
                target_kbps = 2800.0
            elif quality == "480p":
                target_kbps = 1400.0
            else:
                target_kbps = 2800.0

        estimated_bytes = (duration_seconds * target_kbps * 1000) / 8
        return round(estimated_bytes / (1024 * 1024), 2)

    @classmethod
    def _build_instant_estimate_fields(cls, quality_label: str, duration: Any) -> Dict[str, Any]:
        """Duration-based size estimate for every quality label, computed instantly from
        the shallow playlist stub (no format list yet, so no `selected_format` to work from).
        Lets playlist rows show a plausible size immediately instead of a blank cell while
        the parallel detail pass resolves exact per-video values -- which then overwrite
        these via `_PROGRESSIVE_DETAIL_KEYS` in the UI layer.

        Resolution/format_note are intentionally left out here: unlike size, they can't be
        estimated without real format data, so the UI leaves those chips blank until the
        entry actually resolves.
        """
        quality_labels = ["En İyi", "1080p", "720p", "480p", "Sadece Ses"]
        size_by_quality = {
            label: cls._estimate_filesize_mb_from_quality_hint(label, duration, None)
            for label in quality_labels
        }
        return {
            "filesize_mb": size_by_quality.get(quality_label, 0.0),
            "size_by_quality_mb": size_by_quality,
        }

    @classmethod
    def compute_size_by_quality(cls, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute per-quality size/resolution maps from a raw yt-dlp info dict.

        Returns a dict with keys:
          size_by_quality_mb, resolution_by_quality, format_note_by_quality
        """
        formats = info.get("formats", [])
        duration = info.get("duration", 0)
        quality_labels = ["En İyi", "1080p", "720p", "480p", "Sadece Ses"]

        size_by_quality: Dict[str, float] = {}
        resolution_by_quality: Dict[str, str] = {}
        format_note_by_quality: Dict[str, str] = {}

        for quality_label in quality_labels:
            selected = cls._pick_format_for_quality(formats, quality_label)
            if not selected:
                continue

            estimated_size_mb = cls._estimate_filesize_mb(selected, duration)
            if estimated_size_mb <= 0:
                estimated_size_mb = cls._estimate_filesize_mb_from_quality_hint(
                    quality_label,
                    duration,
                    selected,
                )
            size_by_quality[quality_label] = estimated_size_mb

            if quality_label == "Sadece Ses":
                resolution_by_quality[quality_label] = "Audio"
            else:
                width = int(cls._to_float(selected.get("width")))
                height = int(cls._to_float(selected.get("height")))
                if width and height:
                    resolution_by_quality[quality_label] = f"{width}x{height}"
                else:
                    resolution_by_quality[quality_label] = selected.get("format_note", "Unknown") or "Unknown"

            format_note_by_quality[quality_label] = selected.get("format_note", "") or ""

        return {
            "size_by_quality_mb": size_by_quality,
            "resolution_by_quality": resolution_by_quality,
            "format_note_by_quality": format_note_by_quality,
        }

    @classmethod
    def _pick_format_for_quality(
        cls,
        formats: List[Dict[str, Any]],
        quality_label: str,
    ) -> Optional[Dict[str, Any]]:
        """Pick the most suitable yt-dlp format row for a quality label."""
        if not isinstance(formats, list) or not formats:
            return None

        quality = str(quality_label or "En İyi")
        max_height_by_quality = {
            "1080p": 1080,
            "720p": 720,
            "480p": 480,
        }
        max_height = max_height_by_quality.get(quality)
        audio_only = quality == "Sadece Ses"

        combined_candidates: List[Dict[str, Any]] = []
        video_only_candidates: List[Dict[str, Any]] = []
        audio_candidates: List[Dict[str, Any]] = []

        for fmt in formats:
            if not isinstance(fmt, dict):
                continue

            has_video = fmt.get("vcodec") not in (None, "none")
            has_audio = fmt.get("acodec") not in (None, "none")

            if audio_only:
                if has_audio and not has_video:
                    audio_candidates.append(fmt)
                continue

            if has_audio and not has_video:
                audio_candidates.append(fmt)

            if not has_video:
                continue

            height = int(cls._to_float(fmt.get("height")))
            if max_height and height and height > max_height:
                continue

            if has_audio:
                combined_candidates.append(fmt)
            else:
                video_only_candidates.append(fmt)

        if not combined_candidates and not video_only_candidates and not audio_only:
            for fmt in formats:
                if not isinstance(fmt, dict):
                    continue
                has_video = fmt.get("vcodec") not in (None, "none")
                has_audio = fmt.get("acodec") not in (None, "none")
                if audio_only and has_audio:
                    audio_candidates.append(fmt)
                elif not audio_only and has_video:
                    if has_audio:
                        combined_candidates.append(fmt)
                    else:
                        video_only_candidates.append(fmt)

        if audio_only:
            candidates = audio_candidates
        elif video_only_candidates:
            # Download yoluyla tutarlı davran: önce video-only seçip en iyi audio ile eşleştir.
            candidates = video_only_candidates
        else:
            candidates = combined_candidates

        if not candidates:
            return None

        def candidate_sort_key(fmt: Dict[str, Any]) -> tuple:
            height = cls._to_float(fmt.get("height"))
            if audio_only:
                bitrate = cls._to_float(fmt.get("abr")) or cls._to_float(fmt.get("tbr"))
            else:
                bitrate = cls._to_float(fmt.get("tbr")) or (
                    cls._to_float(fmt.get("vbr")) + cls._to_float(fmt.get("abr"))
                )
            size = cls._to_float(fmt.get("filesize") or fmt.get("filesize_approx"))
            return (height, bitrate, size)

        candidates.sort(key=candidate_sort_key, reverse=True)
        selected = dict(candidates[0])

        if not audio_only and selected.get("acodec") in (None, "none") and audio_candidates:
            audio_candidates.sort(key=candidate_sort_key, reverse=True)
            selected["_paired_audio_format"] = audio_candidates[0]

        return selected

    def extract_playlist_entries(
        self,
        url: str,
        timeout: int = 120,
        with_details: bool = False,
        quality_label: str = "En İyi",
    ) -> List[Dict[str, Any]]:
        """
        Extract playlist entries without downloading media files.

        Args:
            url: Playlist URL
            timeout: Request timeout
            with_details: If True, includes detailed info (filesize, resolution) for each video
            quality_label: UI quality label used for default per-entry details

        Returns:
            Normalized entry list with keys: title, url, duration, uploader.
            If with_details=True, also includes: filesize_mb, resolution, format_note,
            plus per-quality maps (size_by_quality_mb, resolution_by_quality, format_note_by_quality).
        """
        cmd = [
            self.executable_path,
            "--dump-single-json",
            "--no-warnings",
            "--skip-download",
            url,
        ]

        if not with_details:
            cmd.insert(2, "--flat-playlist")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                **get_hidden_subprocess_kwargs(),
            )
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp playlist extraction timed out")
            return []
        except Exception as exc:
            logger.error("yt-dlp playlist extraction error: %s", exc)
            return []

        if result.returncode != 0:
            logger.error("yt-dlp playlist extraction failed: %s", result.stderr)
            return []

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            logger.error("yt-dlp playlist JSON parse error: %s", exc)
            return []

        entries = payload.get("entries")
        if not isinstance(entries, list):
            return []

        playlist_url = str(payload.get("webpage_url") or url)
        normalized_entries: List[Dict[str, Any]] = []
        for item in entries:
            if not isinstance(item, dict):
                continue

            entry_url = self._resolve_playlist_entry_url(item, playlist_url)
            if not entry_url:
                continue

            entry_data = {
                "title": item.get("title") or item.get("id") or "Unknown",
                "url": entry_url,
                "duration": item.get("duration", 0),
                "uploader": item.get("uploader") or item.get("channel") or "",
                "channel": item.get("channel") or item.get("uploader") or "",
                "album": item.get("album") or "",
                "view_count": item.get("view_count", 0),
                "like_count": item.get("like_count", 0),
                "upload_date": item.get("upload_date") or "",
            }

            if with_details:
                formats = item.get("formats", [])
                quality_labels = ["En İyi", "1080p", "720p", "480p", "Sadece Ses"]
                size_by_quality: Dict[str, float] = {}
                resolution_by_quality: Dict[str, str] = {}
                format_note_by_quality: Dict[str, str] = {}

                duration = item.get("duration", 0)
                for current_quality in quality_labels:
                    selected = self._pick_format_for_quality(formats, current_quality)
                    if not selected:
                        continue

                    size_by_quality[current_quality] = self._estimate_filesize_mb(selected, duration)

                    if current_quality == "Sadece Ses":
                        resolution_by_quality[current_quality] = "Audio"
                    else:
                        width = int(self._to_float(selected.get("width")))
                        height = int(self._to_float(selected.get("height")))
                        if width > 0 and height > 0:
                            resolution_by_quality[current_quality] = f"{width}x{height}"
                        else:
                            resolution_by_quality[current_quality] = (
                                selected.get("format_note", "Unknown") or "Unknown"
                            )

                    format_note_by_quality[current_quality] = selected.get("format_note", "") or ""

                selected_size = size_by_quality.get(quality_label)
                selected_resolution = resolution_by_quality.get(quality_label)
                selected_note = format_note_by_quality.get(quality_label)

                # Size could be unknown for DASH video-only formats; in that case
                # keep quality-specific resolution/note and only fallback for size.
                if selected_size is None or selected_size <= 0.0:
                    selected_size = size_by_quality.get("En İyi", 0.0)
                if selected_size is None or selected_size <= 0.0:
                    selected = self._pick_format_for_quality(formats, quality_label)
                    selected_size = self._estimate_filesize_mb_from_quality_hint(
                        quality_label,
                        duration,
                        selected,
                    )

                if not selected_resolution:
                    selected_resolution = resolution_by_quality.get("En İyi", "Unknown")

                if selected_note is None:
                    selected_note = format_note_by_quality.get("En İyi", "")

                entry_data["filesize_mb"] = selected_size
                entry_data["resolution"] = selected_resolution
                entry_data["format_note"] = selected_note
                entry_data["size_by_quality_mb"] = size_by_quality
                entry_data["resolution_by_quality"] = resolution_by_quality
                entry_data["format_note_by_quality"] = format_note_by_quality

            normalized_entries.append(entry_data)

        return normalized_entries

    @staticmethod
    def _normalize_shallow_entry(stub: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize a yt-dlp library shallow (unresolved) playlist entry to RAVN's schema."""
        entry_url = stub.get("url")
        if not isinstance(entry_url, str) or not entry_url.startswith(("http://", "https://")):
            video_id = stub.get("id")
            if not video_id:
                return None
            entry_url = f"https://www.youtube.com/watch?v={video_id}"

        thumbnails = stub.get("thumbnails") or []
        thumbnail_url = ""
        if isinstance(thumbnails, list) and thumbnails:
            last = thumbnails[-1]
            if isinstance(last, dict):
                thumbnail_url = last.get("url") or ""

        return {
            "title": stub.get("title") or stub.get("id") or "Unknown",
            "url": entry_url,
            "duration": stub.get("duration", 0),
            "uploader": stub.get("uploader") or stub.get("channel") or "",
            "channel": stub.get("channel") or stub.get("uploader") or "",
            "album": "",
            "view_count": stub.get("view_count", 0),
            "like_count": stub.get("like_count", 0),
            "upload_date": stub.get("upload_date") or "",
            "thumbnail_url": thumbnail_url,
        }

    @classmethod
    def _build_detail_fields(cls, full_info: Dict[str, Any], quality_label: str) -> Dict[str, Any]:
        """Compute the same size/quality detail fields extract_playlist_entries(with_details=True) produces."""
        size_maps = cls.compute_size_by_quality(full_info)
        size_by_quality = size_maps["size_by_quality_mb"]
        resolution_by_quality = size_maps["resolution_by_quality"]
        format_note_by_quality = size_maps["format_note_by_quality"]

        selected_size = size_by_quality.get(quality_label)
        selected_resolution = resolution_by_quality.get(quality_label)
        selected_note = format_note_by_quality.get(quality_label)

        if selected_size is None or selected_size <= 0.0:
            selected_size = size_by_quality.get("En İyi", 0.0)
        if not selected_resolution:
            selected_resolution = resolution_by_quality.get("En İyi", "Unknown")
        if selected_note is None:
            selected_note = format_note_by_quality.get("En İyi", "")

        return {
            "filesize_mb": selected_size,
            "resolution": selected_resolution,
            "format_note": selected_note,
            "size_by_quality_mb": size_by_quality,
            "resolution_by_quality": resolution_by_quality,
            "format_note_by_quality": format_note_by_quality,
        }

    def extract_playlist_entries_progressive(
        self,
        url: str,
        quality_label: str,
        on_shallow_ready: Callable[[List[Dict[str, Any]]], None],
        on_entry_resolved: Callable[[int, Dict[str, Any]], None],
        is_cancelled: Optional[Callable[[], bool]] = None,
        max_workers: int = 6,
    ) -> bool:
        """
        Extract playlist entries via the yt-dlp Python library instead of two blocking
        subprocess calls. Yields results progressively: the shallow (fast) list arrives
        via on_shallow_ready almost immediately (also carries real thumbnail URLs and an
        instant duration-based size estimate per entry -- see _build_instant_estimate_fields
        -- so rows never render blank), then each entry's real size/quality/resolution is
        resolved and reported via on_entry_resolved as soon as it's ready.

        Detail resolution runs on a bounded thread pool (max_workers, default 6): each
        entry's info fetch is a separate network round-trip, so resolving them one at a
        time serially (the original approach) left every row after the first waiting on
        every prior row's network call. Threads are I/O-bound here (network extraction),
        so the GIL is released during the wait and this parallelizes well -- though expect
        sub-linear speedup, not a clean Nx, since YouTube's signature deciphering is CPU
        work that still contends for the GIL. Each worker thread gets its own YoutubeDL
        instance (thread-local, lazily created and reused across that thread's tasks) --
        a single YoutubeDL is not safe to share across threads.

        Both callbacks may now be invoked from different worker threads (out of order,
        keyed by index) rather than always the same calling thread; callers running this
        from a background thread must bridge every callback invocation to the UI thread
        themselves (e.g. Tkinter's `after(0, ...)`, which is thread-safe to call from any
        thread).

        Returns True if the library path was used, False if the library is unavailable
        (caller should fall back to extract_playlist_entries()).
        """
        ytdlp_lib = _get_ytdlp_library()
        if ytdlp_lib is None:
            return False

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": "discard_in_playlist",
        }

        try:
            with ytdlp_lib.YoutubeDL(ydl_opts) as ydl:
                shallow_result = ydl.extract_info(url, download=False, process=False)
                stubs = list((shallow_result or {}).get("entries") or [])

                normalized_entries: List[Dict[str, Any]] = []
                valid_stubs: List[Dict[str, Any]] = []
                for stub in stubs:
                    if not isinstance(stub, dict):
                        continue
                    normalized = self._normalize_shallow_entry(stub)
                    if normalized is None:
                        continue
                    normalized.update(
                        self._build_instant_estimate_fields(quality_label, normalized.get("duration", 0))
                    )
                    normalized_entries.append(normalized)
                    valid_stubs.append(stub)

                on_shallow_ready(normalized_entries)

            if is_cancelled is not None and is_cancelled():
                return True
            if not valid_stubs:
                return True

            thread_local = threading.local()
            clients_lock = threading.Lock()
            created_clients: List[Any] = []

            def get_thread_client():
                client = getattr(thread_local, "ydl", None)
                if client is None:
                    client = ytdlp_lib.YoutubeDL(ydl_opts)
                    thread_local.ydl = client
                    with clients_lock:
                        created_clients.append(client)
                return client

            def resolve_entry(index: int) -> Optional[Dict[str, Any]]:
                if is_cancelled is not None and is_cancelled():
                    return None
                entry_url = normalized_entries[index].get("url")
                if not entry_url:
                    return None
                client = get_thread_client()
                full_info = client.extract_info(entry_url, download=False)
                detail_fields = self._build_detail_fields(full_info, quality_label)
                resolved_entry = dict(normalized_entries[index])
                resolved_entry.update(detail_fields)
                return resolved_entry

            try:
                with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
                    future_to_index = {}
                    for index in range(len(valid_stubs)):
                        if is_cancelled is not None and is_cancelled():
                            break
                        future_to_index[executor.submit(resolve_entry, index)] = index

                    for future in as_completed(future_to_index):
                        index = future_to_index[future]
                        try:
                            resolved_entry = future.result()
                        except Exception as exc:
                            logger.warning("yt-dlp progressive resolve failed for entry %s: %s", index, exc)
                            continue
                        if resolved_entry is None:
                            continue
                        on_entry_resolved(index, resolved_entry)
            finally:
                for client in created_clients:
                    try:
                        client.close()
                    except Exception:  # pragma: no cover - defensive cleanup
                        pass

            return True
        except Exception as exc:
            logger.error("yt-dlp library playlist extraction failed: %s", exc)
            return False

    def list_formats(self, url: str) -> Optional[List[Dict[str, Any]]]:
        """
        List available formats for a URL.

        Args:
            url: Media URL

        Returns:
            List of format dictionaries, or None on error
        """
        info = self.extract_info(url)
        if info and "formats" in info:
            return info["formats"]
        return None

    def get_version(self) -> Optional[str]:
        """Get yt-dlp version string."""
        try:
            result = subprocess.run(
                [self.executable_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                **get_hidden_subprocess_kwargs(),
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as exc:
            logger.debug("yt-dlp version probe failed: %s", exc)
        return None

    def update(self, timeout: int = 300) -> bool:
        """
        Update yt-dlp to latest version by downloading yt-dlp.exe from GitHub.
        Checks version to prevent downgrade loops.

        Args:
            timeout: Update timeout in seconds

        Returns:
            True if update successful or already up to date
        """
        try:
            import os
            from pathlib import Path

            import requests

            tools_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ravn" / "bin"
            tools_dir.mkdir(parents=True, exist_ok=True)
            target_exe = tools_dir / "yt-dlp.exe"

            logger.info("Checking latest yt-dlp release...")
            url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            latest_version = data.get("tag_name", "").strip()
            current_version = self.get_version()

            if current_version and latest_version:
                curr_v = current_version.lstrip("v").strip()
                late_v = latest_version.lstrip("v").strip()
                if curr_v == late_v:
                    logger.info("yt-dlp is already up to date: %s", current_version)
                    self.executable_path = str(target_exe) if target_exe.exists() else self.executable_path
                    return True

            download_url = None
            for asset in data.get("assets", []):
                if asset.get("name") == "yt-dlp.exe":
                    download_url = asset.get("browser_download_url")
                    break

            if not download_url:
                logger.error("yt-dlp.exe asset not found in latest release")
                return False

            logger.info("Downloading yt-dlp.exe from %s", download_url)
            dl_response = requests.get(download_url, stream=True, timeout=timeout)
            dl_response.raise_for_status()

            temp_exe = target_exe.with_suffix(".tmp")
            with open(temp_exe, "wb") as f:
                for chunk in dl_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            if target_exe.exists():
                try:
                    target_exe.unlink()
                except Exception as e:
                    logger.warning("Could not delete old yt-dlp.exe: %s", e)

            temp_exe.rename(target_exe)
            logger.info("yt-dlp updated successfully to %s", latest_version)

            self.executable_path = str(target_exe)
            return True
        except Exception as exc:
            logger.error("yt-dlp update failed: %s", exc)
            return False


def get_ytdlp_runner(ytdlp_path: Optional[str] = None) -> YtDlpRunner:
    """Create and return a YtDlpRunner instance."""
    import os
    from pathlib import Path

    if not ytdlp_path:
        tools_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ravn" / "bin"
        local_exe = tools_dir / "yt-dlp.exe"
        if local_exe.exists():
            ytdlp_path = str(local_exe)
        else:
            ytdlp_path = "yt-dlp"

    return YtDlpRunner(ytdlp_path)
