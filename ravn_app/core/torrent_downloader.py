"""
RAVN - High-level torrent downloader built on top of Aria2Runner.
"""

from __future__ import annotations

import http.server
import logging
import os
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional
from urllib.parse import parse_qs, unquote_plus, urlparse

from ravn_app.core.runners.aria2 import Aria2Runner, ProgressCallback, TorrentProgressSnapshot, emit_torrent_progress

logger = logging.getLogger(__name__)

_VIDEO_AUDIO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".webm",
    ".mp3", ".m4a", ".flac", ".ogg",
}
_SKIP_OUTPUT_EXTENSIONS = {".aria2", ".torrent"}


class TorrentSource(Enum):
    MAGNET = "magnet"
    TORRENT_FILE = "torrent_file"


class TorrentDownloadMode(Enum):
    FULL = "full"
    SEQUENTIAL = "sequential"
    STREAM = "stream"


@dataclass
class TorrentDownloadResult:
    success: bool
    source: str
    output_files: List[str] = field(default_factory=list)
    error_message: str = ""
    stream_url: Optional[str] = None
    display_name: str = ""
    primary_file: Optional[str] = None
    cancelled: bool = False


class TorrentDownloader:
    """
    High-level interface for downloading torrents via aria2c.
    Supports full, sequential, and streaming (local HTTP) modes.
    """

    def __init__(self, aria2c_path: str = "aria2c") -> None:
        self._runner = Aria2Runner(aria2c_path)
        self._http_server: Optional[http.server.HTTPServer] = None
        self._http_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if aria2c is accessible."""
        return self._runner.is_available()

    @staticmethod
    def is_playable_media(file_path: str) -> bool:
        """Return True when *file_path* looks like playable audio/video media."""
        return os.path.splitext(file_path)[1].lower() in _VIDEO_AUDIO_EXTENSIONS

    def detect_source_type(self, source: str) -> TorrentSource:
        """
        Determine whether *source* is a magnet link or a .torrent file path.

        Raises:
            ValueError: if the source format is not recognised.
        """
        normalized = source.strip()
        lowered = normalized.lower()
        parsed = urlparse(normalized)
        parsed_path = parsed.path or normalized

        if lowered.startswith("magnet:?") and "xt=urn:" in lowered:
            return TorrentSource.MAGNET
        if parsed_path.lower().endswith(".torrent"):
            return TorrentSource.TORRENT_FILE
        raise ValueError(f"Desteklenmeyen kaynak türü: {source!r}")

    def infer_display_name(self, source: str) -> str:
        """Infer a user-friendly torrent name from the source string."""
        normalized = source.strip()
        lowered = normalized.lower()

        if lowered.startswith("magnet:?"):
            params = parse_qs(urlparse(normalized).query)
            display_name = unquote_plus((params.get("dn") or [""])[0]).strip()
            if display_name:
                return display_name

            info_hash_match = re.search(r"btih:([^&]+)", normalized, flags=re.IGNORECASE)
            if info_hash_match:
                return f"magnet-{info_hash_match.group(1)[:12]}"
            return "magnet"

        parsed = urlparse(normalized)
        candidate_path = parsed.path or normalized
        name = Path(candidate_path).name
        if not name:
            return normalized
        stem = Path(name).stem
        return stem or name

    def list_output_files(self, output_dir: str) -> List[str]:
        """Return all non-temporary payload files discovered under *output_dir*."""
        return self._collect_output_files(output_dir)

    def list_playable_files(self, file_paths: List[str]) -> List[str]:
        """Return only playable media files from a file-path list."""
        return [path for path in file_paths if self.is_playable_media(path)]

    def download(
        self,
        source: str,
        output_dir: str,
        mode: TorrentDownloadMode = TorrentDownloadMode.FULL,
        progress_callback: ProgressCallback = None,
        seed_time: int = 0,
    ) -> TorrentDownloadResult:
        """
        Download a magnet link or .torrent file.

        Args:
            source: Magnet URI or path to a .torrent file.
            output_dir: Directory where downloaded files will be placed.
            mode: FULL, SEQUENTIAL, or STREAM.
            progress_callback: Optional callback receiving a progress snapshot
                or legacy (percent, status_message) arguments.
            seed_time: Minutes to seed after download completes (0 = no seed).

        Returns:
            TorrentDownloadResult with outcome details.

        Raises:
            RuntimeError: If aria2c is not available.
        """
        # Check aria2c availability first
        if not self.is_available():
            error_msg = (
                "aria2c is not available. Torrent features require aria2c to be installed and accessible in PATH. "
                "Please install aria2c to use torrent downloads. See README.md for installation instructions."
            )
            logger.error(error_msg)
            return TorrentDownloadResult(
                success=False,
                source=source,
                error_message=error_msg,
                display_name=self.infer_display_name(source)
            )

        sequential = mode in (TorrentDownloadMode.SEQUENTIAL, TorrentDownloadMode.STREAM)
        display_name = self.infer_display_name(source)
        latest_progress: Optional[TorrentProgressSnapshot] = None

        self._stop_local_http_server()

        logger.info(
            "TorrentDownloader: starting download source=%r mode=%s output_dir=%r",
            source,
            mode.value,
            output_dir,
        )

        def _progress_wrapper(snapshot: TorrentProgressSnapshot) -> None:
            nonlocal latest_progress, display_name
            latest_progress = snapshot
            if snapshot.name:
                display_name = snapshot.name
            emit_torrent_progress(progress_callback, snapshot)

        runner_result = self._runner.download(
            source,
            output_dir,
            sequential=sequential,
            seed_time=seed_time,
            progress_callback=_progress_wrapper,
        )

        if not runner_result.success:
            logger.warning(
                "TorrentDownloader: download failed: %s",
                runner_result.error_message,
            )
            return TorrentDownloadResult(
                success=False,
                source=source,
                error_message="" if runner_result.metadata.get("cancelled") else runner_result.error_message,
                display_name=display_name,
                cancelled=bool(runner_result.metadata.get("cancelled")),
            )

        output_files = self.list_output_files(output_dir)
        primary_file = self._pick_primary_output_file(output_files)

        if primary_file:
            display_name = Path(primary_file).name
        elif output_files:
            display_name = Path(output_files[0]).name
        elif latest_progress and latest_progress.name:
            display_name = latest_progress.name

        stream_url: Optional[str] = None
        if mode == TorrentDownloadMode.STREAM and primary_file:
            stream_url = self._start_local_http_server(primary_file)
            logger.info("TorrentDownloader: stream URL: %s", stream_url)

        return TorrentDownloadResult(
            success=True,
            source=source,
            output_files=output_files,
            stream_url=stream_url,
            display_name=display_name,
            primary_file=primary_file,
        )

    def cancel(self) -> bool:
        """Cancel the currently active download. Returns True if successful."""
        self._stop_local_http_server()
        return self._runner.cancel()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _collect_output_files(self, output_dir: str) -> List[str]:
        """Return sorted absolute payload file paths found under *output_dir*."""
        discovered: List[str] = []

        try:
            for root, _dirs, files in os.walk(output_dir):
                for name in files:
                    extension = os.path.splitext(name)[1].lower()
                    if extension in _SKIP_OUTPUT_EXTENSIONS:
                        continue
                    discovered.append(os.path.abspath(os.path.join(root, name)))
        except OSError:
            logger.warning(
                "TorrentDownloader: could not walk output directory %r", output_dir
            )
            return []

        return sorted(discovered)

    def _pick_primary_output_file(self, file_paths: List[str]) -> Optional[str]:
        """Pick the most likely playable media file from the output list."""
        media_candidates = self.list_playable_files(file_paths)
        if not media_candidates:
            return None

        def _score(path: str) -> tuple[int, str]:
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            return size, path.lower()

        return max(media_candidates, key=_score)

    def _start_local_http_server(self, file_path: str) -> str:
        """
        Serve *file_path*'s parent directory over HTTP on a random local port.

        Returns:
            URL string pointing directly at the file, e.g.
            ``http://127.0.0.1:54321/video.mp4``
        """
        self._stop_local_http_server()
        serve_dir = os.path.dirname(os.path.abspath(file_path))

        class _Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=serve_dir, **kwargs)

            def log_message(self, fmt, *args):  # silence default access log
                logger.debug("HTTP: " + fmt, *args)

        server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        port: int = server.server_address[1]

        self._http_server = server
        self._http_thread = threading.Thread(
            target=server.serve_forever,
            daemon=True,
        )
        self._http_thread.start()

        filename = os.path.basename(file_path)
        return f"http://127.0.0.1:{port}/{filename}"

    def _stop_local_http_server(self) -> None:
        """Shut down the local HTTP server if one is running."""
        if self._http_server is not None:
            try:
                self._http_server.shutdown()
                self._http_server.server_close()
            finally:
                self._http_server = None

        if self._http_thread is not None:
            self._http_thread.join(timeout=2)
            self._http_thread = None
