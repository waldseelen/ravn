"""
RAVN - aria2c process runner.
"""

from __future__ import annotations

import inspect
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from ravn_app.core.error_handler import parse_aria2c_error
from ravn_app.core.runners.base import BaseRunner, RunnerResult, RunnerStatus, get_hidden_subprocess_kwargs
from ravn_app.utils import bundled_tools

logger = logging.getLogger(__name__)

_PERCENT_PATTERN = re.compile(r"\((\d+)%\)")
_SPEED_PATTERN = re.compile(r"(?:DL|SPD):(\S+)")
_ETA_PATTERN = re.compile(r"ETA:([^\]\s]+)")
_FILE_PATTERN = re.compile(r"FILE:\s*(.+)")
_PEERS_PATTERN = re.compile(r"CN:(\d+)")
_SEEDERS_PATTERN = re.compile(r"SEED(?:ERS?)?:(\d+)", flags=re.IGNORECASE)
_SIZE_PATTERNS = (
    re.compile(r"SIZE:([0-9.]+[A-Za-z]+)\/([0-9.]+[A-Za-z]+)"),
    re.compile(r"\b([0-9.]+[A-Za-z]+)\/([0-9.]+[A-Za-z]+)\(\d+%\)"),
)
_SIZE_UNITS = {
    "B": 1,
    "KIB": 1024,
    "MIB": 1024 ** 2,
    "GIB": 1024 ** 3,
    "TIB": 1024 ** 4,
    "KB": 1024,
    "MB": 1024 ** 2,
    "GB": 1024 ** 3,
    "TB": 1024 ** 4,
}

ProgressCallback = Optional[Callable[..., None]]


@dataclass
class TorrentProgressSnapshot:
    """Parsed aria2 torrent progress snapshot."""

    percent: int
    status_message: str = ""
    name: str = ""
    downloaded_bytes: Optional[int] = None
    total_bytes: Optional[int] = None
    remaining_bytes: Optional[int] = None
    downloaded_text: str = ""
    total_text: str = ""
    remaining_text: str = ""
    speed_text: str = ""
    eta_text: str = ""
    peers: Optional[int] = None
    seeders: Optional[int] = None
    peers_text: str = ""
    seeders_text: str = ""
    raw_line: str = ""


class _Aria2ProgressParser:
    """Stateful parser for aria2 progress/stdout lines."""

    def __init__(self) -> None:
        self._current_name = ""
        self._last_snapshot: Optional[TorrentProgressSnapshot] = None

    def parse_line(self, line: str) -> Optional[TorrentProgressSnapshot]:
        text = line.strip()
        if not text:
            return None

        file_match = _FILE_PATTERN.search(text)
        if file_match:
            candidate_name = self._extract_name(file_match.group(1))
            if candidate_name:
                self._current_name = candidate_name
                if self._last_snapshot is not None:
                    self._last_snapshot = self._clone_snapshot(self._last_snapshot, name=candidate_name)
                    return self._last_snapshot
            return None

        percent_match = _PERCENT_PATTERN.search(text)
        if not percent_match:
            return None

        percent = int(percent_match.group(1))
        downloaded_bytes: Optional[int] = None
        total_bytes: Optional[int] = None
        remaining_bytes: Optional[int] = None
        downloaded_text = ""
        total_text = ""
        remaining_text = ""

        size_match = self._match_size_block(text)
        if size_match is not None:
            downloaded_bytes = _parse_size_token(size_match.group(1))
            total_bytes = _parse_size_token(size_match.group(2))
            if downloaded_bytes is not None:
                downloaded_text = _format_size_bytes(downloaded_bytes)
            if total_bytes is not None:
                total_text = _format_size_bytes(total_bytes)
            if downloaded_bytes is not None and total_bytes is not None:
                remaining_bytes = max(total_bytes - downloaded_bytes, 0)
                remaining_text = _format_size_bytes(remaining_bytes)

        speed_match = _SPEED_PATTERN.search(text)
        speed_text = _normalize_speed_text(speed_match.group(1)) if speed_match else ""

        eta_match = _ETA_PATTERN.search(text)
        eta_text = eta_match.group(1) if eta_match else ""

        peers_match = _PEERS_PATTERN.search(text)
        peers = int(peers_match.group(1)) if peers_match else None
        peers_text = str(peers) if peers is not None else ""

        seeders_match = _SEEDERS_PATTERN.search(text)
        seeders = int(seeders_match.group(1)) if seeders_match else None
        seeders_text = str(seeders) if seeders is not None else ""

        snapshot = TorrentProgressSnapshot(
            percent=percent,
            name=self._current_name,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            remaining_bytes=remaining_bytes,
            downloaded_text=downloaded_text,
            total_text=total_text,
            remaining_text=remaining_text,
            speed_text=speed_text,
            eta_text=eta_text,
            peers=peers,
            seeders=seeders,
            peers_text=peers_text,
            seeders_text=seeders_text,
            raw_line=text,
        )
        snapshot.status_message = _build_status_message(snapshot)
        self._last_snapshot = snapshot
        return snapshot

    @staticmethod
    def _match_size_block(text: str):
        for pattern in _SIZE_PATTERNS:
            match = pattern.search(text)
            if match is not None:
                return match
        return None

    @staticmethod
    def _extract_name(raw_value: str) -> str:
        candidate = raw_value.strip().strip("'\"")
        if not candidate:
            return ""

        upper_candidate = candidate.upper()
        if "[METADATA]" in upper_candidate or "[MEMORY]" in upper_candidate:
            return ""

        path_candidate = candidate.replace("\\", "/").rstrip("/")
        name = Path(path_candidate).name or candidate
        return name.strip()

    @staticmethod
    def _clone_snapshot(
        snapshot: TorrentProgressSnapshot,
        *,
        name: Optional[str] = None,
    ) -> TorrentProgressSnapshot:
        cloned = TorrentProgressSnapshot(
            percent=snapshot.percent,
            status_message=snapshot.status_message,
            name=name if name is not None else snapshot.name,
            downloaded_bytes=snapshot.downloaded_bytes,
            total_bytes=snapshot.total_bytes,
            remaining_bytes=snapshot.remaining_bytes,
            downloaded_text=snapshot.downloaded_text,
            total_text=snapshot.total_text,
            remaining_text=snapshot.remaining_text,
            speed_text=snapshot.speed_text,
            eta_text=snapshot.eta_text,
            peers=snapshot.peers,
            seeders=snapshot.seeders,
            peers_text=snapshot.peers_text,
            seeders_text=snapshot.seeders_text,
            raw_line=snapshot.raw_line,
        )
        cloned.status_message = _build_status_message(cloned)
        return cloned


