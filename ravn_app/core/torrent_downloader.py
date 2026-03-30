"""
RAVN - High-level torrent downloader built on top of Aria2Runner.
"""

from __future__ import annotations

import http.server
import logging
import os
import socket
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional

from ravn_app.core.runners.aria2 import Aria2Runner


logger = logging.getLogger(__name__)

_VIDEO_AUDIO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".webm",
    ".mp3", ".m4a", ".flac", ".ogg",
}


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

    def detect_source_type(self, source: str) -> TorrentSource:
        """
        Determine whether *source* is a magnet link or a .torrent file path.

        Raises:
            ValueError: if the source format is not recognised.
        """
        if source.startswith("magnet:?xt=urn:"):
            return TorrentSource.MAGNET
        if source.lower().endswith(".torrent"):
            return TorrentSource.TORRENT_FILE
        raise ValueError(f"Desteklenmeyen kaynak türü: {source!r}")

    def download(
        self,
        source: str,
        output_dir: str,
        mode: TorrentDownloadMode = TorrentDownloadMode.FULL,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        seed_time: int = 0,
    ) -> TorrentDownloadResult:
        """
        Download a magnet link or .torrent file.

        Args:
            source: Magnet URI or path to a .torrent file.
            output_dir: Directory where downloaded files will be placed.
            mode: FULL, SEQUENTIAL, or STREAM.
            progress_callback: Optional callback(percent: int, message: str).
            seed_time: Minutes to seed after download completes (0 = no seed).

        Returns:
            TorrentDownloadResult with outcome details.
        """
        sequential = mode in (TorrentDownloadMode.SEQUENTIAL, TorrentDownloadMode.STREAM)

        logger.info(
            "TorrentDownloader: starting download source=%r mode=%s output_dir=%r",
            source,
            mode.value,
            output_dir,
        )

        runner_result = self._runner.download(
            source,
            output_dir,
            sequential=sequential,
            seed_time=seed_time,
            progress_callback=progress_callback,
        )

        if not runner_result.success:
            logger.warning(
                "TorrentDownloader: download failed: %s",
                runner_result.error_message,
            )
            return TorrentDownloadResult(
                success=False,
                source=source,
                error_message=runner_result.error_message,
            )

        output_files = self._collect_output_files(output_dir)

        stream_url: Optional[str] = None
        if mode == TorrentDownloadMode.STREAM and output_files:
            stream_url = self._start_local_http_server(output_files[0])
            logger.info("TorrentDownloader: stream URL: %s", stream_url)

        return TorrentDownloadResult(
            success=True,
            source=source,
            output_files=output_files,
            stream_url=stream_url,
        )

    def cancel(self) -> bool:
        """Cancel the currently active download. Returns True if successful."""
        return self._runner.cancel()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _collect_output_files(self, output_dir: str) -> List[str]:
        """
        Return sorted absolute paths of media files found in *output_dir*.
        Only files with recognised video/audio extensions are included.
        """
        try:
            entries = os.listdir(output_dir)
        except OSError:
            logger.warning(
                "TorrentDownloader: could not list output directory %r", output_dir
            )
            return []

        matched = [
            os.path.join(output_dir, name)
            for name in entries
            if os.path.splitext(name)[1].lower() in _VIDEO_AUDIO_EXTENSIONS
        ]
        return sorted(matched)

    def _start_local_http_server(self, file_path: str) -> str:
        """
        Serve *file_path*'s parent directory over HTTP on a random local port.

        Returns:
            URL string pointing directly at the file, e.g.
            ``http://127.0.0.1:54321/video.mp4``
        """
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
            self._http_server.shutdown()
            self._http_server = None
