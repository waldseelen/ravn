"""
RAVN - Unified Process Runners for FFmpeg and yt-dlp
Centralizes all subprocess execution for media processing tools.
"""

import os
import subprocess
import logging
import threading
import queue
import json
import re
from pathlib import Path
from typing import Optional, Dict, List, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class RunnerStatus(Enum):
    """Process execution status"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class RunnerResult:
    """Result of a runner execution"""
    success: bool
    return_code: int
    stdout: str = ""
    stderr: str = ""
    error_message: str = ""
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseRunner(ABC):
    """Abstract base class for process runners"""

    def __init__(self, executable_path: str):
        self.executable_path = executable_path
        self.current_process: Optional[subprocess.Popen] = None
        self.status = RunnerStatus.IDLE
        self._lock = threading.Lock()

    @abstractmethod
    def _build_command(self, *args, **kwargs) -> List[str]:
        """Build the command to execute"""
        pass

    def _find_executable(self, name: str) -> Optional[str]:
        """Find executable in PATH or local directory"""
        from shutil import which

        if os.path.isabs(name) and os.path.exists(name):
            return name

        # Check script directory first
        import sys
        script_dir = Path(sys.argv[0]).parent
        local_exe = script_dir / (f"{name}.exe" if os.name == 'nt' else name)
        if local_exe.exists():
            return str(local_exe)

        return which(name)

    def is_available(self) -> bool:
        """Check if the executable is available"""
        return self._find_executable(self.executable_path) is not None

    def cancel(self) -> bool:
        """Cancel the current running process"""
        with self._lock:
            if self.current_process and self.status == RunnerStatus.RUNNING:
                try:
                    self.current_process.terminate()
                    self.current_process.wait(timeout=5)
                    self.status = RunnerStatus.CANCELLED
                    logger.info(f"{self.__class__.__name__}: Process cancelled")
                    return True
                except Exception as e:
                    logger.error(f"Failed to cancel process: {e}")
                    try:
                        self.current_process.kill()
                    except Exception:
                        pass
        return False

    def _run_process(
        self,
        command: List[str],
        timeout: Optional[int] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        env: Optional[Dict[str, str]] = None
    ) -> RunnerResult:
        """Execute a process with the given command"""
        import time
        start_time = time.time()

        with self._lock:
            self.status = RunnerStatus.RUNNING

        try:
            process_env = os.environ.copy()
            if env:
                process_env.update(env)

            logger.debug(f"Running command: {' '.join(command)}")

            self.current_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=process_env
            )

            stdout, stderr = self.current_process.communicate(timeout=timeout)
            duration = time.time() - start_time

            with self._lock:
                if self.current_process.returncode == 0:
                    self.status = RunnerStatus.COMPLETED
                    return RunnerResult(
                        success=True,
                        return_code=0,
                        stdout=stdout,
                        stderr=stderr,
                        duration_seconds=duration
                    )
                else:
                    self.status = RunnerStatus.FAILED
                    error_msg = self._parse_error(stderr)
                    return RunnerResult(
                        success=False,
                        return_code=self.current_process.returncode,
                        stdout=stdout,
                        stderr=stderr,
                        error_message=error_msg,
                        duration_seconds=duration
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
                duration_seconds=time.time() - start_time
            )

        except Exception as e:
            with self._lock:
                self.status = RunnerStatus.FAILED
            logger.exception(f"Process execution error: {e}")
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=str(e),
                duration_seconds=time.time() - start_time
            )

        finally:
            with self._lock:
                self.current_process = None

    @abstractmethod
    def _parse_error(self, stderr: str) -> str:
        """Parse stderr to extract human-readable error message"""
        pass


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
            r'frame=\s*(\d+).*?fps=\s*([\d.]+).*?time=(\d+:\d+:\d+\.\d+)'
        )
        self._duration_pattern = re.compile(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)')

    def _build_command(
        self,
        input_file: str,
        output_file: str,
        video_args: Optional[List[str]] = None,
        audio_args: Optional[List[str]] = None,
        extra_args: Optional[List[str]] = None,
        overwrite: bool = True
    ) -> List[str]:
        """Build FFmpeg command"""
        cmd = [self.executable_path, '-i', input_file]

        if video_args:
            cmd.extend(video_args)
        if audio_args:
            cmd.extend(audio_args)
        if extra_args:
            cmd.extend(extra_args)
        if overwrite:
            cmd.append('-y')

        cmd.append(output_file)
        return cmd

    def _parse_error(self, stderr: str) -> str:
        """Parse FFmpeg stderr to extract user-friendly error message"""
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

        # Extract the last error line as fallback
        lines = [l.strip() for l in stderr.split('\n') if l.strip()]
        for line in reversed(lines):
            if 'error' in line.lower() or 'failed' in line.lower():
                return line[:200]  # Limit length

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
        use_realtime_progress: bool = False
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
                error_message=f"Input file not found: {input_file}"
            )

        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        command = self._build_command(
            input_file, output_file,
            video_args, audio_args, extra_args
        )

        logger.info(f"FFmpeg: Converting {input_file} -> {output_file}")
        
        # Use real-time progress if requested and callback is provided
        if use_realtime_progress and progress_callback:
            result = self._run_with_realtime_progress(
                command, input_file, timeout, progress_callback
            )
        else:
            result = self._run_process(command, timeout, progress_callback)

        if result.success and os.path.exists(output_file):
            result.metadata['output_size'] = os.path.getsize(output_file)
            result.metadata['input_size'] = os.path.getsize(input_file)

        return result

    def run_raw(
        self,
        args: List[str],
        timeout: Optional[int] = None
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

    def probe(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Analyze media file using FFprobe.

        Args:
            file_path: Path to media file

        Returns:
            Dictionary with format and stream information, or None on error
        """
        if not os.path.exists(file_path):
            logger.error(f"FFprobe: File not found: {file_path}")
            return None

        cmd = [
            self.ffprobe_path,
            '-v', 'error',
            '-show_entries', 'format:stream',
            '-of', 'json',
            file_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"FFprobe error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("FFprobe timed out")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"FFprobe output parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"FFprobe error: {e}")
            return None

    def get_duration(self, file_path: str) -> Optional[float]:
        """Get media duration in seconds"""
        info = self.probe(file_path)
        if info and 'format' in info:
            try:
                return float(info['format'].get('duration', 0))
            except (ValueError, TypeError):
                pass
        return None

    def get_version(self) -> Optional[str]:
        """Get FFmpeg version string"""
        try:
            result = subprocess.run(
                [self.executable_path, '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.split('\n')[0]
        except Exception:
            pass
        return None

    def check_codec_support(self, codec: str) -> bool:
        """Check if a codec is supported"""
        try:
            result = subprocess.run(
                [self.executable_path, '-encoders'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return codec in result.stdout
        except Exception:
            return False

    def _run_with_realtime_progress(
        self,
        command: List[str],
        input_file: str,
        timeout: Optional[int] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
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
        
        # Get input duration for percentage calculation
        total_duration = self.get_duration(input_file) or 0
        
        # Add progress reporting to command
        progress_cmd = command[:-1]  # Remove output file
        progress_cmd.extend(['-progress', 'pipe:1', command[-1]])  # Add progress flag and output
        
        with self._lock:
            self.status = RunnerStatus.RUNNING
        
        try:
            process_env = os.environ.copy()
            logger.debug(f"Running FFmpeg with real-time progress: {' '.join(progress_cmd)}")
            
            self.current_process = subprocess.Popen(
                progress_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,  # Line buffered
                env=process_env
            )
            
            stderr_lines = []
            stderr_thread = threading.Thread(
                target=lambda: stderr_lines.extend(self.current_process.stderr.readlines()),
                daemon=True
            )
            stderr_thread.start()
            
            # Parse progress from stdout
            last_progress = 0
            for line in self.current_process.stdout:
                line = line.strip()
                
                # FFmpeg progress format: key=value pairs
                if line.startswith('out_time_ms='):
                    try:
                        # Extract microseconds
                        time_us = int(line.split('=')[1])
                        time_s = time_us / 1_000_000
                        
                        if total_duration > 0:
                            percent = int(min(100, (time_s / total_duration) * 100))
                            if percent != last_progress:
                                last_progress = percent
                                if progress_callback:
                                    progress_callback(percent, f"İşleniyor: {percent}%")
                    except (ValueError, IndexError):
                        pass
                
                elif line.startswith('progress='):
                    status = line.split('=')[1]
                    if status == 'end' and progress_callback:
                        progress_callback(100, "Tamamlandı")
                        
                # Check for timeout
                if timeout and (time.time() - start_time) > timeout:
                    raise subprocess.TimeoutExpired(progress_cmd, timeout)
            
            # Wait for process to complete
            self.current_process.wait()
            stderr_thread.join(timeout=5)
            
            duration = time.time() - start_time
            stderr = ''.join(stderr_lines)
            
            with self._lock:
                if self.current_process.returncode == 0:
                    self.status = RunnerStatus.COMPLETED
                    return RunnerResult(
                        success=True,
                        return_code=0,
                        stdout="",  # Progress output, not useful to save
                        stderr=stderr,
                        duration_seconds=duration
                    )
                else:
                    self.status = RunnerStatus.FAILED
                    error_msg = self._parse_error(stderr)
                    return RunnerResult(
                        success=False,
                        return_code=self.current_process.returncode,
                        stdout="",
                        stderr=stderr,
                        error_message=error_msg,
                        duration_seconds=duration
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
                duration_seconds=time.time() - start_time
            )
            
        except Exception as e:
            with self._lock:
                self.status = RunnerStatus.FAILED
            logger.exception(f"FFmpeg real-time progress error: {e}")
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=str(e),
                duration_seconds=time.time() - start_time
            )
            
        finally:
            with self._lock:
                self.current_process = None


class YtDlpRunner(BaseRunner):
    """
    Unified yt-dlp subprocess runner.
    Handles all media downloads with consistent error handling,
    progress reporting, and retry logic.
    """

    DEFAULT_RETRIES = 3
    DEFAULT_TIMEOUT = 3600  # 1 hour

    def __init__(self, ytdlp_path: str = "yt-dlp"):
        super().__init__(ytdlp_path)
        self._progress_pattern = re.compile(
            r'\[download\]\s+(\d+\.?\d*)%\s+of\s+~?(\d+\.?\d*\w+)'
        )

    def _build_command(
        self,
        url: str,
        output_template: str,
        format_spec: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> List[str]:
        """Build yt-dlp command"""
        cmd = [
            self.executable_path,
            '--no-warnings',
            '-o', output_template,
            '--newline',  # Progress on new lines for parsing
        ]

        if format_spec:
            cmd.extend(['-f', format_spec])

        if extra_args:
            cmd.extend(extra_args)

        cmd.append(url)
        return cmd

    def _parse_error(self, stderr: str) -> str:
        """Parse yt-dlp stderr to extract user-friendly error message"""
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

        lines = [l.strip() for l in stderr.split('\n') if l.strip()]
        for line in reversed(lines):
            if 'error' in line.lower():
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
        progress_callback: Optional[Callable[[int, str], None]] = None
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

        last_result = None
        for attempt in range(1, retries + 1):
            logger.info(f"yt-dlp: Download attempt {attempt}/{retries} for {url}")

            result = self._run_process(
                command,
                timeout or self.DEFAULT_TIMEOUT,
                progress_callback
            )

            if result.success:
                # Extract downloaded filename from output
                downloaded_files = self._extract_downloaded_files(result.stdout)
                result.metadata['downloaded_files'] = downloaded_files
                return result

            last_result = result

            # Don't retry on certain errors
            if any(err in result.error_message.lower() for err in
                   ['unavailable', 'private', 'not found', 'invalid url']):
                break

            if attempt < retries:
                import time
                wait_time = attempt * 2  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

        return last_result or RunnerResult(
            success=False,
            return_code=-1,
            error_message="All download attempts failed"
        )

    def _extract_downloaded_files(self, stdout: str) -> List[str]:
        """Extract list of downloaded files from yt-dlp output"""
        files = []
        patterns = [
            r'\[download\] Destination: (.+)',
            r'\[Merger\] Merging formats into "(.+)"',
            r'\[ExtractAudio\] Destination: (.+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, stdout)
            files.extend(matches)

        return list(set(files))  # Remove duplicates

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
            '--dump-json',
            '--no-warnings',
            '--no-download',
            url
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"yt-dlp info extraction failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("yt-dlp info extraction timed out")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"yt-dlp output parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            return None

    @staticmethod
    def _resolve_playlist_entry_url(entry: Dict[str, Any], playlist_url: str) -> Optional[str]:
        """Resolve playlist entry URL to a downloadable HTTP URL."""
        direct_url = entry.get('webpage_url') or entry.get('url') or entry.get('original_url')
        if isinstance(direct_url, str) and direct_url.startswith(('http://', 'https://')):
            return direct_url

        playlist_lower = playlist_url.lower()
        candidate_id = direct_url if isinstance(direct_url, str) and direct_url else entry.get('id')
        if isinstance(candidate_id, str) and candidate_id and 'youtube.com' in playlist_lower:
            return f"https://www.youtube.com/watch?v={candidate_id}"

        return None

    def extract_playlist_entries(self, url: str, timeout: int = 120) -> List[Dict[str, Any]]:
        """
        Extract playlist entries without downloading media files.

        Returns:
            Normalized entry list with keys: title, url, duration, uploader.
        """
        cmd = [
            self.executable_path,
            '--dump-single-json',
            '--flat-playlist',
            '--no-warnings',
            '--skip-download',
            url
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp playlist extraction timed out")
            return []
        except Exception as e:
            logger.error(f"yt-dlp playlist extraction error: {e}")
            return []

        if result.returncode != 0:
            logger.error(f"yt-dlp playlist extraction failed: {result.stderr}")
            return []

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"yt-dlp playlist JSON parse error: {e}")
            return []

        entries = payload.get('entries')
        if not isinstance(entries, list):
            return []

        playlist_url = str(payload.get('webpage_url') or url)
        normalized_entries: List[Dict[str, Any]] = []
        for item in entries:
            if not isinstance(item, dict):
                continue

            entry_url = self._resolve_playlist_entry_url(item, playlist_url)
            if not entry_url:
                continue

            normalized_entries.append({
                'title': item.get('title') or item.get('id') or 'Unknown',
                'url': entry_url,
                'duration': item.get('duration', 0),
                'uploader': item.get('uploader') or item.get('channel') or '',
            })

        return normalized_entries

    def list_formats(self, url: str) -> Optional[List[Dict[str, Any]]]:
        """
        List available formats for a URL.

        Args:
            url: Media URL

        Returns:
            List of format dictionaries, or None on error
        """
        info = self.extract_info(url)
        if info and 'formats' in info:
            return info['formats']
        return None

    def get_version(self) -> Optional[str]:
        """Get yt-dlp version string"""
        try:
            result = subprocess.run(
                [self.executable_path, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def update(self, timeout: int = 300) -> bool:
        """
        Update yt-dlp to latest version.

        Args:
            timeout: Update timeout in seconds

        Returns:
            True if update successful
        """
        try:
            result = subprocess.run(
                [self.executable_path, '-U'],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"yt-dlp update failed: {e}")
            return False


# Convenience factory functions
def get_ffmpeg_runner(
    ffmpeg_path: str = "ffmpeg",
    ffprobe_path: str = "ffprobe"
) -> FFmpegRunner:
    """Create and return an FFmpegRunner instance"""
    return FFmpegRunner(ffmpeg_path, ffprobe_path)


def get_ytdlp_runner(ytdlp_path: str = "yt-dlp") -> YtDlpRunner:
    """Create and return a YtDlpRunner instance"""
    return YtDlpRunner(ytdlp_path)
