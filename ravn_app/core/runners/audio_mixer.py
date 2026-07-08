"""
High-level audio mixing and editing helpers built on top of FFmpegRunner.
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

from ravn_app.core.runners.base import RunnerResult
from ravn_app.core.runners.ffmpeg import FFmpegRunner

logger = logging.getLogger(__name__)
ProgressCallback = Optional[Callable[[int, str], None]]


@dataclass
class AudioTrack:
    """Single audio track configuration for mix operations."""

    file_path: str
    volume: float = 1.0
    delay_ms: int = 0


class AudioMixerRunner:
    """High-level FFmpeg-backed audio mixing operations."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self._runner = FFmpegRunner(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)

    @staticmethod
    def _failure(message: str) -> RunnerResult:
        return RunnerResult(success=False, return_code=-1, error_message=message)

    @staticmethod
    def _resolve_audio_codec(output_file: str, override: Optional[str] = None) -> str:
        if override:
            return override

        suffix = Path(output_file).suffix.lower()
        codec_map = {
            ".aac": "aac",
            ".flac": "flac",
            ".m4a": "aac",
            ".mp3": "libmp3lame",
            ".ogg": "libvorbis",
            ".opus": "libopus",
            ".wav": "pcm_s16le",
        }
        return codec_map.get(suffix, "aac")

    @staticmethod
    def _ensure_output_dir(output_file: str) -> None:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _find_missing_file(paths: Sequence[str]) -> Optional[str]:
        for path in paths:
            if not Path(path).exists():
                return path
        return None

    def concat(
        self,
        input_files: Sequence[str],
        output_file: str,
        codec: Optional[str] = None,
        bitrate: Optional[str] = None,
        sample_rate: Optional[int] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Concatenate multiple audio files into a single output file."""
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

            args = [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_file,
                "-vn",
                "-c:a",
                self._resolve_audio_codec(output_file, codec),
            ]
            if bitrate:
                args.extend(["-b:a", bitrate])
            if sample_rate:
                args.extend(["-ar", str(sample_rate)])
            args.extend(["-y", output_file])

            if progress_callback:
                progress_callback(10, "Preparing audio concatenation")
            result = self._runner.run_raw(args)
            if progress_callback and result.success:
                progress_callback(100, "Audio concatenation complete")
            result.metadata.update(
                {
                    "operation": "concat",
                    "input_files": list(input_files),
                    "output_file": output_file,
                }
            )
            return result
        finally:
            if concat_file:
                Path(concat_file).unlink(missing_ok=True)

    def mix(
        self,
        tracks: Sequence[AudioTrack],
        output_file: str,
        codec: Optional[str] = None,
        bitrate: Optional[str] = None,
        sample_rate: Optional[int] = None,
        normalize: bool = False,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Mix multiple tracks into a single output stream."""
        if len(tracks) < 2:
            return self._failure("At least two tracks are required for audio mixing")

        missing = self._find_missing_file([track.file_path for track in tracks])
        if missing:
            return self._failure(f"Input file not found: {missing}")

        self._ensure_output_dir(output_file)

        args: list[str] = []
        filter_parts: list[str] = []
        labels: list[str] = []

        for index, track in enumerate(tracks):
            args.extend(["-i", track.file_path])
            label = f"a{index}"
            labels.append(label)
            chain: list[str] = []
            if track.delay_ms > 0:
                chain.append(f"adelay={track.delay_ms}|{track.delay_ms}")
            if track.volume != 1.0:
                chain.append(f"volume={track.volume}")
            chain_str = ",".join(chain) if chain else "anull"
            filter_parts.append(f"[{index}:a]{chain_str}[{label}]")

        mixed_label = "mix0"
        mix_inputs = "".join(f"[{label}]" for label in labels)
        filter_parts.append(
            f"{mix_inputs}amix=inputs={len(labels)}:dropout_transition=2:normalize=0[{mixed_label}]"
        )

        final_label = mixed_label
        post_filters: list[str] = []
        if sample_rate:
            post_filters.append(f"aresample={sample_rate}")
        if normalize:
            post_filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
        if post_filters:
            final_label = "mixout"
            filter_parts.append(f"[{mixed_label}]{','.join(post_filters)}[{final_label}]")

        args.extend(
            [
                "-filter_complex",
                ";".join(filter_parts),
                "-map",
                f"[{final_label}]",
                "-c:a",
                self._resolve_audio_codec(output_file, codec),
            ]
        )
        if bitrate:
            args.extend(["-b:a", bitrate])
        args.extend(["-y", output_file])

        if progress_callback:
            progress_callback(10, "Preparing audio mix")
        result = self._runner.run_raw(args)
        if progress_callback and result.success:
            progress_callback(100, "Audio mix complete")
        result.metadata.update(
            {
                "operation": "mix",
                "track_count": len(tracks),
                "output_file": output_file,
                "normalize": normalize,
            }
        )
        return result

    def crossfade(
        self,
        input_files: Sequence[str],
        output_file: str,
        duration: float,
        codec: Optional[str] = None,
        bitrate: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Crossfade audio files sequentially."""
        if duration <= 0:
            return self._failure("Crossfade duration must be greater than zero")
        if len(input_files) < 2:
            return self._failure("At least two input files are required for crossfade")

        missing = self._find_missing_file(input_files)
        if missing:
            return self._failure(f"Input file not found: {missing}")

        self._ensure_output_dir(output_file)

        args: list[str] = []
        for path in input_files:
            args.extend(["-i", path])

        filter_parts: list[str] = []
        previous_label = "0:a"
        for index in range(1, len(input_files)):
            next_label = f"cf{index}"
            filter_parts.append(
                f"[{previous_label}][{index}:a]acrossfade=d={duration}:c1=tri:c2=tri[{next_label}]"
            )
            previous_label = next_label

        args.extend(
            [
                "-filter_complex",
                ";".join(filter_parts),
                "-map",
                f"[{previous_label}]",
                "-c:a",
                self._resolve_audio_codec(output_file, codec),
            ]
        )
        if bitrate:
            args.extend(["-b:a", bitrate])
        args.extend(["-y", output_file])

        if progress_callback:
            progress_callback(10, "Preparing audio crossfade")
        result = self._runner.run_raw(args)
        if progress_callback and result.success:
            progress_callback(100, "Audio crossfade complete")
        result.metadata.update(
            {
                "operation": "crossfade",
                "input_files": list(input_files),
                "duration": duration,
                "output_file": output_file,
            }
        )
        return result

    def normalize(
        self,
        input_file: str,
        output_file: str,
        target_lufs: float = -16.0,
        target_peak: float = -1.5,
        codec: Optional[str] = None,
        bitrate: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Normalize loudness of a single audio file."""
        if not Path(input_file).exists():
            return self._failure(f"Input file not found: {input_file}")

        audio_filter = f"loudnorm=I={target_lufs}:TP={target_peak}:LRA=11"
        result = self._runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=["-vn"],
            audio_args=["-c:a", self._resolve_audio_codec(output_file, codec)],
            extra_args=["-af", audio_filter] + (["-b:a", bitrate] if bitrate else []),
            progress_callback=progress_callback,
            use_realtime_progress=True,
        )
        result.metadata.update(
            {
                "operation": "normalize",
                "input_file": input_file,
                "output_file": output_file,
                "target_lufs": target_lufs,
            }
        )
        return result

    def trim(
        self,
        input_file: str,
        output_file: str,
        start_time: float,
        duration: float,
        codec: Optional[str] = None,
        bitrate: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Trim a segment from an audio file."""
        if start_time < 0 or duration <= 0:
            return self._failure("Trim start time and duration must be valid positive values")
        if not Path(input_file).exists():
            return self._failure(f"Input file not found: {input_file}")

        extra_args = ["-ss", str(start_time), "-t", str(duration)]
        if bitrate:
            extra_args.extend(["-b:a", bitrate])
        result = self._runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=["-vn"],
            audio_args=["-c:a", self._resolve_audio_codec(output_file, codec)],
            extra_args=extra_args,
            progress_callback=progress_callback,
            use_realtime_progress=True,
        )
        result.metadata.update(
            {
                "operation": "trim",
                "input_file": input_file,
                "output_file": output_file,
                "start_time": start_time,
                "duration": duration,
            }
        )
        return result

    def convert_sample_rate(
        self,
        input_file: str,
        output_file: str,
        sample_rate: int,
        codec: Optional[str] = None,
        bitrate: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Convert sample rate for a single audio file."""
        if sample_rate <= 0:
            return self._failure("Sample rate must be greater than zero")
        if not Path(input_file).exists():
            return self._failure(f"Input file not found: {input_file}")

        extra_args = ["-ar", str(sample_rate)]
        if bitrate:
            extra_args.extend(["-b:a", bitrate])
        result = self._runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=["-vn"],
            audio_args=["-c:a", self._resolve_audio_codec(output_file, codec)],
            extra_args=extra_args,
            progress_callback=progress_callback,
            use_realtime_progress=True,
        )
        result.metadata.update(
            {
                "operation": "sample_rate",
                "sample_rate": sample_rate,
                "output_file": output_file,
            }
        )
        return result

    def apply_fade(
        self,
        input_file: str,
        output_file: str,
        fade_in_duration: float = 0.0,
        fade_out_duration: float = 0.0,
        codec: Optional[str] = None,
        bitrate: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Apply fade-in and/or fade-out effects."""
        if not Path(input_file).exists():
            return self._failure(f"Input file not found: {input_file}")
        if fade_in_duration < 0 or fade_out_duration < 0:
            return self._failure("Fade durations must be zero or positive")

        duration = self._runner.get_duration(input_file) or 0.0
        filters: list[str] = []
        if fade_in_duration > 0:
            filters.append(f"afade=t=in:st=0:d={fade_in_duration}")
        if fade_out_duration > 0:
            start = max(duration - fade_out_duration, 0.0)
            filters.append(f"afade=t=out:st={start}:d={fade_out_duration}")
        if not filters:
            return self._failure("At least one fade duration must be provided")

        extra_args = ["-af", ",".join(filters)]
        if bitrate:
            extra_args.extend(["-b:a", bitrate])
        result = self._runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=["-vn"],
            audio_args=["-c:a", self._resolve_audio_codec(output_file, codec)],
            extra_args=extra_args,
            progress_callback=progress_callback,
            use_realtime_progress=True,
        )
        result.metadata.update(
            {
                "operation": "fade",
                "fade_in_duration": fade_in_duration,
                "fade_out_duration": fade_out_duration,
                "output_file": output_file,
            }
        )
        return result

    def inject_silence(
        self,
        input_file: str,
        output_file: str,
        prepend_seconds: float = 0.0,
        append_seconds: float = 0.0,
        sample_rate: int = 44100,
        codec: Optional[str] = None,
        bitrate: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> RunnerResult:
        """Inject silence before and/or after an audio file."""
        if prepend_seconds < 0 or append_seconds < 0:
            return self._failure("Silence durations must be zero or positive")
        if prepend_seconds == 0 and append_seconds == 0:
            return self._failure("Either prepend_seconds or append_seconds must be greater than zero")
        if not Path(input_file).exists():
            return self._failure(f"Input file not found: {input_file}")

        self._ensure_output_dir(output_file)
        args: list[str] = []
        input_count = 0
        if prepend_seconds > 0:
            args.extend(["-f", "lavfi", "-t", str(prepend_seconds), "-i", f"anullsrc=r={sample_rate}:cl=stereo"])
            input_count += 1
        args.extend(["-i", input_file])
        main_index = input_count
        input_count += 1
        if append_seconds > 0:
            args.extend(["-f", "lavfi", "-t", str(append_seconds), "-i", f"anullsrc=r={sample_rate}:cl=stereo"])
            input_count += 1

        labels = [f"[{index}:a]" for index in range(input_count)]
        if main_index != 0 and prepend_seconds == 0:
            labels.insert(0, labels.pop(main_index))
        filter_complex = f"{''.join(labels)}concat=n={input_count}:v=0:a=1[aout]"

        args.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[aout]",
                "-c:a",
                self._resolve_audio_codec(output_file, codec),
            ]
        )
        if bitrate:
            args.extend(["-b:a", bitrate])
        args.extend(["-y", output_file])

        if progress_callback:
            progress_callback(10, "Injecting silence")
        result = self._runner.run_raw(args)
        if progress_callback and result.success:
            progress_callback(100, "Silence injection complete")
        result.metadata.update(
            {
                "operation": "inject_silence",
                "prepend_seconds": prepend_seconds,
                "append_seconds": append_seconds,
                "output_file": output_file,
            }
        )
        return result

    def cancel(self) -> bool:
        """Cancel the currently running FFmpeg process if one is active."""
        return self._runner.cancel()
