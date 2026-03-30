"""
RAVN - aria2c process runner.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from typing import Callable, List, Optional

from ravn_app.core.error_handler import parse_aria2c_error
from ravn_app.core.runners.base import BaseRunner, RunnerResult, RunnerStatus


logger = logging.getLogger(__name__)

_PERCENT_PATTERN = re.compile(r"\((\d+)%\)")
_DL_SPEED_PATTERN = re.compile(r"DL:(\S+)")



class Aria2Runner(BaseRunner):
    """
    aria2c subprocess runner for HTTP(S), FTP, Magnet, and Torrent downloads.
    Supports real-time progress reporting via stdout line parsing.
    """

    def __init__(self, aria2c_path: str = "aria2c") -> None:
        super().__init__(aria2c_path)

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
        progress_callback: Optional[Callable[[int, str], None]],
        timeout: Optional[int],
    ) -> RunnerResult:
        """
        Launch aria2c and parse stdout lines for progress updates.
        stderr is captured separately; stdout is read line-by-line.
        """
        start_time = time.time()

        with self._lock:
            self.status = RunnerStatus.RUNNING

        try:
            process_env = os.environ.copy()
            logger.debug("aria2c command: %s", " ".join(command))

            self.current_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                env=process_env,
            )

            stderr_lines: List[str] = []
            import threading

            stderr_thread = threading.Thread(
                target=lambda: stderr_lines.extend(
                    self.current_process.stderr.readlines()
                ),
                daemon=True,
            )
            stderr_thread.start()

            for line in self.current_process.stdout:
                _handle_progress_line(line, progress_callback)

                if timeout and (time.time() - start_time) > timeout:
                    raise subprocess.TimeoutExpired(command, timeout)

            self.current_process.wait()
            stderr_thread.join(timeout=5)

            duration = time.time() - start_time
            stderr = "".join(stderr_lines)

            with self._lock:
                if self.current_process.returncode == 0:
                    self.status = RunnerStatus.COMPLETED
                    return RunnerResult(
                        success=True,
                        return_code=0,
                        stdout="",
                        stderr=stderr,
                        duration_seconds=duration,
                    )

                self.status = RunnerStatus.FAILED
                return RunnerResult(
                    success=False,
                    return_code=self.current_process.returncode,
                    stdout="",
                    stderr=stderr,
                    error_message=self._parse_error(stderr),
                    duration_seconds=duration,
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
        progress_callback: Optional[Callable[[int, str], None]] = None,
        timeout: Optional[int] = None,
    ) -> RunnerResult:
        """
        Download a URL, magnet link, or torrent file via aria2c.

        Args:
            source: URL, magnet link, or .torrent file path
            output_dir: Directory where files will be saved
            sequential: Enable sequential download (torrent head-first)
            seed_time: Seed time in minutes after download (0 = no seeding)
            progress_callback: Callback(percent, status_message)
            timeout: Hard timeout in seconds (None = no limit)

        Returns:
            RunnerResult with success status and details
        """
        os.makedirs(output_dir, exist_ok=True)
        command = self._build_command(source, output_dir, sequential, seed_time)
        logger.info("aria2c: Downloading %s -> %s", source, output_dir)
        return self._run_torrent_with_progress(command, progress_callback, timeout)

    def is_available(self) -> bool:
        """Return True if aria2c is found on PATH or local directory."""
        return self._find_executable("aria2c") is not None


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _handle_progress_line(
    line: str,
    progress_callback: Optional[Callable[[int, str], None]],
) -> None:
    """Parse a single aria2c stdout line and fire progress_callback if applicable."""
    if progress_callback is None:
        return

    percent_match = _PERCENT_PATTERN.search(line)
    if not percent_match:
        return

    percent = int(percent_match.group(1))
    dl_match = _DL_SPEED_PATTERN.search(line)
    speed_str = dl_match.group(1) if dl_match else "?"
    progress_callback(percent, f"İndiriliyor... {speed_str}/s")


def get_aria2c_runner(aria2c_path: str = "aria2c") -> Aria2Runner:
    """Create and return an Aria2Runner instance."""
    return Aria2Runner(aria2c_path)