class Aria2Runner(BaseRunner):
    """
    aria2c subprocess runner for HTTP(S), FTP, Magnet, and Torrent downloads.
    Supports real-time progress reporting via stdout line parsing.
    """

    def __init__(self, aria2c_path: str = "aria2c") -> None:
        # Use the aria2c a packaged build shipped with, when there is one. An explicit
        # user-configured path wins; with nothing bundled the name passes through
        # unchanged so BaseRunner still resolves it from PATH at execution time.
        super().__init__(bundled_tools.prefer_bundled(aria2c_path, "aria2c"))

    # ------------------------------------------------------------------
    # BaseRunner abstract method implementations
    # ------------------------------------------------------------------

    def _build_command(
        self,
        source: str,
        output_dir: str,
        sequential: bool = False,
        seed_time: int = 0,
        extra_args: Optional[List[str]] = None,
    ) -> List[str]:
        """Build the aria2c command list."""
        cmd: List[str] = [
            self.executable_path,
            f"--dir={output_dir}",
            "--console-log-level=notice",
            "--show-console-readout=false",
            "--summary-interval=1",
        ]

        if sequential:
            cmd.extend([
                "--file-allocation=none",
                "--enable-sequential-download=true",
                "--bt-prioritize-piece=head=5M",
            ])

        if seed_time == 0:
            cmd.append("--seed-time=0")

        if extra_args:
            cmd.extend(extra_args)

        cmd.append(source)
        return cmd

    def _parse_error(self, stderr: str) -> str:
        """Map aria2c error codes and keywords to Turkish messages."""
        return parse_aria2c_error(stderr)

    # ------------------------------------------------------------------
    # Progress-aware execution
    # ------------------------------------------------------------------

    def _run_torrent_with_progress(
        self,
        command: List[str],
        progress_callback: ProgressCallback,
        timeout: Optional[int],
    ) -> RunnerResult:
        """
        Launch aria2c and parse stdout lines for progress updates.
        stderr is captured separately; stdout is read line-by-line.
        """
        start_time = time.time()
        parser = _Aria2ProgressParser()
        last_progress: Optional[TorrentProgressSnapshot] = None

        with self._lock:
            self.status = RunnerStatus.RUNNING

        try:
            process_env = os.environ.copy()
            logger.debug("aria2c command: %s", " ".join(command))

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                env=process_env,
                **get_hidden_subprocess_kwargs(),
            )
            self.current_process = process
            # stdout=PIPE/stderr=PIPE guarantee these streams exist; bind locally so the
            # reads below are on a known-non-None Popen rather than the Optional attribute.
            assert process.stdout is not None and process.stderr is not None
            stderr_stream = process.stderr  # narrowed non-None local for the thread lambda

            stderr_lines: List[str] = []
            import threading

            stderr_thread = threading.Thread(
                target=lambda: stderr_lines.extend(
                    stderr_stream.readlines()
                ),
                daemon=True,
            )
            stderr_thread.start()

            for line in process.stdout:
                snapshot = _handle_progress_line(line, progress_callback, parser)
                if snapshot is not None:
                    last_progress = snapshot

                if timeout and (time.time() - start_time) > timeout:
                    raise subprocess.TimeoutExpired(command, timeout)

            self.current_process.wait()
            stderr_thread.join(timeout=5)

            duration = time.time() - start_time
            stderr = "".join(stderr_lines)

            with self._lock:
                status = self.status

            if status == RunnerStatus.CANCELLED:
                return RunnerResult(
                    success=False,
                    return_code=self.current_process.returncode,
                    stdout="",
                    stderr=stderr,
                    error_message="Cancelled",
                    duration_seconds=duration,
                    metadata={"cancelled": True, "progress": last_progress},
                )

            with self._lock:
                if self.current_process.returncode == 0:
                    self.status = RunnerStatus.COMPLETED
                    return RunnerResult(
                        success=True,
                        return_code=0,
                        stdout="",
                        stderr=stderr,
                        duration_seconds=duration,
                        metadata={"progress": last_progress},
                    )

                self.status = RunnerStatus.FAILED
                return RunnerResult(
                    success=False,
                    return_code=self.current_process.returncode,
                    stdout="",
                    stderr=stderr,
                    error_message=self._parse_error(stderr),
                    duration_seconds=duration,
                    metadata={"progress": last_progress},
                )

        except subprocess.TimeoutExpired:
            with self._lock:
                self.status = RunnerStatus.TIMEOUT
            if self.current_process:
                self.current_process.kill()
                self.current_process.wait()
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message="Process timed out",
                duration_seconds=time.time() - start_time,
                metadata={"progress": last_progress},
            )

        except Exception as exc:
            with self._lock:
                self.status = RunnerStatus.FAILED
            logger.exception("aria2c execution error: %s", exc)
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=str(exc),
                duration_seconds=time.time() - start_time,
                metadata={"progress": last_progress},
            )

        finally:
            with self._lock:
                self.current_process = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def download(
        self,
        source: str,
        output_dir: str,
        sequential: bool = False,
        seed_time: int = 0,
        progress_callback: ProgressCallback = None,
        timeout: Optional[int] = None,
    ) -> RunnerResult:
        """
        Download a URL, magnet link, or torrent file via aria2c.

        Args:
            source: URL, magnet link, or .torrent file path
            output_dir: Directory where files will be saved
            sequential: Enable sequential download (torrent head-first)
            seed_time: Seed time in minutes after download (0 = no seeding)
            progress_callback: Callback receiving a progress snapshot or legacy
                (percent, status_message) arguments.
            timeout: Hard timeout in seconds (None = no limit)

        Returns:
            RunnerResult with success status and details
        """
        os.makedirs(output_dir, exist_ok=True)
        command = self._build_command(source, output_dir, sequential, seed_time)
        logger.info("aria2c: Downloading %s -> %s", source, output_dir)
        return self._run_torrent_with_progress(command, progress_callback, timeout)

    def is_available(self) -> bool:
        """Return True if aria2c is found on PATH or via configured path."""
        return self._find_executable(self.executable_path) is not None


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _parse_size_token(value: str) -> Optional[int]:
    token = value.strip()
    match = re.fullmatch(r"([0-9]*\.?[0-9]+)([A-Za-z]+)", token)
    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2).upper()
    multiplier = _SIZE_UNITS.get(unit)
    if multiplier is None:
        return None
    return int(number * multiplier)


