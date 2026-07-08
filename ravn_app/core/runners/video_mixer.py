"""
High-level video mixing, compositing, and filtering helpers built on top of FFmpegRunner.
"""

from __future__ import annotations

import logging
import math
import tempfile
from pathlib import Path
from typing import Callable, Optional, Sequence

from ravn_app.core.runners.base import RunnerResult
from ravn_app.core.runners.ffmpeg import FFmpegRunner

logger = logging.getLogger(__name__)
ProgressCallback = Optional[Callable[[int, str], None]]


class VideoMixerRunner:
    """High-level FFmpeg-backed video compositing and filter operations."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self._runner = FFmpegRunner(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)

    @staticmethod
    def _failure(message: str) -> RunnerResult:
        return RunnerResult(success=False, return_code=-1, error_message=message)

    @staticmethod
    def _ensure_output_dir(output_file: str) -> None:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _find_missing_file(paths: Sequence[str]) -> Optional[str]:
        for path in paths:
            if not Path(path).exists():
                return path
        return None

    @staticmethod
    def _resolve_video_codec(output_file: str, override: Optional[str] = None) -> str:
        if override:
            return override
        suffix = Path(output_file).suffix.lower()
        codec_map = {
            ".avi": "mpeg4",
            ".mkv": "libx264",
            ".mov": "libx264",
            ".mp4": "libx264",
            ".webm": "libvpx-vp9",
        }
        return codec_map.get(suffix, "libx264")

    @staticmethod
    def _resolve_audio_codec(output_file: str) -> str:
        return "libopus" if Path(output_file).suffix.lower() == ".webm" else "aac"

    @staticmethod
    def _resolve_position(position: str, margin: int = 16) -> tuple[str, str]:
        raw = str(position or "top-left").strip().lower()
        if "," in raw:
            x_value, y_value = raw.split(",", 1)
            return x_value.strip(), y_value.strip()

        mapping = {
            "top-left": (str(margin), str(margin)),
            "top-right": (f"main_w-overlay_w-{margin}", str(margin)),
            "bottom-left": (str(margin), f"main_h-overlay_h-{margin}"),
            "bottom-right": (f"main_w-overlay_w-{margin}", f"main_h-overlay_h-{margin}"),
            "center": ("(main_w-overlay_w)/2", "(main_h-overlay_h)/2"),
        }
        return mapping.get(raw, (str(margin), str(margin)))

    @staticmethod
    def _overlay_prep_chain(scale: Optional[float], opacity: float) -> str:
        chain: list[str] = []
        if scale is not None:
            if 0 < scale <= 1:
                chain.append(f"scale=iw*{scale}:ih*{scale}")
            else:
                chain.append(f"scale={int(scale)}:-1")
        if 0 < opacity < 1:
            chain.extend(["format=rgba", f"colorchannelmixer=aa={opacity}"])
        return ",".join(chain)

    def concat(
        self,
        input_files: Sequence[str],
        output_file: str,
        reencode: bool = False,
        video_codec: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Concatenate multiple video files into a single output file."""
        if len(input_files) < 2:
            return self._failure("At least two input files are required for concatenation")

        missing = self._find_missing_file(input_files)
        if missing:
            return self._failure(f"Input file not found: {missing}")

        self._ensure_output_dir(output_file)
        concat_file: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".concat.txt", delete=False, encoding="utf-8") as handle:
                concat_file = handle.name
                for item in input_files:
                    handle.write(f"file '{Path(item).resolve().as_posix()}'\n")

            args = ["-f", "concat", "-safe", "0", "-i", concat_file]
            if reencode:
                args.extend(
                    [
                        "-c:v",
                        self._resolve_video_codec(output_file, video_codec),
                        "-c:a",
                        self._resolve_audio_codec(output_file),
                    ]
                )
            else:
                args.extend(["-c", "copy"])
            args.extend(["-y", output_file])

            if progress_callback:
                progress_callback(10, "Preparing video concatenation")
            result = self._runner.run_raw(args)
            if progress_callback and result.success:
                progress_callback(100, "Video concatenation complete")
            result.metadata.update(
                {
                    "operation": "concat",
                    "input_files": list(input_files),
                    "output_file": output_file,
                    "reencode": reencode,
                }
            )
            return result
        finally:
            if concat_file:
                Path(concat_file).unlink(missing_ok=True)

    def overlay(
        self,
        base_file: str,
        overlay_file: str,
        output_file: str,
        position: str = "top-left",
        scale: Optional[float] = None,
        opacity: float = 1.0,
        video_codec: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Overlay one video or image on top of another video."""
        missing = self._find_missing_file([base_file, overlay_file])
        if missing:
            return self._failure(f"Input file not found: {missing}")

        self._ensure_output_dir(output_file)
        x_pos, y_pos = self._resolve_position(position)
        overlay_chain = self._overlay_prep_chain(scale=scale, opacity=opacity)
        filter_parts: list[str] = []
        overlay_label = "1:v"
        if overlay_chain:
            overlay_label = "overlayv"
            filter_parts.append(f"[1:v]{overlay_chain}[{overlay_label}]")
        filter_parts.append(f"[0:v][{overlay_label}]overlay=x={x_pos}:y={y_pos}:eof_action=pass[vout]")

        args = [
            "-i",
            base_file,
            "-i",
            overlay_file,
            "-filter_complex",
            ";".join(filter_parts),
            "-map",
            "[vout]",
            "-map",
            "0:a?",
            "-c:v",
            self._resolve_video_codec(output_file, video_codec),
            "-c:a",
            self._resolve_audio_codec(output_file),
            "-y",
            output_file,
        ]

        if progress_callback:
            progress_callback(10, "Preparing overlay composition")
        result = self._runner.run_raw(args)
        if progress_callback and result.success:
            progress_callback(100, "Overlay composition complete")
        result.metadata.update(
            {
                "operation": "overlay",
                "base_file": base_file,
                "overlay_file": overlay_file,
                "position": position,
                "output_file": output_file,
            }
        )
        return result

    def picture_in_picture(
        self,
        main_file: str,
        pip_file: str,
        output_file: str,
        position: str = "bottom-right",
        scale: float = 0.25,
        video_codec: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Create a picture-in-picture layout."""
        result = self.overlay(
            base_file=main_file,
            overlay_file=pip_file,
            output_file=output_file,
            position=position,
            scale=scale,
            opacity=1.0,
            video_codec=video_codec,
            progress_callback=progress_callback,
        )
        result.metadata["operation"] = "pip"
        return result

    def side_by_side(
        self,
        left_file: str,
        right_file: str,
        output_file: str,
        orientation: str = "horizontal",
        video_codec: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Create a horizontal or vertical side-by-side layout."""
        missing = self._find_missing_file([left_file, right_file])
        if missing:
            return self._failure(f"Input file not found: {missing}")

        self._ensure_output_dir(output_file)
        stack_filter = "hstack=inputs=2" if orientation.lower() == "horizontal" else "vstack=inputs=2"
        args = [
            "-i",
            left_file,
            "-i",
            right_file,
            "-filter_complex",
            f"[0:v][1:v]{stack_filter}[vout]",
            "-map",
            "[vout]",
            "-map",
            "0:a?",
            "-c:v",
            self._resolve_video_codec(output_file, video_codec),
            "-c:a",
            self._resolve_audio_codec(output_file),
            "-y",
            output_file,
        ]

        if progress_callback:
            progress_callback(10, "Preparing side-by-side composition")
        result = self._runner.run_raw(args)
        if progress_callback and result.success:
            progress_callback(100, "Side-by-side composition complete")
        result.metadata.update(
            {
                "operation": "side_by_side",
                "orientation": orientation,
                "output_file": output_file,
            }
        )
        return result

    def watermark(
        self,
        video_file: str,
        watermark_file: str,
        output_file: str,
        position: str = "top-right",
        scale: Optional[float] = None,
        opacity: float = 1.0,
        video_codec: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Apply an image or video watermark onto a video."""
        result = self.overlay(
            base_file=video_file,
            overlay_file=watermark_file,
            output_file=output_file,
            position=position,
            scale=scale,
            opacity=opacity,
            video_codec=video_codec,
            progress_callback=progress_callback,
        )
        result.metadata["operation"] = "watermark"
        return result

    def transition(
        self,
        first_file: str,
        second_file: str,
        output_file: str,
        duration: float = 1.0,
        transition: str = "fade",
        video_codec: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Create a transition between two videos using xfade/acrossfade."""
        if duration <= 0:
            return self._failure("Transition duration must be greater than zero")

        missing = self._find_missing_file([first_file, second_file])
        if missing:
            return self._failure(f"Input file not found: {missing}")

        self._ensure_output_dir(output_file)
        first_duration = self._runner.get_duration(first_file) or 0.0
        offset = max(first_duration - duration, 0.0)
        filter_complex = (
            f"[0:v][1:v]xfade=transition={transition}:duration={duration}:offset={offset}[vout];"
            f"[0:a][1:a]acrossfade=d={duration}[aout]"
        )
        args = [
            "-i",
            first_file,
            "-i",
            second_file,
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            self._resolve_video_codec(output_file, video_codec),
            "-c:a",
            self._resolve_audio_codec(output_file),
            "-y",
            output_file,
        ]

        if progress_callback:
            progress_callback(10, "Preparing video transition")
        result = self._runner.run_raw(args)
        if progress_callback and result.success:
            progress_callback(100, "Video transition complete")
        result.metadata.update(
            {
                "operation": "transition",
                "transition": transition,
                "duration": duration,
                "offset": offset,
                "output_file": output_file,
            }
        )
        return result

    def replace_audio(
        self,
        video_file: str,
        audio_file: str,
        output_file: str,
        audio_codec: Optional[str] = None,
        shortest: bool = True,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Replace or synchronize a video's audio stream with an external audio file."""
        missing = self._find_missing_file([video_file, audio_file])
        if missing:
            return self._failure(f"Input file not found: {missing}")

        self._ensure_output_dir(output_file)
        args = [
            "-i",
            video_file,
            "-i",
            audio_file,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            audio_codec or self._resolve_audio_codec(output_file),
        ]
        if shortest:
            args.append("-shortest")
        args.extend(["-y", output_file])

        if progress_callback:
            progress_callback(10, "Preparing audio synchronization")
        result = self._runner.run_raw(args)
        if progress_callback and result.success:
            progress_callback(100, "Audio synchronization complete")
        result.metadata.update(
            {
                "operation": "replace_audio",
                "video_file": video_file,
                "audio_file": audio_file,
                "shortest": shortest,
                "output_file": output_file,
            }
        )
        return result

    def extract_frame(
        self,
        input_file: str,
        output_file: str,
        timestamp: float = 0.0,
    ) -> RunnerResult:
        """Extract a single frame from a video."""
        if timestamp < 0:
            return self._failure("Timestamp must be zero or positive")
        if not Path(input_file).exists():
            return self._failure(f"Input file not found: {input_file}")

        self._ensure_output_dir(output_file)
        result = self._runner.run_raw(
            ["-ss", str(timestamp), "-i", input_file, "-frames:v", "1", "-y", output_file]
        )
        result.metadata.update(
            {
                "operation": "extract_frame",
                "input_file": input_file,
                "output_file": output_file,
                "timestamp": timestamp,
            }
        )
        return result

    def create_from_frames(
        self,
        frames_pattern: str,
        output_file: str,
        fps: int = 24,
        video_codec: Optional[str] = None,
    ) -> RunnerResult:
        """Create a video from an image sequence pattern."""
        if fps <= 0:
            return self._failure("FPS must be greater than zero")

        self._ensure_output_dir(output_file)
        result = self._runner.run_raw(
            [
                "-framerate",
                str(fps),
                "-i",
                frames_pattern,
                "-c:v",
                self._resolve_video_codec(output_file, video_codec),
                "-pix_fmt",
                "yuv420p",
                "-y",
                output_file,
            ]
        )
        result.metadata.update(
            {
                "operation": "create_from_frames",
                "frames_pattern": frames_pattern,
                "fps": fps,
                "output_file": output_file,
            }
        )
        return result

    def apply_filters(
        self,
        input_file: str,
        output_file: str,
        *,
        brightness: Optional[float] = None,
        contrast: Optional[float] = None,
        saturation: Optional[float] = None,
        hue: Optional[float] = None,
        gamma: Optional[float] = None,
        crop_left: int = 0,
        crop_top: int = 0,
        crop_right: int = 0,
        crop_bottom: int = 0,
        rotate: Optional[float] = None,
        flip_horizontal: bool = False,
        flip_vertical: bool = False,
        blur: Optional[float] = None,
        sharpen: Optional[float] = None,
        denoise: Optional[str] = None,
        grayscale: bool = False,
        sepia: bool = False,
        invert: bool = False,
        deinterlace: bool = False,
        lut_file: Optional[str] = None,
        video_codec: Optional[str] = None,
        bitrate: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Apply a chain of FFmpeg filters to a video file."""
        if not Path(input_file).exists():
            return self._failure(f"Input file not found: {input_file}")
        if lut_file and not Path(lut_file).exists():
            return self._failure(f"LUT file not found: {lut_file}")

        filters: list[str] = []

        eq_parts: list[str] = []
        if brightness is not None:
            normalized_brightness = brightness / 100.0 if abs(brightness) > 1 else brightness
            eq_parts.append(f"brightness={normalized_brightness}")
        if contrast is not None:
            eq_parts.append(f"contrast={contrast}")
        if saturation is not None:
            eq_parts.append(f"saturation={saturation}")
        if gamma is not None:
            eq_parts.append(f"gamma={gamma}")
        if eq_parts:
            filters.append(f"eq={':'.join(eq_parts)}")

        if hue is not None:
            filters.append(f"hue=h={hue}")

        if any(value > 0 for value in (crop_left, crop_top, crop_right, crop_bottom)):
            filters.append(
                f"crop=w=iw-{crop_left}-{crop_right}:h=ih-{crop_top}-{crop_bottom}:x={crop_left}:y={crop_top}"
            )

        if rotate is not None:
            rotation = int(rotate) if float(rotate).is_integer() else rotate
            if rotation == 90:
                filters.append("transpose=1")
            elif rotation == 180:
                filters.extend(["hflip", "vflip"])
            elif rotation == 270:
                filters.append("transpose=2")
            else:
                filters.append(f"rotate={math.radians(float(rotate))}:fillcolor=black")

        if flip_horizontal:
            filters.append("hflip")
        if flip_vertical:
            filters.append("vflip")
        if blur is not None:
            filters.append(f"gblur=sigma={blur}")
        if sharpen is not None:
            filters.append(f"unsharp=5:5:{sharpen}:5:5:0")

        denoise_map = {
            "light": "hqdn3d=1.5:1.5:6:6",
            "moderate": "hqdn3d=3:3:6:6",
            "strong": "hqdn3d=4.5:4.5:9:9",
            "ultra": "hqdn3d=6:6:12:12",
        }
        if denoise:
            filters.append(denoise_map.get(str(denoise).lower(), denoise_map["moderate"]))

        if grayscale:
            filters.append("format=gray")
        if sepia:
            filters.append("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131")
        if invert:
            filters.append("negate")
        if deinterlace:
            filters.append("yadif")
        if lut_file:
            filters.append(f"lut3d=file='{Path(lut_file).as_posix()}'")

        if not filters:
            return self._failure("At least one filter option must be provided")

        extra_args = ["-vf", ",".join(filters)]
        if bitrate:
            extra_args.extend(["-b:v", bitrate])

        self._ensure_output_dir(output_file)
        result = self._runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=["-c:v", self._resolve_video_codec(output_file, video_codec)],
            audio_args=["-c:a", "copy"],
            extra_args=extra_args,
            progress_callback=progress_callback,
            use_realtime_progress=True,
        )
        result.metadata.update(
            {
                "operation": "apply_filters",
                "output_file": output_file,
                "filters": filters,
            }
        )
        return result

    def cancel(self) -> bool:
        """Cancel the currently running FFmpeg process if one is active."""
        return self._runner.cancel()
