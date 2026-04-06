"""
RAVN - Media utility helpers using FFmpegRunner.

This module provides high-level utility functions for common media operations.
All operations use FFmpegRunner for consistent error handling and progress reporting.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ravn_app.core.runners.ffmpeg import FFmpegRunner
from ravn_app.core.runners.base import RunnerResult, RunnerStatus


logger = logging.getLogger(__name__)


class MediaHelpers:
    """High-level media utility operations using FFmpegRunner."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """Initialize with FFmpeg paths."""
        self.runner = FFmpegRunner(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)

    # =============================================================================
    # QUICK HELPERS (UTL-02)
    # =============================================================================

    def remux(
        self,
        input_file: str,
        output_file: str,
        container_format: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Remux (change container format without re-encoding).

        Fast operation that only changes the container, preserving all streams.

        Args:
            input_file: Input media file path
            output_file: Output file path (extension determines container)
            container_format: Optional container format override (mp4, mkv, webm, etc.)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> helpers = MediaHelpers()
            >>> result = helpers.remux("input.mkv", "output.mp4")
            >>> print(f"Success: {result.success}, Output: {result.metadata['output_file']}")
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        # Remux uses -c copy for all streams (no re-encoding)
        video_args = ["-c:v", "copy"]
        audio_args = ["-c:a", "copy"]
        extra_args = []

        if container_format:
            extra_args.extend(["-f", container_format])

        logger.info(f"Remuxing {input_file} -> {output_file}")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            extra_args=extra_args,
            progress_callback=progress_callback,
        )

        if result.success:
            result.metadata["operation"] = "remux"
            result.metadata["output_file"] = output_file

        return result

    def extract_audio(
        self,
        input_file: str,
        output_file: str,
        audio_codec: str = "copy",
        audio_bitrate: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Extract audio track from media file.

        Args:
            input_file: Input media file path
            output_file: Output audio file path (e.g., .mp3, .m4a, .flac)
            audio_codec: Audio codec ('copy' for no re-encoding, 'aac', 'mp3', 'opus', 'flac')
            audio_bitrate: Optional audio bitrate (e.g., '192k', '320k')
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.extract_audio("video.mp4", "audio.mp3", audio_codec="mp3", audio_bitrate="192k")
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        # No video stream
        video_args = ["-vn"]

        # Audio encoding
        audio_args = ["-c:a", audio_codec]
        if audio_bitrate and audio_codec != "copy":
            audio_args.extend(["-b:a", audio_bitrate])

        logger.info(f"Extracting audio from {input_file} -> {output_file}")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
        )

        if result.success:
            result.metadata["operation"] = "extract_audio"
            result.metadata["output_file"] = output_file
            result.metadata["audio_codec"] = audio_codec

        return result

    def mute(
        self,
        input_file: str,
        output_file: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Remove audio track from media file.

        Args:
            input_file: Input media file path
            output_file: Output file path (same container as input)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.mute("video.mp4", "video_muted.mp4")
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        # Copy video, remove audio
        video_args = ["-c:v", "copy"]
        audio_args = ["-an"]  # No audio

        logger.info(f"Muting {input_file} -> {output_file}")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
        )

        if result.success:
            result.metadata["operation"] = "mute"
            result.metadata["output_file"] = output_file

        return result

    def trim(
        self,
        input_file: str,
        output_file: str,
        start_time: float,
        end_time: Optional[float] = None,
        duration: Optional[float] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Trim media file to specific time range.

        Args:
            input_file: Input media file path
            output_file: Output file path
            start_time: Start time in seconds
            end_time: End time in seconds (mutually exclusive with duration)
            duration: Duration in seconds from start_time (mutually exclusive with end_time)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.trim("video.mp4", "clip.mp4", start_time=10.5, end_time=30.0)
            >>> result = helpers.trim("video.mp4", "clip.mp4", start_time=10.5, duration=19.5)
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        if end_time is not None and duration is not None:
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message="Cannot specify both end_time and duration",
            )

        # Build trim arguments
        extra_args = ["-ss", str(start_time)]

        if duration is not None:
            extra_args.extend(["-t", str(duration)])
        elif end_time is not None:
            calculated_duration = end_time - start_time
            extra_args.extend(["-t", str(calculated_duration)])

        # Copy streams for fast trim
        video_args = ["-c:v", "copy"]
        audio_args = ["-c:a", "copy"]

        logger.info(f"Trimming {input_file} -> {output_file} (start={start_time}, duration={duration or (end_time - start_time if end_time else 'end')})")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            extra_args=extra_args,
            progress_callback=progress_callback,
        )

        if result.success:
            result.metadata["operation"] = "trim"
            result.metadata["output_file"] = output_file
            result.metadata["start_time"] = start_time
            result.metadata["duration"] = duration or (end_time - start_time if end_time else None)

        return result

    def preview_clip(
        self,
        input_file: str,
        output_file: str,
        duration: float = 10.0,
        start_time: float = 0.0,
        scale: Optional[str] = "640:-2",
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Generate a small preview clip from media file.

        Args:
            input_file: Input media file path
            output_file: Output preview file path
            duration: Preview duration in seconds (default: 10s)
            start_time: Start time in seconds (default: 0s)
            scale: Video scale (default: 640:-2 for 640px width, auto height)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.preview_clip("movie.mp4", "preview.mp4", duration=15, start_time=60)
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        extra_args = ["-ss", str(start_time), "-t", str(duration)]

        # Scale down for preview
        video_args = ["-vf", f"scale={scale}", "-c:v", "libx264", "-preset", "fast", "-crf", "28"]
        audio_args = ["-c:a", "aac", "-b:a", "96k"]

        logger.info(f"Creating preview clip from {input_file} -> {output_file} (duration={duration}s)")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            extra_args=extra_args,
            progress_callback=progress_callback,
        )

        if result.success:
            result.metadata["operation"] = "preview_clip"
            result.metadata["output_file"] = output_file
            result.metadata["duration"] = duration
            result.metadata["start_time"] = start_time

        return result

    def thumbnail(
        self,
        input_file: str,
        output_file: str,
        timestamp: float = 1.0,
        width: Optional[int] = None,
        height: Optional[int] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Extract a single frame as thumbnail from media file.

        Args:
            input_file: Input media file path
            output_file: Output image file path (.jpg, .png, .webp)
            timestamp: Timestamp in seconds for frame extraction (default: 1s)
            width: Optional thumbnail width (maintains aspect ratio if height not specified)
            height: Optional thumbnail height (maintains aspect ratio if width not specified)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.thumbnail("video.mp4", "thumb.jpg", timestamp=30, width=640)
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        extra_args = ["-ss", str(timestamp), "-frames:v", "1"]

        # Build scale filter if dimensions specified
        video_args = []
        if width or height:
            scale_w = str(width) if width else "-2"
            scale_h = str(height) if height else "-2"
            video_args = ["-vf", f"scale={scale_w}:{scale_h}"]

        logger.info(f"Extracting thumbnail from {input_file} -> {output_file} (timestamp={timestamp}s)")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=["-an"],  # No audio for image
            extra_args=extra_args,
            progress_callback=progress_callback,
        )

        if result.success:
            result.metadata["operation"] = "thumbnail"
            result.metadata["output_file"] = output_file
            result.metadata["timestamp"] = timestamp

        return result

    # =============================================================================
    # AUDIO UTILITY OPERATIONS (UTL-03)
    # =============================================================================

    def adjust_volume(
        self,
        input_file: str,
        output_file: str,
        volume_db: float,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Adjust audio volume level.

        Args:
            input_file: Input media file path
            output_file: Output file path
            volume_db: Volume adjustment in decibels (positive to increase, negative to decrease)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.adjust_volume("audio.mp3", "louder.mp3", volume_db=5.0)  # +5dB
            >>> result = helpers.adjust_volume("audio.mp3", "quieter.mp3", volume_db=-10.0)  # -10dB
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        # Use volume filter
        video_args = ["-c:v", "copy"]
        audio_args = ["-af", f"volume={volume_db}dB", "-c:a", "aac"]

        logger.info(f"Adjusting volume {input_file} -> {output_file} ({volume_db}dB)")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
        )

        if result.success:
            result.metadata["operation"] = "adjust_volume"
            result.metadata["output_file"] = output_file
            result.metadata["volume_db"] = volume_db

        return result

    def fade_audio(
        self,
        input_file: str,
        output_file: str,
        fade_in_duration: float = 0.0,
        fade_out_duration: float = 0.0,
        fade_out_start: Optional[float] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Apply fade in/out effects to audio.

        Args:
            input_file: Input media file path
            output_file: Output file path
            fade_in_duration: Fade in duration in seconds (0 = no fade in)
            fade_out_duration: Fade out duration in seconds (0 = no fade out)
            fade_out_start: Fade out start time in seconds (None = auto-detect from duration)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.fade_audio("audio.mp3", "faded.mp3", fade_in_duration=2.0, fade_out_duration=3.0)
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        # Build fade filter
        filters = []
        if fade_in_duration > 0:
            filters.append(f"afade=t=in:st=0:d={fade_in_duration}")

        if fade_out_duration > 0:
            if fade_out_start is None:
                # Auto-detect from duration (requires probe)
                filters.append(f"afade=t=out:d={fade_out_duration}")
            else:
                filters.append(f"afade=t=out:st={fade_out_start}:d={fade_out_duration}")

        if not filters:
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message="At least one of fade_in_duration or fade_out_duration must be > 0",
            )

        filter_str = ",".join(filters)
        video_args = ["-c:v", "copy"]
        audio_args = ["-af", filter_str, "-c:a", "aac"]

        logger.info(f"Applying fade to {input_file} -> {output_file} (in={fade_in_duration}s, out={fade_out_duration}s)")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
        )

        if result.success:
            result.metadata["operation"] = "fade_audio"
            result.metadata["output_file"] = output_file
            result.metadata["fade_in_duration"] = fade_in_duration
            result.metadata["fade_out_duration"] = fade_out_duration

        return result

    def convert_audio_bitrate(
        self,
        input_file: str,
        output_file: str,
        audio_bitrate: str = "192k",
        sample_rate: Optional[int] = None,
        audio_codec: str = "aac",
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Convert audio bitrate and/or sample rate.

        Args:
            input_file: Input media file path
            output_file: Output file path
            audio_bitrate: Target audio bitrate (e.g., '128k', '192k', '320k')
            sample_rate: Optional sample rate in Hz (e.g., 44100, 48000)
            audio_codec: Audio codec (default: 'aac')
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.convert_audio_bitrate("audio.mp3", "audio_192k.mp3", audio_bitrate="192k", sample_rate=44100)
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        video_args = ["-c:v", "copy"]
        audio_args = ["-c:a", audio_codec, "-b:a", audio_bitrate]

        if sample_rate:
            audio_args.extend(["-ar", str(sample_rate)])

        logger.info(f"Converting audio bitrate {input_file} -> {output_file} (bitrate={audio_bitrate}, sample_rate={sample_rate})")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
        )

        if result.success:
            result.metadata["operation"] = "convert_audio_bitrate"
            result.metadata["output_file"] = output_file
            result.metadata["audio_bitrate"] = audio_bitrate
            result.metadata["sample_rate"] = sample_rate

        return result

    def convert_channels(
        self,
        input_file: str,
        output_file: str,
        channels: int,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Convert audio channels (stereo/mono conversion).

        Args:
            input_file: Input media file path
            output_file: Output file path
            channels: Target channel count (1 = mono, 2 = stereo)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.convert_channels("stereo.mp3", "mono.mp3", channels=1)
            >>> result = helpers.convert_channels("mono.mp3", "stereo.mp3", channels=2)
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        if channels not in (1, 2):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Invalid channel count: {channels} (must be 1 or 2)",
            )

        video_args = ["-c:v", "copy"]
        audio_args = ["-ac", str(channels), "-c:a", "aac"]

        logger.info(f"Converting channels {input_file} -> {output_file} (channels={channels})")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
        )

        if result.success:
            result.metadata["operation"] = "convert_channels"
            result.metadata["output_file"] = output_file
            result.metadata["channels"] = channels

        return result

    def detect_silence(
        self,
        input_file: str,
        noise_threshold_db: float = -50.0,
        min_duration: float = 0.5,
    ) -> RunnerResult:
        """
        Detect silent sections in audio.

        Args:
            input_file: Input media file path
            noise_threshold_db: Silence threshold in dB (default: -50dB)
            min_duration: Minimum silence duration in seconds (default: 0.5s)

        Returns:
            RunnerResult with silence detection results in metadata["silence_periods"]

        Example:
            >>> result = helpers.detect_silence("audio.mp3", noise_threshold_db=-40, min_duration=1.0)
            >>> print(result.metadata["silence_periods"])  # List of (start, end, duration) tuples
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        logger.info(f"Detecting silence in {input_file} (threshold={noise_threshold_db}dB, min_duration={min_duration}s)")

        try:
            result = self.runner.run_raw(
                [
                    "-i", input_file,
                    "-af", f"silencedetect=n={noise_threshold_db}dB:d={min_duration}",
                    "-f", "null",
                    "-",
                ],
                timeout=300,
            )
            stderr = result.stderr

            # Parse silence detection output
            import re
            silence_start_pattern = re.compile(r"silence_start: ([\d.]+)")
            silence_end_pattern = re.compile(r"silence_end: ([\d.]+)")
            silence_duration_pattern = re.compile(r"silence_duration: ([\d.]+)")

            silence_periods = []
            current_start = None

            for line in stderr.split("\n"):
                start_match = silence_start_pattern.search(line)
                if start_match:
                    current_start = float(start_match.group(1))

                end_match = silence_end_pattern.search(line)
                duration_match = silence_duration_pattern.search(line)
                if end_match and duration_match and current_start is not None:
                    end_time = float(end_match.group(1))
                    duration = float(duration_match.group(1))
                    silence_periods.append((current_start, end_time, duration))
                    current_start = None

            result.metadata["operation"] = "detect_silence"
            result.metadata["silence_periods"] = silence_periods
            result.metadata["threshold_db"] = noise_threshold_db
            result.metadata["min_duration"] = min_duration

            return result

        except Exception as e:
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Silence detection failed: {str(e)}",
            )

    def loudness_normalize(
        self,
        input_file: str,
        output_file: str,
        target_loudness: float = -16.0,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Normalize audio loudness to EBU R128 standard.

        Args:
            input_file: Input media file path
            output_file: Output file path
            target_loudness: Target integrated loudness in LUFS (default: -16.0 for streaming)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.loudness_normalize("audio.mp3", "normalized.mp3", target_loudness=-16.0)
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        # Use loudnorm filter
        video_args = ["-c:v", "copy"]
        audio_args = ["-af", f"loudnorm=I={target_loudness}:TP=-1.5:LRA=11", "-c:a", "aac"]

        logger.info(f"Normalizing loudness {input_file} -> {output_file} (target={target_loudness} LUFS)")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
        )

        if result.success:
            result.metadata["operation"] = "loudness_normalize"
            result.metadata["output_file"] = output_file
            result.metadata["target_loudness"] = target_loudness

        return result

    # =============================================================================
    # VIDEO UTILITY OPERATIONS (UTL-04)
    # =============================================================================

    def scale_video(
        self,
        input_file: str,
        output_file: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        maintain_aspect: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Scale video resolution.

        Args:
            input_file: Input video file path
            output_file: Output file path
            width: Target width (None = auto from height)
            height: Target height (None = auto from width)
            maintain_aspect: Maintain aspect ratio (default: True, uses -2 for auto dimension)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.scale_video("video.mp4", "scaled.mp4", width=1280, height=720)
            >>> result = helpers.scale_video("video.mp4", "scaled.mp4", width=640)  # Auto height
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        if not width and not height:
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message="At least one of width or height must be specified",
            )

        # Build scale filter
        if maintain_aspect:
            scale_w = str(width) if width else "-2"
            scale_h = str(height) if height else "-2"
        else:
            scale_w = str(width) if width else "iw"
            scale_h = str(height) if height else "ih"

        video_args = ["-vf", f"scale={scale_w}:{scale_h}", "-c:v", "libx264", "-preset", "medium", "-crf", "23"]
        audio_args = ["-c:a", "copy"]

        logger.info(f"Scaling video {input_file} -> {output_file} ({scale_w}x{scale_h})")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
            use_realtime_progress=True,
        )

        if result.success:
            result.metadata["operation"] = "scale_video"
            result.metadata["output_file"] = output_file
            result.metadata["width"] = width
            result.metadata["height"] = height

        return result

    def crop_video(
        self,
        input_file: str,
        output_file: str,
        width: int,
        height: int,
        x: int = 0,
        y: int = 0,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Crop video to specific area.

        Args:
            input_file: Input video file path
            output_file: Output file path
            width: Crop width
            height: Crop height
            x: Crop X offset (default: 0)
            y: Crop Y offset (default: 0)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.crop_video("video.mp4", "cropped.mp4", width=1280, height=720, x=100, y=50)
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        video_args = ["-vf", f"crop={width}:{height}:{x}:{y}", "-c:v", "libx264", "-preset", "medium", "-crf", "23"]
        audio_args = ["-c:a", "copy"]

        logger.info(f"Cropping video {input_file} -> {output_file} ({width}x{height} at {x},{y})")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
            use_realtime_progress=True,
        )

        if result.success:
            result.metadata["operation"] = "crop_video"
            result.metadata["output_file"] = output_file
            result.metadata["crop_area"] = f"{width}x{height} at ({x},{y})"

        return result

    def pad_video(
        self,
        input_file: str,
        output_file: str,
        width: int,
        height: int,
        x: str = "(ow-iw)/2",
        y: str = "(oh-ih)/2",
        color: str = "black",
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Add padding (letterbox/pillarbox) to video.

        Args:
            input_file: Input video file path
            output_file: Output file path
            width: Output width
            height: Output height
            x: Horizontal position expression (default: centered)
            y: Vertical position expression (default: centered)
            color: Padding color (default: 'black')
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.pad_video("video.mp4", "padded.mp4", width=1920, height=1080, color="black")
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        video_args = ["-vf", f"pad={width}:{height}:{x}:{y}:color={color}", "-c:v", "libx264", "-preset", "medium", "-crf", "23"]
        audio_args = ["-c:a", "copy"]

        logger.info(f"Padding video {input_file} -> {output_file} (to {width}x{height}, color={color})")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
            use_realtime_progress=True,
        )

        if result.success:
            result.metadata["operation"] = "pad_video"
            result.metadata["output_file"] = output_file
            result.metadata["padded_size"] = f"{width}x{height}"

        return result

    def rotate_video(
        self,
        input_file: str,
        output_file: str,
        rotation: int,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Rotate video by 90, 180, or 270 degrees.

        Args:
            input_file: Input video file path
            output_file: Output file path
            rotation: Rotation angle (90, 180, or 270 degrees clockwise)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.rotate_video("video.mp4", "rotated.mp4", rotation=90)
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        # Map rotation to transpose values
        rotation_map = {
            90: "1",      # clock=1
            180: "2,transpose=2",  # transpose twice
            270: "2",     # cclock=2
        }

        if rotation not in rotation_map:
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Invalid rotation: {rotation} (must be 90, 180, or 270)",
            )

        video_args = ["-vf", f"transpose={rotation_map[rotation]}", "-c:v", "libx264", "-preset", "medium", "-crf", "23"]
        audio_args = ["-c:a", "copy"]

        logger.info(f"Rotating video {input_file} -> {output_file} ({rotation} degrees)")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
            use_realtime_progress=True,
        )

        if result.success:
            result.metadata["operation"] = "rotate_video"
            result.metadata["output_file"] = output_file
            result.metadata["rotation"] = rotation

        return result

    def change_fps(
        self,
        input_file: str,
        output_file: str,
        fps: int,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Change video frame rate.

        Args:
            input_file: Input video file path
            output_file: Output file path
            fps: Target frame rate (e.g., 24, 30, 60)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.change_fps("video.mp4", "video_60fps.mp4", fps=60)
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        video_args = ["-vf", f"fps={fps}", "-c:v", "libx264", "-preset", "medium", "-crf", "23"]
        audio_args = ["-c:a", "copy"]

        logger.info(f"Changing FPS {input_file} -> {output_file} (to {fps} fps)")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
            use_realtime_progress=True,
        )

        if result.success:
            result.metadata["operation"] = "change_fps"
            result.metadata["output_file"] = output_file
            result.metadata["fps"] = fps

        return result

    def adjust_color(
        self,
        input_file: str,
        output_file: str,
        brightness: float = 0.0,
        contrast: float = 1.0,
        saturation: float = 1.0,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Adjust video brightness, contrast, and saturation.

        Args:
            input_file: Input video file path
            output_file: Output file path
            brightness: Brightness adjustment (-1.0 to 1.0, default: 0)
            contrast: Contrast multiplier (0.0 to 2.0, default: 1.0)
            saturation: Saturation multiplier (0.0 to 3.0, default: 1.0)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.adjust_color("video.mp4", "adjusted.mp4", brightness=0.1, contrast=1.2, saturation=1.5)
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        # Use eq filter for brightness/contrast and hue filter for saturation
        filters = []
        if brightness != 0.0 or contrast != 1.0:
            filters.append(f"eq=brightness={brightness}:contrast={contrast}")
        if saturation != 1.0:
            filters.append(f"hue=s={saturation}")

        if not filters:
            # No adjustment needed, just copy
            filters.append("copy")

        filter_str = ",".join(filters)
        video_args = ["-vf", filter_str, "-c:v", "libx264", "-preset", "medium", "-crf", "23"]
        audio_args = ["-c:a", "copy"]

        logger.info(f"Adjusting color {input_file} -> {output_file} (brightness={brightness}, contrast={contrast}, saturation={saturation})")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
            use_realtime_progress=True,
        )

        if result.success:
            result.metadata["operation"] = "adjust_color"
            result.metadata["output_file"] = output_file
            result.metadata["brightness"] = brightness
            result.metadata["contrast"] = contrast
            result.metadata["saturation"] = saturation

        return result

    def blur_sharpen(
        self,
        input_file: str,
        output_file: str,
        blur_amount: float = 0.0,
        sharpen_amount: float = 0.0,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Apply blur or sharpen filter to video.

        Args:
            input_file: Input video file path
            output_file: Output file path
            blur_amount: Blur amount (0.0 = none, 1.0 = light, 5.0 = heavy)
            sharpen_amount: Sharpen amount (0.0 = none, 1.0 = light, 5.0 = heavy)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Note: Only one of blur_amount or sharpen_amount should be > 0

        Example:
            >>> result = helpers.blur_sharpen("video.mp4", "blurred.mp4", blur_amount=2.0)
            >>> result = helpers.blur_sharpen("video.mp4", "sharpened.mp4", sharpen_amount=1.5)
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        filters = []
        if blur_amount > 0:
            filters.append(f"boxblur={blur_amount}:{blur_amount}")
        if sharpen_amount > 0:
            filters.append(f"unsharp=5:5:{sharpen_amount}:5:5:0.0")

        if not filters:
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message="At least one of blur_amount or sharpen_amount must be > 0",
            )

        filter_str = ",".join(filters)
        video_args = ["-vf", filter_str, "-c:v", "libx264", "-preset", "medium", "-crf", "23"]
        audio_args = ["-c:a", "copy"]

        logger.info(f"Applying blur/sharpen {input_file} -> {output_file} (blur={blur_amount}, sharpen={sharpen_amount})")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
            use_realtime_progress=True,
        )

        if result.success:
            result.metadata["operation"] = "blur_sharpen"
            result.metadata["output_file"] = output_file
            result.metadata["blur_amount"] = blur_amount
            result.metadata["sharpen_amount"] = sharpen_amount

        return result

    def deinterlace(
        self,
        input_file: str,
        output_file: str,
        method: str = "yadif",
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Deinterlace interlaced video.

        Args:
            input_file: Input video file path
            output_file: Output file path
            method: Deinterlacing method ('yadif' = adaptive, 'bwdif' = motion adaptive)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with success status and metadata

        Example:
            >>> result = helpers.deinterlace("interlaced.mp4", "progressive.mp4", method="yadif")
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        if method not in ("yadif", "bwdif"):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Invalid deinterlace method: {method} (must be 'yadif' or 'bwdif')",
            )

        video_args = ["-vf", f"{method}=0:-1:0", "-c:v", "libx264", "-preset", "medium", "-crf", "23"]
        audio_args = ["-c:a", "copy"]

        logger.info(f"Deinterlacing {input_file} -> {output_file} (method={method})")
        result = self.runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=video_args,
            audio_args=audio_args,
            progress_callback=progress_callback,
            use_realtime_progress=True,
        )

        if result.success:
            result.metadata["operation"] = "deinterlace"
            result.metadata["output_file"] = output_file
            result.metadata["method"] = method

        return result

    # =============================================================================
    # SMART HELPERS (UTL-05)
    # =============================================================================

    def detect_black_frames(
        self,
        input_file: str,
        black_threshold: float = 0.10,
        black_duration_min: float = 0.5,
    ) -> RunnerResult:
        """
        Detect black frames and scene boundaries in video.

        Args:
            input_file: Input video file path
            black_threshold: Threshold for what constitutes "black" (0.0-1.0, default: 0.10)
            black_duration_min: Minimum black frame duration in seconds (default: 0.5s)

        Returns:
            RunnerResult with black frame periods in metadata["black_periods"]

        Example:
            >>> result = helpers.detect_black_frames("video.mp4", black_threshold=0.1, black_duration_min=1.0)
            >>> print(result.metadata["black_periods"])  # List of (start, end, duration) tuples
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        logger.info(f"Detecting black frames in {input_file} (threshold={black_threshold}, min_duration={black_duration_min}s)")

        import re
        try:
            result = self.runner.run_raw(
                [
                    "-i", input_file,
                    "-vf", f"blackdetect=d={black_duration_min}:pix_th={black_threshold}",
                    "-f", "null",
                    "-",
                ],
                timeout=600,
            )
            stderr = result.stderr

            # Parse blackdetect output
            black_start_pattern = re.compile(r"black_start:([\d.]+)")
            black_end_pattern = re.compile(r"black_end:([\d.]+)")
            black_duration_pattern = re.compile(r"black_duration:([\d.]+)")

            black_periods = []
            current_start = None

            for line in stderr.split("\n"):
                start_match = black_start_pattern.search(line)
                if start_match:
                    current_start = float(start_match.group(1))

                end_match = black_end_pattern.search(line)
                duration_match = black_duration_pattern.search(line)
                if end_match and duration_match and current_start is not None:
                    end_time = float(end_match.group(1))
                    duration = float(duration_match.group(1))
                    black_periods.append((current_start, end_time, duration))
                    current_start = None

            result.metadata["operation"] = "detect_black_frames"
            result.metadata["black_periods"] = black_periods
            result.metadata["threshold"] = black_threshold
            result.metadata["min_duration"] = black_duration_min

            return result

        except Exception as e:
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Black frame detection failed: {str(e)}",
            )

    def generate_scene_previews(
        self,
        input_file: str,
        output_dir: str,
        scene_count: int = 10,
        preview_duration: float = 3.0,
        scale: str = "640:-2",
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Generate preview clips from detected scenes.

        Args:
            input_file: Input video file path
            output_dir: Output directory for preview clips
            scene_count: Number of scenes to extract (default: 10)
            preview_duration: Duration of each preview clip in seconds (default: 3s)
            scale: Video scale for previews (default: 640:-2)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with generated preview files in metadata["preview_files"]

        Example:
            >>> result = helpers.generate_scene_previews("movie.mp4", "previews/", scene_count=10, preview_duration=5.0)
            >>> print(result.metadata["preview_files"])  # List of generated preview file paths
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        os.makedirs(output_dir, exist_ok=True)

        logger.info(f"Detecting scenes in {input_file}")

        import re
        try:
            detection_result = self.runner.run_raw(
                [
                    "-i", input_file,
                    "-vf", "select='gt(scene,0.3)',showinfo",
                    "-f", "null",
                    "-",
                ],
                timeout=600,
            )
            stderr = detection_result.stderr

            # Parse scene timestamps from showinfo output
            pts_time_pattern = re.compile(r"pts_time:([\d.]+)")
            scene_times = []

            for line in stderr.split("\n"):
                if "showinfo" in line:
                    match = pts_time_pattern.search(line)
                    if match:
                        scene_times.append(float(match.group(1)))

            if not scene_times:
                return RunnerResult(
                    success=False,
                    return_code=-1,
                    error_message="No scenes detected in video",
                )

            # Limit to requested scene count
            scene_times = scene_times[:scene_count]

            # Generate preview clips for each scene
            preview_files = []
            input_stem = Path(input_file).stem

            for idx, start_time in enumerate(scene_times):
                output_file = os.path.join(output_dir, f"{input_stem}_scene_{idx+1:03d}.mp4")

                # Generate preview clip
                extra_args = ["-ss", str(start_time), "-t", str(preview_duration)]
                video_args = ["-vf", f"scale={scale}", "-c:v", "libx264", "-preset", "fast", "-crf", "28"]
                audio_args = ["-c:a", "aac", "-b:a", "96k"]

                clip_result = self.runner.run(
                    input_file=input_file,
                    output_file=output_file,
                    video_args=video_args,
                    audio_args=audio_args,
                    extra_args=extra_args,
                )

                if clip_result.success:
                    preview_files.append(output_file)

                if progress_callback:
                    progress_percent = int(((idx + 1) / len(scene_times)) * 100)
                    progress_callback(progress_percent, f"Generating preview {idx+1}/{len(scene_times)}")

            result = RunnerResult(
                success=True,
                return_code=0,
                stdout=f"Generated {len(preview_files)} preview clips",
                stderr="",
            )
            result.metadata["operation"] = "generate_scene_previews"
            result.metadata["preview_files"] = preview_files
            result.metadata["scene_count"] = len(preview_files)

            return result

        except Exception as e:
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Scene preview generation failed: {str(e)}",
            )

    def generate_scene_thumbnails(
        self,
        input_file: str,
        output_dir: str,
        scene_count: int = 10,
        thumbnail_width: int = 640,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> RunnerResult:
        """
        Generate representative thumbnails from detected scenes.

        Args:
            input_file: Input video file path
            output_dir: Output directory for thumbnails
            scene_count: Number of scene thumbnails to extract (default: 10)
            thumbnail_width: Thumbnail width in pixels (default: 640)
            progress_callback: Optional progress callback (percent, status_text)

        Returns:
            RunnerResult with generated thumbnail files in metadata["thumbnail_files"]

        Example:
            >>> result = helpers.generate_scene_thumbnails("movie.mp4", "thumbs/", scene_count=20, thumbnail_width=800)
            >>> print(result.metadata["thumbnail_files"])  # List of generated thumbnail file paths
        """
        if not os.path.exists(input_file):
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Input file not found: {input_file}",
            )

        os.makedirs(output_dir, exist_ok=True)

        logger.info(f"Detecting scenes in {input_file} for thumbnail generation")

        import re
        try:
            detection_result = self.runner.run_raw(
                [
                    "-i", input_file,
                    "-vf", "select='gt(scene,0.3)',showinfo",
                    "-f", "null",
                    "-",
                ],
                timeout=600,
            )
            stderr = detection_result.stderr

            # Parse scene timestamps
            pts_time_pattern = re.compile(r"pts_time:([\d.]+)")
            scene_times = []

            for line in stderr.split("\n"):
                if "showinfo" in line:
                    match = pts_time_pattern.search(line)
                    if match:
                        scene_times.append(float(match.group(1)))

            if not scene_times:
                return RunnerResult(
                    success=False,
                    return_code=-1,
                    error_message="No scenes detected in video",
                )

            # Limit to requested scene count
            scene_times = scene_times[:scene_count]

            # Generate thumbnails for each scene
            thumbnail_files = []
            input_stem = Path(input_file).stem

            for idx, timestamp in enumerate(scene_times):
                output_file = os.path.join(output_dir, f"{input_stem}_thumb_{idx+1:03d}.jpg")

                # Extract frame as thumbnail
                thumb_result = self.thumbnail(
                    input_file=input_file,
                    output_file=output_file,
                    timestamp=timestamp,
                    width=thumbnail_width,
                )

                if thumb_result.success:
                    thumbnail_files.append(output_file)

                if progress_callback:
                    progress_percent = int(((idx + 1) / len(scene_times)) * 100)
                    progress_callback(progress_percent, f"Generating thumbnail {idx+1}/{len(scene_times)}")

            result = RunnerResult(
                success=True,
                return_code=0,
                stdout=f"Generated {len(thumbnail_files)} scene thumbnails",
                stderr="",
            )
            result.metadata["operation"] = "generate_scene_thumbnails"
            result.metadata["thumbnail_files"] = thumbnail_files
            result.metadata["scene_count"] = len(thumbnail_files)

            return result

        except Exception as e:
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=f"Scene thumbnail generation failed: {str(e)}",
            )


# Convenience function for direct usage
def get_media_helpers(ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> MediaHelpers:
    """
    Get MediaHelpers instance with specified FFmpeg paths.

    Args:
        ffmpeg_path: Path to ffmpeg executable
        ffprobe_path: Path to ffprobe executable

    Returns:
        MediaHelpers instance
    """
    return MediaHelpers(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)
