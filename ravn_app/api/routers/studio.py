"""
ravn_app/api/routers/studio.py — Endpoints for Studio workspace media operations.

Covers:
- Video & Audio Transcoding (/convert/start)
- Subtitle downloading & processing (/subtitle/download, /subtitle/process)
- Video filter application (/filters/apply)
- Audio/Video mixing operations (/mixer/run)
- Utility operations (/utilities/run)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ravn_app.api.deps import QueueDep
from ravn_app.core.task_manager import TaskType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["studio"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ConvertStartRequest(BaseModel):
    input_file: str = Field(..., description="Path to source media file")
    output_file: Optional[str] = Field(None, description="Optional target destination path")
    video_codec: str = Field("h264", description="Video codec (h264, hevc, vp9, av1, copy)")
    audio_codec: str = Field("aac", description="Audio codec (aac, mp3, opus, flac, copy)")
    video_quality: str = Field("HIGH", description="Quality level / CRF (LOSSLESS, VERYHIGH, HIGH, MEDIUM, LOW, VERYLOW)")
    audio_bitrate: str = Field("192k", description="Audio bitrate (320k, 256k, 192k, 128k, 96k)")
    preset: Optional[str] = Field("fast", description="FFmpeg speed preset")
    hardware_accel: Optional[str] = Field(None, description="Hardware acceleration: nvenc, quicksync, amf")


class SubtitleDownloadRequest(BaseModel):
    url: str = Field(..., description="Media URL to fetch subtitles from")
    output_dir: Optional[str] = Field(None, description="Output directory")
    languages: List[str] = Field(default_factory=lambda: ["tr", "en"], description="List of language codes")
    auto_generated: bool = Field(True, description="Whether to include auto-generated subtitles")


class SubtitleProcessRequest(BaseModel):
    action: str = Field(..., description="Action: 'convert', 'shift', 'mux', or 'burn'")
    subtitle_file: str = Field(..., description="Path to subtitle file")
    video_file: Optional[str] = Field(None, description="Path to video file (required for mux/burn)")
    output_file: Optional[str] = Field(None, description="Path to output file")
    shift_seconds: Optional[float] = Field(0.0, description="Time shift in seconds (for shift)")
    output_format: Optional[str] = Field("srt", description="Target subtitle format (for convert)")


class FilterApplyRequest(BaseModel):
    input_file: str = Field(..., description="Input media path")
    output_file: Optional[str] = Field(None, description="Output media path")
    brightness: Optional[float] = Field(0.0, description="Brightness adjustment (-1.0 to 1.0)")
    contrast: Optional[float] = Field(1.0, description="Contrast multiplier (0.0 to 3.0)")
    saturation: Optional[float] = Field(1.0, description="Saturation multiplier (0.0 to 3.0)")
    blur: Optional[float] = Field(0.0, description="Blur amount (0.0 to 10.0)")
    sharpen: Optional[float] = Field(0.0, description="Sharpen amount (0.0 to 5.0)")
    rotate: Optional[int] = Field(0, description="Rotation degrees: 0, 90, 180, 270")
    flip_h: bool = Field(False, description="Horizontal flip")
    flip_v: bool = Field(False, description="Vertical flip")
    grayscale: bool = Field(False, description="Convert to grayscale")
    sepia: bool = Field(False, description="Apply sepia tone")
    invert: bool = Field(False, description="Invert colors")
    deinterlace: bool = Field(False, description="Apply deinterlacing")
    denoise: Optional[str] = Field("off", description="Denoise level: off, light, moderate, strong, ultra")
    lut_file: Optional[str] = Field(None, description="Path to 3D LUT file")


class MixerRunRequest(BaseModel):
    mode: str = Field("audio", description="Mode: 'audio' or 'video'")
    operation: str = Field(..., description="Operation name")
    input_files: List[str] = Field(..., description="List of source input file paths")
    output_file: Optional[str] = Field(None, description="Output file path")
    options: Dict[str, Any] = Field(default_factory=dict, description="Operation specific options")


class UtilitiesRunRequest(BaseModel):
    category: str = Field("quick", description="Category: 'quick', 'audio', 'video', or 'smart'")
    operation: str = Field(..., description="Operation name")
    input_file: str = Field(..., description="Source media file path")
    output_file: Optional[str] = Field(None, description="Output destination file path")
    options: Dict[str, Any] = Field(default_factory=dict, description="Operation specific options")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/convert/start", summary="Start or queue a media conversion task", status_code=202)
def start_conversion(
    body: ConvertStartRequest,
    queue: QueueDep,
) -> Dict[str, Any]:
    """Queue a video or audio conversion task."""
    input_path = Path(body.input_file)

    from ravn_app.core.converter import (
        AudioBitrate,
        AudioCodec,
        ConversionSettings,
        VideoCodec,
        VideoConverter,
        VideoQuality,
    )

    out_file = body.output_file
    if not out_file:
        out_ext = ".mp4" if body.video_codec != "copy" else input_path.suffix or ".mp4"
        out_file = str(input_path.with_name(f"{input_path.stem}_converted{out_ext}"))

    v_codec = getattr(VideoCodec, body.video_codec.upper(), VideoCodec.H264)
    a_codec = getattr(AudioCodec, body.audio_codec.upper(), AudioCodec.AAC)
    v_quality = getattr(VideoQuality, body.video_quality.upper(), VideoQuality.HIGH)
    a_bitrate = getattr(AudioBitrate, body.audio_bitrate.upper(), AudioBitrate.HIGH)

    settings = ConversionSettings(
        input_file=str(input_path),
        output_file=out_file,
        video_codec=v_codec,
        audio_codec=a_codec,
        video_quality=v_quality,
        audio_bitrate=a_bitrate,
        preset=body.preset,
        hardware_accel=body.hardware_accel,
    )

    conv = VideoConverter()

    task_id = queue.add_task(
        task_type=TaskType.CONVERT,
        name=f"Convert: {input_path.name}",
        execute_fn=conv.convert,
        args=(settings,),
    )

    return {
        "task_id": task_id,
        "name": f"Convert: {input_path.name}",
        "input_file": str(input_path),
        "output_file": out_file,
        "status": "queued",
    }


@router.post("/subtitle/download", summary="Download subtitles for video URL", status_code=202)
def download_subtitles(
    body: SubtitleDownloadRequest,
    queue: QueueDep,
) -> Dict[str, Any]:
    """Download subtitle files from YouTube or supported platforms."""
    from ravn_app.core.subtitle_manager import SubtitleDownloader

    downloader = SubtitleDownloader()
    out_dir = body.output_dir or str(Path.home() / "Downloads" / "RAVN")

    task_id = queue.add_task(
        task_type=TaskType.SUBTITLE,
        name=f"Subtitles: {body.url[:30]}...",
        execute_fn=downloader.download_subtitles,
        kwargs={
            "video_url": body.url,
            "output_dir": out_dir,
            "languages": body.languages,
            "auto_sub": body.auto_generated,
        },
    )

    return {
        "task_id": task_id,
        "url": body.url,
        "languages": body.languages,
        "status": "queued",
    }


@router.post("/subtitle/process", summary="Convert, shift, or embed subtitles", status_code=200)
def process_subtitles(body: SubtitleProcessRequest) -> Dict[str, Any]:
    """Execute synchronous subtitle conversion, timing shift, or embedding."""
    from ravn_app.core.subtitle_manager import (
        SubtitleConverter,
        SubtitleEditor,
        SubtitleEmbedder,
        SubtitleFormat,
    )

    sub_path = Path(body.subtitle_file)
    action = body.action.lower()

    if action == "convert":
        target_fmt = getattr(SubtitleFormat, (body.output_format or "srt").upper(), SubtitleFormat.SRT)
        out_path = body.output_file or str(sub_path.with_suffix(f".{target_fmt.value}"))
        conv = SubtitleConverter()
        success = conv.convert(str(sub_path), target_fmt, out_path)
        if not success:
            raise HTTPException(status_code=500, detail="Subtitle format conversion failed")
        return {"status": "success", "action": "convert", "output_file": out_path}

    elif action == "shift":
        editor = SubtitleEditor()
        out_path = body.output_file or str(sub_path.with_name(f"{sub_path.stem}_shifted{sub_path.suffix}"))
        shift_ms = int((body.shift_seconds or 0.0) * 1000)
        success = editor.shift_timing(str(sub_path), out_path, shift_ms)
        if not success:
            raise HTTPException(status_code=500, detail="Subtitle timing shift failed")
        return {"status": "success", "action": "shift", "output_file": out_path}

    elif action in ("mux", "burn"):
        if not body.video_file:
            raise HTTPException(status_code=400, detail="Valid video file required for mux/burn")
        embedder = SubtitleEmbedder()
        v_path = Path(body.video_file)
        out_path = body.output_file or str(v_path.with_name(f"{v_path.stem}_subbed{v_path.suffix}"))

        if action == "mux":
            success = embedder.embed_soft(str(v_path), str(sub_path), out_path)
        else:
            success = embedder.embed_hard(str(v_path), str(sub_path), out_path)

        if not success:
            raise HTTPException(status_code=500, detail=f"Subtitle {action} failed")
        return {"status": "success", "action": action, "output_file": out_path}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown subtitle action: {action}")


@router.post("/filters/apply", summary="Apply video filters and adjustments", status_code=202)
def apply_filters(
    body: FilterApplyRequest,
    queue: QueueDep,
) -> Dict[str, Any]:
    """Queue a video filter processing task."""
    in_path = Path(body.input_file)

    from ravn_app.core.runners import VideoMixerRunner

    out_file = body.output_file or str(in_path.with_name(f"{in_path.stem}_filtered{in_path.suffix or '.mp4'}"))
    runner = VideoMixerRunner()

    filter_kwargs = {
        "brightness": body.brightness,
        "contrast": body.contrast,
        "saturation": body.saturation,
        "blur": body.blur,
        "sharpen": body.sharpen,
        "rotate": float(body.rotate) if body.rotate is not None else None,
        "flip_horizontal": body.flip_h,
        "flip_vertical": body.flip_v,
        "grayscale": body.grayscale,
        "sepia": body.sepia,
        "invert": body.invert,
        "deinterlace": body.deinterlace,
        "denoise": body.denoise if body.denoise != "off" else None,
        "lut_file": body.lut_file,
    }

    def _execute_filter_task(progress_callback=None):
        return runner.apply_filters(
            input_file=str(in_path),
            output_file=out_file,
            progress_callback=progress_callback,
            **filter_kwargs,
        )

    task_id = queue.add_task(
        task_type=TaskType.APPLY_FILTERS,
        name=f"Filters: {in_path.name}",
        execute_fn=_execute_filter_task,
    )

    return {
        "task_id": task_id,
        "input_file": str(in_path),
        "output_file": out_file,
        "status": "queued",
    }


@router.post("/mixer/run", summary="Run audio/video mixer operation", status_code=202)
def run_mixer(
    body: MixerRunRequest,
    queue: QueueDep,
) -> Dict[str, Any]:
    """Queue an audio or video mixing task."""
    if not body.input_files:
        raise HTTPException(status_code=400, detail="At least one input file required")

    from ravn_app.core.runners import AudioMixerRunner, AudioTrack, VideoMixerRunner

    first_path = Path(body.input_files[0])
    out_file = body.output_file or str(first_path.with_name(f"{first_path.stem}_mixed{first_path.suffix or '.mp4'}"))

    if body.mode.lower() == "audio":
        a_runner = AudioMixerRunner()
        t_type = TaskType.MIXER_AUDIO

        def _execute_audio_mix(progress_callback=None):
            op = body.operation.lower()
            if op == "concat":
                return a_runner.concat(body.input_files, out_file, progress_callback=progress_callback)
            elif op == "mix":
                tracks = [AudioTrack(file_path=f) for f in body.input_files]
                return a_runner.mix(tracks, out_file, progress_callback=progress_callback)
            elif op == "crossfade":
                dur = float(body.options.get("duration", 2.0))
                return a_runner.crossfade(body.input_files, out_file, duration=dur, progress_callback=progress_callback)
            elif op == "normalize":
                return a_runner.normalize(body.input_files[0], out_file, progress_callback=progress_callback)
            elif op == "trim":
                st = float(body.options.get("start", 0.0))
                dur = float(body.options.get("duration", 30.0))
                return a_runner.trim(body.input_files[0], out_file, start_time=st, duration=dur, progress_callback=progress_callback)
            elif op == "fade":
                fi = float(body.options.get("fade_in", 1.0))
                fo = float(body.options.get("fade_out", 1.0))
                return a_runner.apply_fade(body.input_files[0], out_file, fade_in_duration=fi, fade_out_duration=fo, progress_callback=progress_callback)
            return a_runner._failure(f"Unknown audio mixer op: {op}")

        exec_fn = _execute_audio_mix
    else:
        v_runner = VideoMixerRunner()
        t_type = TaskType.MIXER_VIDEO

        def _execute_video_mix(progress_callback=None):
            op = body.operation.lower()
            if op == "concat":
                return v_runner.concat(body.input_files, out_file, progress_callback=progress_callback)
            elif op == "overlay":
                sec = body.input_files[1] if len(body.input_files) > 1 else body.input_files[0]
                pos = str(body.options.get("position", "bottom_right"))
                return v_runner.overlay(body.input_files[0], sec, out_file, position=pos, progress_callback=progress_callback)
            elif op == "pip":
                pip = body.input_files[1] if len(body.input_files) > 1 else body.input_files[0]
                scale = float(body.options.get("scale", 0.25))
                pos = str(body.options.get("position", "bottom_right"))
                return v_runner.picture_in_picture(body.input_files[0], pip, out_file, scale=scale, position=pos, progress_callback=progress_callback)
            elif op == "side-by-side":
                sec = body.input_files[1] if len(body.input_files) > 1 else body.input_files[0]
                orient = str(body.options.get("orientation", "horizontal"))
                return v_runner.side_by_side(body.input_files[0], sec, out_file, orientation=orient, progress_callback=progress_callback)
            elif op == "watermark":
                wm = body.input_files[1] if len(body.input_files) > 1 else body.input_files[0]
                pos = str(body.options.get("position", "bottom_right"))
                opac = float(body.options.get("opacity", 1.0))
                return v_runner.watermark(body.input_files[0], wm, out_file, position=pos, opacity=opac, progress_callback=progress_callback)
            elif op == "transition":
                sec = body.input_files[1] if len(body.input_files) > 1 else body.input_files[0]
                dur = float(body.options.get("duration", 1.0))
                return v_runner.transition(body.input_files[0], sec, out_file, duration=dur, progress_callback=progress_callback)
            elif op == "replace-audio":
                audio = body.input_files[1] if len(body.input_files) > 1 else body.input_files[0]
                return v_runner.replace_audio(body.input_files[0], audio, out_file, progress_callback=progress_callback)
            return v_runner._failure(f"Unknown video mixer op: {op}")

        exec_fn = _execute_video_mix

    task_id = queue.add_task(
        task_type=t_type,
        name=f"Mixer ({body.mode}): {body.operation}",
        execute_fn=exec_fn,
    )

    return {
        "task_id": task_id,
        "operation": body.operation,
        "output_file": out_file,
        "status": "queued",
    }


@router.post("/utilities/run", summary="Run media utility operation", status_code=202)
def run_utility(
    body: UtilitiesRunRequest,
    queue: QueueDep,
) -> Dict[str, Any]:
    """Queue a quick, audio, video, or smart helper operation."""
    in_path = Path(body.input_file)

    from ravn_app.core.media_helpers import MediaHelpers

    helpers = MediaHelpers()
    out_file = body.output_file or str(in_path.with_name(f"{in_path.stem}_{body.operation}{in_path.suffix or '.mp4'}"))

    def _execute_util_task(progress_callback=None):
        op = body.operation.lower()
        if op == "remux":
            return helpers.remux(str(in_path), out_file, progress_callback=progress_callback)
        elif op == "extract-audio":
            return helpers.extract_audio(str(in_path), out_file, progress_callback=progress_callback)
        elif op == "mute":
            return helpers.mute_audio(str(in_path), out_file, progress_callback=progress_callback)
        elif op == "trim-30s":
            return helpers.trim_quick(str(in_path), out_file, duration=30.0, progress_callback=progress_callback)
        elif op == "preview-clip":
            return helpers.preview_clip(str(in_path), out_file, duration=10.0, progress_callback=progress_callback)
        elif op == "thumbnail":
            return helpers.generate_thumbnail(str(in_path), out_file)
        elif op == "volume-boost":
            return helpers.boost_volume(str(in_path), out_file, gain_db=3.0, progress_callback=progress_callback)
        elif op == "fade":
            return helpers.fade_audio(str(in_path), out_file, fade_in=1.0, fade_out=1.0, progress_callback=progress_callback)
        elif op == "convert-bitrate":
            return helpers.change_audio_bitrate(str(in_path), out_file, bitrate="192k", sample_rate=44100, progress_callback=progress_callback)
        elif op == "to-stereo":
            return helpers.stereo_to_mono(str(in_path), out_file, mode="stereo", progress_callback=progress_callback)
        elif op == "silence-detect":
            return helpers.detect_silence(str(in_path))
        elif op == "loudness-norm":
            return helpers.normalize_loudness(str(in_path), out_file, progress_callback=progress_callback)
        elif op == "scale-720p":
            return helpers.scale_resolution(str(in_path), out_file, width=1280, height=720, progress_callback=progress_callback)
        elif op == "crop-90":
            return helpers.crop_video(str(in_path), out_file, percentage=90, progress_callback=progress_callback)
        elif op == "pad":
            return helpers.pad_video(str(in_path), out_file, aspect_ratio="16:9", progress_callback=progress_callback)
        elif op == "rotate-90":
            return helpers.rotate_video(str(in_path), out_file, angle=90, progress_callback=progress_callback)
        elif op == "fps-30":
            return helpers.change_fps(str(in_path), out_file, fps=30, progress_callback=progress_callback)
        elif op == "color-adjust":
            return helpers.adjust_color(str(in_path), out_file, brightness=0.05, contrast=1.1, saturation=1.1, progress_callback=progress_callback)
        elif op == "blur-sharpen":
            return helpers.blur_sharpen(str(in_path), out_file, sharpen=1.5, progress_callback=progress_callback)
        elif op == "deinterlace":
            return helpers.deinterlace_video(str(in_path), out_file, progress_callback=progress_callback)
        elif op == "blackframe-detect":
            return helpers.detect_black_frames(str(in_path))
        elif op == "scene-preview":
            return helpers.generate_scene_preview(str(in_path), out_file, max_scenes=10)
        elif op == "scene-thumbnails":
            return helpers.extract_scene_thumbnails(str(in_path), out_file, width=640)
        return helpers.remux(str(in_path), out_file, progress_callback=progress_callback)

    task_id = queue.add_task(
        task_type=TaskType.GENERIC,
        name=f"Util: {body.operation}",
        execute_fn=_execute_util_task,
    )

    return {
        "task_id": task_id,
        "operation": body.operation,
        "output_file": out_file,
        "status": "queued",
    }
