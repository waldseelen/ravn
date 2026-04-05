"""
RAVN - FFmpeg process runner.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
from typing import Any, Callable, Dict, List, Optional

from ravn_app.core.runners.base import BaseRunner, RunnerResult, RunnerStatus


logger = logging.getLogger(__name__)


class FFmpegRunner(BaseRunner):
    """
    Unified FFmpeg subprocess runner.
    Handles all FFmpeg and FFprobe operations with consistent error handling,
    progress reporting, and resource management.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        super().__init__(ffmpeg_path)
        self.ffprobe_path = ffprobe_path
        self._progress_pattern = re.compile(
            r"frame=\s*(\d+).*?fps=\s*([\d.]+).*?time=(\d+:\d+:\d+\.\d+)"
        )
        self._duration_pattern = re.compile(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)")

    def _build_command(
        self,
        input_file: str,
        output_file: str,
        video_args: Optional[List[str]] = None,
        audio_args: Optional[List[str]] = None,
        extra_args: Optional[List[str]] = None,
        overwrite: bool = True,
    ) -> List[str]:
        """Build FFmpeg command."""
        cmd = [self.executable_path, "-i", input_file]

        if video_args:
            cmd.extend(video_args)
        if audio_args:
            cmd.extend(audio_args)
        if extra_args:
            cmd.extend(extra_args)
        if overwrite:
            cmd.append("-y")

        cmd.append(output_file)
        return cmd

    def _parse_error(self, stderr: str) -> str:
        """Parse FFmpeg stderr to extract user-friendly error message."""
        error_patterns = [
            (r"No such file or directory", "File not found"),
            (r"Invalid data found when processing input", "Invalid or corrupted input file"),
            (r"does not contain any stream", "No media streams found in file"),
            (r"Unknown encoder", "Unsupported encoder/codec"),
            (r"Encoder .+ not found", "Required encoder not available"),
            (r"Permission denied", "Permission denied - cannot access file"),
            (r"No space left on device", "Disk full - no space left"),
            (r"Could not open file", "Cannot open file for writing"),
            (r"Invalid argument", "Invalid parameter provided"),
            (r"Avi file size limit", "Output file size exceeds limit"),
            (r"decode_slice_header error", "Video decoding error - file may be corrupted"),
            (r"moov atom not found", "Invalid MP4 file - missing metadata"),
        ]

        for pattern, message in error_patterns:
            if re.search(pattern, stderr, re.IGNORECASE):
                return message

        lines = [line.strip() for line in stderr.split("\n") if line.strip()]
        for line in reversed(lines):
            if "error" in line.lower() or "failed" in line.lower():
                return line[:200]

        return "FFmpeg operation failed"

    def run(
        self,
        input_file: str,
        output_file: str,
        video_args: Optional[List[str]] = None,
        audio_args: Optional[List[str]] = None,
        extra_args: Optional[List[str]] = None,
        timeout: Optional[int] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        use_realtime_progress: bool = False,
    ) -> RunnerResult:
        """
        Run an FFmpeg conversion/operation.

        Args:
            input_file: Input file path
            output_file: Output file path
            video_args: Video encoding arguments (e.g., ['-c:v', 'libx264'])
            audio_args: Audio encoding arguments (e.g., ['-c:a', 'aac'])
            extra_args: Additional FFmpeg arguments
            timeout: Process timeout in seconds
            progress_callback: Callback for progress updates (percent, status)
            use_realtime_progress: If True, use -progress pipe:1 for real-time progress

        Returns:
            RunnerResult with success status and details
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        command = self._build_command(
            input_file,
            output_file,
            video_args,
            audio_args,
            extra_args,
        )

        logger.info("FFmpeg: Converting %s -> %s", input_file, output_file)

        if use_realtime_progress and progress_callback:
            result = self._run_with_realtime_progress(
                command,
                input_file,
                timeout,
                progress_callback,
            )
        else:
            result = self._run_process(command, timeout, progress_callback)

        if result.success and os.path.exists(output_file):
            result.metadata["output_size"] = os.path.getsize(output_file)
            result.metadata["input_size"] = os.path.getsize(input_file)

        return result

    def run_raw(
        self,
        args: List[str],
        timeout: Optional[int] = None,
    ) -> RunnerResult:
        """
        Run FFmpeg with raw arguments (for advanced use cases).

        Args:
            args: Complete list of FFmpeg arguments (excluding 'ffmpeg' itself)
            timeout: Process timeout in seconds

        Returns:
            RunnerResult
        """
        command = [self.executable_path] + args
        return self._run_process(command, timeout)

    def run_ffprobe(
        self,
        args: List[str],
        timeout: Optional[int] = 60,
    ) -> RunnerResult:
        """Run FFprobe with raw arguments and normalized RunnerResult output."""
        command = [self.ffprobe_path] + args
        return self._run_process(command, timeout)

    def run_ffprobe_json(
        self,
        args: List[str],
        timeout: Optional[int] = 60,
    ) -> Optional[Dict[str, Any]]:
        """Run FFprobe and parse JSON stdout output."""
        result = self.run_ffprobe(args, timeout)
        if not result.success:
            logger.error("FFprobe error: %s", result.error_message or result.stderr)
            return None

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            logger.error("FFprobe output parse error: %s", exc)
            return None

    def probe(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Analyze media file using FFprobe.

        Args:
            file_path: Path to media file

        Returns:
            Dictionary with format and stream information, or None on error
        """
        if not os.path.exists(file_path):
            logger.error("FFprobe: File not found: %s", file_path)
            return None

        return self.run_ffprobe_json(
            [
                "-v",
                "error",
                "-show_entries",
                "format:stream",
                "-of",
                "json",
                file_path,
            ],
            timeout=60,
        )

    def get_duration(self, file_path: str) -> Optional[float]:
        """Get media duration in seconds."""
        info = self.probe(file_path)
        if info and "format" in info:
            try:
                return float(info["format"].get("duration", 0))
            except (TypeError, ValueError):
                pass
        return None

    def get_version(self) -> Optional[str]:
        """Get FFmpeg version string."""
        try:
            result = subprocess.run(
                [self.executable_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.split("\n")[0]
        except Exception:
            pass
        return None

    def check_codec_support(self, codec: str) -> bool:
        """Check if a codec is supported."""
        try:
            result = subprocess.run(
                [self.executable_path, "-encoders"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return codec in result.stdout
        except Exception:
            return False

    def _run_with_realtime_progress(
        self,
        command: List[str],
        input_file: str,
        timeout: Optional[int] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Run FFmpeg with real-time progress parsing using -progress pipe:1.

        Args:
            command: FFmpeg command list
            input_file: Input file path (for duration lookup)
            timeout: Process timeout in seconds
            progress_callback: Callback for progress updates (percent, message)

        Returns:
            RunnerResult with execution status
        """
        import time

        start_time = time.time()
        total_duration = self.get_duration(input_file) or 0
        progress_cmd = command[:-1]
        progress_cmd.extend(["-progress", "pipe:1", command[-1]])

        with self._lock:
            self.status = RunnerStatus.RUNNING

        try:
            process_env = os.environ.copy()
            logger.debug("Running FFmpeg with real-time progress: %s", " ".join(progress_cmd))

            self.current_process = subprocess.Popen(
                progress_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                env=process_env,
            )

            stderr_lines: List[str] = []
            stderr_thread = threading.Thread(
                target=lambda: stderr_lines.extend(self.current_process.stderr.readlines()),
                daemon=True,
            )
            stderr_thread.start()

            last_progress = 0
            for line in self.current_process.stdout:
                line = line.strip()

                if line.startswith("out_time_ms="):
                    try:
                        time_us = int(line.split("=")[1])
                        time_s = time_us / 1_000_000
                        if total_duration > 0:
                            percent = int(min(100, (time_s / total_duration) * 100))
                            if percent != last_progress:
                                last_progress = percent
                                if progress_callback:
                                    progress_callback(percent, f"İşleniyor: {percent}%")
                    except (IndexError, ValueError):
                        pass
                elif line.startswith("progress="):
                    status = line.split("=")[1]
                    if status == "end" and progress_callback:
                        progress_callback(100, "Tamamlandı")

                if timeout and (time.time() - start_time) > timeout:
                    raise subprocess.TimeoutExpired(progress_cmd, timeout)

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
                error_msg = self._parse_error(stderr)
                return RunnerResult(
                    success=False,
                    return_code=self.current_process.returncode,
                    stdout="",
                    stderr=stderr,
                    error_message=error_msg,
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
            logger.exception("FFmpeg real-time progress error: %s", exc)
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=str(exc),
                duration_seconds=time.time() - start_time,
            )

        finally:
            with self._lock:
                self.current_process = None


def get_ffmpeg_runner(
    ffmpeg_path: str = "ffmpeg",
    ffprobe_path: str = "ffprobe",
) -> FFmpegRunner:
    """Create and return an FFmpegRunner instance."""
    return FFmpegRunner(ffmpeg_path, ffprobe_path)