def _format_size_bytes(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _normalize_speed_text(raw_speed: str) -> str:
    speed = raw_speed.strip()
    if speed.endswith("/s"):
        return speed
    if speed.endswith("s"):
        speed = speed[:-1]
    return f"{speed}/s"


def _build_status_message(snapshot: TorrentProgressSnapshot) -> str:
    parts: List[str] = []
    if snapshot.speed_text:
        parts.append(snapshot.speed_text)
    if snapshot.eta_text and snapshot.eta_text != "--":
        parts.append(f"ETA {snapshot.eta_text}")
    if snapshot.downloaded_text and snapshot.total_text:
        parts.append(f"{snapshot.downloaded_text} / {snapshot.total_text}")
    elif snapshot.downloaded_text:
        parts.append(snapshot.downloaded_text)
    return " • ".join(parts) or f"{snapshot.percent}%"


def emit_torrent_progress(
    progress_callback: ProgressCallback,
    snapshot: TorrentProgressSnapshot,
) -> None:
    """Emit torrent progress to either new-style or legacy callbacks."""
    if progress_callback is None:
        return

    try:
        signature = inspect.signature(progress_callback)
        parameters = list(signature.parameters.values())
        accepts_varargs = any(param.kind == inspect.Parameter.VAR_POSITIONAL for param in parameters)
        positional_count = sum(
            1
            for param in parameters
            if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        )

        if accepts_varargs or positional_count <= 1:
            progress_callback(snapshot)
        else:
            progress_callback(snapshot.percent, snapshot.status_message)
    except (TypeError, ValueError):
        progress_callback(snapshot.percent, snapshot.status_message)


def _handle_progress_line(
    line: str,
    progress_callback: ProgressCallback,
    parser: Optional[_Aria2ProgressParser] = None,
) -> Optional[TorrentProgressSnapshot]:
    """Parse a single aria2 stdout line and fire progress_callback if applicable."""
    active_parser = parser or _Aria2ProgressParser()
    snapshot = active_parser.parse_line(line)
    if snapshot is not None:
        emit_torrent_progress(progress_callback, snapshot)
    return snapshot


def get_aria2c_runner(aria2c_path: str = "aria2c") -> Aria2Runner:
    """Create and return an Aria2Runner instance."""
    return Aria2Runner(aria2c_path)
