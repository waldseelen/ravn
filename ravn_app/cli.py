"""
RAVN CLI — Command-line interface for the RAVN media application.
Entry point: ravn_app.cli:cli
"""

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from ravn_app.core.downloader import (
    DownloadFormat,
    DownloadQuality,
    DownloadResult,
    YouTubeDownloader,
)
from ravn_app.core.converter import (
    AudioCodec,
    CodecManager,
    ConversionSettings,
    VideoCodec,
    VideoConverter,
    VideoQuality,
)
from ravn_app.core.database import (
    ConversionRecord,
    DatabaseManager,
    DownloadRecord,
)
from ravn_app.core.i18n import get_i18n
from ravn_app.core.persistence.media_library import MediaLibrary, MediaSearchFilters
from ravn_app.core.runners import AudioMixerRunner, AudioTrack, FFmpegRunner, VideoMixerRunner
from ravn_app.core.subtitle_manager import SubtitleEmbedder
from ravn_app.core.torrent_downloader import TorrentDownloader, TorrentDownloadMode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLI_I18N = None


def _tr(key: str, **kwargs) -> str:
    global _CLI_I18N
    preferred_lang = str(os.environ.get("RAVN_LANG", "en")).strip().lower()
    if preferred_lang not in ("tr", "en"):
        preferred_lang = "en"

    if _CLI_I18N is None:
        _CLI_I18N = get_i18n(config_manager=None, default_lang=preferred_lang)
        _CLI_I18N.set_language(preferred_lang, persist=False)
    elif _CLI_I18N.language != preferred_lang:
        _CLI_I18N.set_language(preferred_lang, persist=False)

    return _CLI_I18N.t(key, **kwargs)


def _output(data: object, as_json: bool) -> None:
    """Print data as JSON or a human-readable string."""
    if as_json:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        if isinstance(data, str):
            click.echo(data)
        else:
            click.echo(json.dumps(data, indent=2, default=str))


def _error(message: str, as_json: bool) -> None:
    """Print an error and exit with code 1."""
    if as_json:
        click.echo(json.dumps({"success": False, "error": message}), err=True)
    else:
        click.echo(f"{_tr('cli.errorPrefix')}: {message}", err=True)
    sys.exit(1)


def _parse_csv_values(raw: Optional[str]) -> list[str]:
    return [item.strip() for item in str(raw or "").split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Quality / format mapping helpers
# ---------------------------------------------------------------------------

_QUALITY_MAP = {
    "360p": DownloadQuality.LOW_480P,   # closest available
    "480p": DownloadQuality.LOW_480P,
    "720p": DownloadQuality.MEDIUM_720P,
    "1080p": DownloadQuality.HIGH_1080P,
    "1440p": DownloadQuality.BEST,
    "2160p": DownloadQuality.BEST,
    "best": DownloadQuality.BEST,
}

_FORMAT_MAP = {
    "mp4": DownloadFormat.MP4,
    "webm": DownloadFormat.WEBM,
    "mkv": DownloadFormat.MKV,
    "mp3": DownloadFormat.MP3,
    "m4a": DownloadFormat.M4A,
}

_VIDEO_QUALITY_MAP = {
    "high": VideoQuality.HIGH,
    "medium": VideoQuality.MEDIUM,
    "low": VideoQuality.LOW,
}

_CODEC_MAP = {
    "h264": VideoCodec.H264,
    "h265": VideoCodec.H265,
    "vp9": VideoCodec.VP9,
    "av1": VideoCodec.AV1,
}


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version="1.0.0", prog_name="ravn")
def cli():
    """RAVN — Media download and conversion tool."""


# ---------------------------------------------------------------------------
# ravn download
# ---------------------------------------------------------------------------

@cli.command("download")
@click.argument("url")
@click.option(
    "--quality",
    default="best",
    type=click.Choice(["360p", "480p", "720p", "1080p", "1440p", "2160p", "best"],
                      case_sensitive=False),
    show_default=True,
    help="Download quality.",
)
@click.option(
    "--format", "fmt",
    default="mp4",
    type=click.Choice(["mp4", "webm", "mkv", "mp3", "m4a"], case_sensitive=False),
    show_default=True,
    help="Output format.",
)
@click.option(
    "--output",
    default=None,
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory (default: ~/Downloads/RAVN).",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def download_cmd(url: str, quality: str, fmt: str, output: Optional[Path], as_json: bool):
    """Download media from URL."""
    output_dir = output or Path.home() / "Downloads" / "RAVN"
    output_dir.mkdir(parents=True, exist_ok=True)

    dl_quality = _QUALITY_MAP[quality.lower()]
    dl_format = _FORMAT_MAP[fmt.lower()]

    if not as_json:
        click.echo(_tr("cli.downloadStarting", url=url))
        click.echo(_tr("cli.downloadStatus", quality=quality, format=fmt, output=str(output_dir)))

    def _progress(percent: int, status: str) -> None:
        if not as_json:
            click.echo(f"\r  {percent:3d}%  {status}", nl=False)

    downloader = YouTubeDownloader()
    try:
        result: DownloadResult = downloader.download(
            url=url,
            output_dir=str(output_dir),
            format_type=dl_format,
            quality=dl_quality,
            progress_callback=_progress,
        )
    except Exception as exc:
        _error(str(exc), as_json)

    if not as_json:
        click.echo()  # newline after progress

    if not result.success:
        _error(result.error_message or _tr("cli.downloadFailed"), as_json)

    # Persist to DB
    try:
        db = DatabaseManager()
        record = DownloadRecord(
            url=url,
            title=result.title or "",
            format=fmt,
            quality=quality,
            file_path=result.output_files[0] if result.output_files else "",
            download_date=datetime.now().isoformat(),
            status="completed",
            duration=result.duration,
        )
        db.add_download(record)
        db.close()
    except Exception:
        pass  # DB errors are non-fatal for CLI

    payload = {
        "success": True,
        "url": result.url,
        "files": result.output_files,
        "title": result.title,
        "duration": result.duration,
    }
    if as_json:
        _output(payload, as_json=True)
    else:
        click.echo(f"\n{_tr('cli.doneFiles', output=str(output_dir))}")
        for f in result.output_files:
            click.echo(f"  {f}")


# ---------------------------------------------------------------------------
# ravn convert
# ---------------------------------------------------------------------------

@cli.command("convert")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--format", "fmt",
    default="mp4",
    type=click.Choice(["mp4", "mkv", "webm", "avi", "mov"], case_sensitive=False),
    show_default=True,
    help="Output container format.",
)
@click.option(
    "--quality",
    default="medium",
    type=click.Choice(["high", "medium", "low"], case_sensitive=False),
    show_default=True,
    help="Encoding quality.",
)
@click.option(
    "--codec",
    default="h264",
    type=click.Choice(["h264", "h265", "vp9", "av1"], case_sensitive=False),
    show_default=True,
    help="Video codec.",
)
@click.option(
    "--output",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output file path (default: alongside input with new extension).",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def convert_cmd(
    file: Path,
    fmt: str,
    quality: str,
    codec: str,
    output: Optional[Path],
    as_json: bool,
):
    """Convert a media file to a different format."""
    video_codec = _CODEC_MAP[codec.lower()]
    video_quality = _VIDEO_QUALITY_MAP[quality.lower()]

    # Derive default codecs for the chosen format
    defaults = CodecManager.get_default_codecs(fmt.lower())
    audio_codec: AudioCodec = defaults.get("audio", AudioCodec.AAC)

    output_path: Path = output or file.with_suffix(f".{fmt.lower()}")

    if output_path == file:
        _error(_tr("cli.sameOutputError"), as_json)

    if not as_json:
        click.echo(_tr("cli.convertStarting", file=str(file)))
        click.echo(
            _tr(
                "cli.convertStatus",
                output=str(output_path),
                codec=codec.upper(),
                quality=quality,
            )
        )

    settings = ConversionSettings(
        input_file=str(file),
        output_file=str(output_path),
        video_codec=video_codec,
        audio_codec=audio_codec,
        video_quality=video_quality,
    )

    converter = VideoConverter()
    try:
        success = converter.convert(settings)
    except Exception as exc:
        _error(str(exc), as_json)

    if not success:
        _error(_tr("cli.conversionFailed"), as_json)

    # Persist to DB
    try:
        db = DatabaseManager()
        record = ConversionRecord(
            input_file=str(file),
            output_file=str(output_path),
            input_codec=file.suffix.lstrip("."),
            output_codec=codec,
            conversion_date=datetime.now().isoformat(),
            status="completed",
        )
        db.add_conversion(record)
        db.close()
    except Exception:
        pass

    payload = {
        "success": True,
        "input": str(file),
        "output": str(output_path),
        "codec": codec,
        "quality": quality,
        "format": fmt,
    }
    if as_json:
        _output(payload, as_json=True)
    else:
        click.echo(f"\n{_tr('cli.convertDone', output=str(output_path))}")


# ---------------------------------------------------------------------------
# ravn info
# ---------------------------------------------------------------------------

@cli.command("info")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def info_cmd(file: Path, as_json: bool):
    """Show media file metadata (duration, codec, resolution, bitrate)."""
    runner = FFmpegRunner()
    try:
        data = runner.probe(str(file))
    except Exception as exc:
        _error(str(exc), as_json)

    if data is None:
        _error(_tr("cli.probeFailed", file=str(file)), as_json)

    fmt_info = data.get("format", {})
    streams = data.get("streams", [])

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

    def _fmt_duration(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    duration_raw = float(fmt_info.get("duration", 0))
    bitrate_raw = int(fmt_info.get("bit_rate", 0))
    width = video_stream.get("width", 0)
    height = video_stream.get("height", 0)
    file_size = int(fmt_info.get("size", 0))

    fps_str = video_stream.get("r_frame_rate", "0/1")
    if "/" in fps_str:
        num, den = map(float, fps_str.split("/"))
        fps = num / den if den else 0.0
    else:
        fps = float(fps_str) if fps_str else 0.0

    payload = {
        "file": str(file),
        "duration": _fmt_duration(duration_raw),
        "duration_seconds": duration_raw,
        "resolution": f"{width}x{height}",
        "width": width,
        "height": height,
        "fps": round(fps, 3),
        "video_codec": video_stream.get("codec_name", "unknown"),
        "audio_codec": audio_stream.get("codec_name", "none"),
        "bitrate_kbps": round(bitrate_raw / 1000, 1),
        "file_size_bytes": file_size,
        "container": file.suffix.lstrip("."),
    }

    if as_json:
        _output(payload, as_json=True)
    else:
        label_width = 10
        click.echo(f"{_tr('cli.infoFile'):<{label_width}}: {payload['file']}")
        click.echo(f"{_tr('cli.infoDuration'):<{label_width}}: {payload['duration']}")
        click.echo(f"{_tr('cli.infoResolution'):<{label_width}}: {payload['resolution']}  @{payload['fps']} fps")
        click.echo(f"{_tr('cli.infoVideo'):<{label_width}}: {payload['video_codec']}")
        click.echo(f"{_tr('cli.infoAudio'):<{label_width}}: {payload['audio_codec']}")
        click.echo(f"{_tr('cli.infoBitrate'):<{label_width}}: {payload['bitrate_kbps']} kbps")
        click.echo(f"{_tr('cli.infoSize'):<{label_width}}: {file_size / (1024 * 1024):.2f} MB")
        click.echo(f"{_tr('cli.infoContainer'):<{label_width}}: {payload['container']}")


# ---------------------------------------------------------------------------
# ravn subtitle
# ---------------------------------------------------------------------------

@cli.command("subtitle")
@click.argument("video", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--embed",
    "subtitle_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Subtitle file to embed into the video.",
)
@click.option(
    "--output",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output file path (default: <video>_subtitled<ext>).",
)
@click.option(
    "--language",
    default="eng",
    show_default=True,
    help="Language code for the embedded subtitle track.",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def subtitle_cmd(
    video: Path,
    subtitle_file: Path,
    output: Optional[Path],
    language: str,
    as_json: bool,
):
    """Embed a subtitle file into a video."""
    output_path: Path = output or video.with_stem(video.stem + "_subtitled")

    if not as_json:
        click.echo(_tr("cli.subtitleEmbedding", subtitle=str(subtitle_file)))
        click.echo(_tr("cli.subtitleInto", video=str(video)))
        click.echo(_tr("cli.subtitleOutput", output=str(output_path)))

    embedder = SubtitleEmbedder()
    try:
        success = embedder.embed_soft(
            video_file=str(video),
            subtitle_file=str(subtitle_file),
            output_file=str(output_path),
            language=language,
        )
    except Exception as exc:
        _error(str(exc), as_json)

    if not success:
        _error(_tr("cli.subtitleEmbedFailed"), as_json)

    payload = {
        "success": True,
        "video": str(video),
        "subtitle": str(subtitle_file),
        "output": str(output_path),
        "language": language,
    }
    if as_json:
        _output(payload, as_json=True)
    else:
        click.echo(f"\n{_tr('cli.subtitleDone', output=str(output_path))}")


# ---------------------------------------------------------------------------
# ravn history
# ---------------------------------------------------------------------------

@cli.command("history")
@click.option("--limit", default=20, show_default=True, help="Number of records to show.")
@click.option(
    "--type", "record_type",
    default="all",
    type=click.Choice(["download", "convert", "all"], case_sensitive=False),
    show_default=True,
    help="Type of records to display.",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def history_cmd(limit: int, record_type: str, as_json: bool):
    """List recent download and conversion operations from the database."""
    try:
        db = DatabaseManager()
    except Exception as exc:
        _error(_tr("cli.dbOpenFail", error=str(exc)), as_json)

    records = []

    if record_type in ("download", "all"):
        try:
            downloads = db.get_downloads(limit=limit)
            for d in downloads:
                records.append({
                    "type": "download",
                    "id": d.id,
                    "url": d.url,
                    "title": d.title,
                    "format": d.format,
                    "quality": d.quality,
                    "file_path": d.file_path,
                    "date": d.download_date,
                    "status": d.status,
                })
        except Exception as exc:
            _error(_tr("cli.historyReadDownloadFail", error=str(exc)), as_json)

    if record_type in ("convert", "all"):
        try:
            conversions = db.get_conversions(limit=limit)
            for c in conversions:
                records.append({
                    "type": "conversion",
                    "id": c.id,
                    "input_file": c.input_file,
                    "output_file": c.output_file,
                    "input_codec": c.input_codec,
                    "output_codec": c.output_codec,
                    "date": c.conversion_date,
                    "status": c.status,
                })
        except Exception as exc:
            _error(_tr("cli.historyReadConversionFail", error=str(exc)), as_json)

    db.close()

    # Sort by date desc and trim to limit
    records.sort(key=lambda r: r.get("date") or "", reverse=True)
    records = records[:limit]

    if as_json:
        _output({"count": len(records), "records": records}, as_json=True)
    else:
        if not records:
            click.echo(_tr("cli.historyEmpty"))
            return
        for rec in records:
            if rec["type"] == "download":
                click.echo(_tr(
                    "cli.historyDownloadLine",
                    date=rec["date"],
                    typeLabel=_tr("cli.historyTypeDownload"),
                    title=rec.get("title") or rec["url"],
                    format=rec["format"],
                    quality=rec["quality"],
                    status=rec["status"],
                ))
            else:
                click.echo(_tr(
                    "cli.historyConversionLine",
                    date=rec["date"],
                    typeLabel=_tr("cli.historyTypeConversion"),
                    input=rec["input_file"],
                    output=rec["output_file"],
                    status=rec["status"],
                ))


# ---------------------------------------------------------------------------
# ravn torrent
# ---------------------------------------------------------------------------

@cli.command("torrent")
@click.argument("source")
@click.option(
    "--output-dir",
    default=None,
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory (default: ~/Downloads/RAVN).",
)
@click.option("--sequential", is_flag=True, default=False, help="Enable sequential (head-first) download.")
@click.option("--seed-time", default=0, show_default=True, help="Seed time in minutes after download (0 = no seeding).")
@click.option("--aria2c", "aria2c_path", default="aria2c", show_default=True, help="Path to aria2c executable.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def torrent_cmd(
    source: str,
    output_dir: Optional[Path],
    sequential: bool,
    seed_time: int,
    aria2c_path: str,
    as_json: bool,
):
    """Download a magnet link or .torrent file via aria2c."""
    downloader = TorrentDownloader(aria2c_path)

    if not downloader.is_available():
        _error(_tr("cli.torrentAria2Missing"), as_json)

    out = output_dir or Path.home() / "Downloads" / "RAVN"
    out.mkdir(parents=True, exist_ok=True)

    mode = TorrentDownloadMode.SEQUENTIAL if sequential else TorrentDownloadMode.FULL

    if not as_json:
        click.echo(_tr("cli.torrentSource", source=source))
        click.echo(_tr("cli.torrentOutputDir", output=str(out)))
        click.echo(_tr("cli.torrentMode", mode=mode.value, seedTime=seed_time))

    def _progress(percent: int, status: str) -> None:
        if not as_json:
            click.echo(f"\r  {percent:3d}%  {status}", nl=False)

    try:
        result = downloader.download(
            source=source,
            output_dir=str(out),
            mode=mode,
            progress_callback=_progress,
            seed_time=seed_time,
        )
    except Exception as exc:
        _error(str(exc), as_json)

    if not as_json:
        click.echo()

    if not result.success:
        _error(result.error_message or _tr("cli.torrentDownloadFailed"), as_json)

    payload = {
        "success": True,
        "source": result.source,
        "output_dir": str(out),
        "files": result.output_files,
    }
    if as_json:
        _output(payload, as_json=True)
    else:
        click.echo(f"\n{_tr('cli.doneFiles', output=str(out))}")
        for f in result.output_files:
            click.echo(f"  {f}")


# ---------------------------------------------------------------------------
# ravn mixer
# ---------------------------------------------------------------------------

@cli.group("mixer")
def mixer_group():
    """Mix and composite local audio/video files."""


@mixer_group.command("audio")
@click.option(
    "--input",
    "input_files",
    multiple=True,
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Input audio file(s). Repeat --input for multiple files.",
)
@click.option("--output", required=True, type=click.Path(dir_okay=False, path_type=Path), help="Output audio file.")
@click.option("--mix", "mix_mode", is_flag=True, default=False, help="Mix tracks together instead of concatenating sequentially.")
@click.option("--crossfade", default=0.0, show_default=True, type=float, help="Sequential crossfade duration in seconds.")
@click.option("--volume", multiple=True, type=float, help="Per-track volume for --mix mode. Repeat once per input.")
@click.option("--normalize/--no-normalize", default=False, help="Normalize the mixed audio loudness.")
@click.option("--sample-rate", default=None, type=int, help="Target sample rate for mix/concat output.")
@click.option("--bitrate", default=None, help="Target audio bitrate (for example 320k).")
@click.option("--trim-start", default=None, type=float, help="Trim start time in seconds (single input only).")
@click.option("--trim-duration", default=None, type=float, help="Trim duration in seconds (single input only).")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def mixer_audio_cmd(
    input_files: tuple[Path, ...],
    output: Path,
    mix_mode: bool,
    crossfade: float,
    volume: tuple[float, ...],
    normalize: bool,
    sample_rate: Optional[int],
    bitrate: Optional[str],
    trim_start: Optional[float],
    trim_duration: Optional[float],
    as_json: bool,
):
    """Run audio concat, mix, crossfade, or trim operations."""
    mixer = AudioMixerRunner()
    input_paths = [str(path) for path in input_files]

    if trim_start is not None or trim_duration is not None:
        if len(input_paths) != 1 or trim_start is None or trim_duration is None:
            _error("Audio trim requires exactly one input plus --trim-start and --trim-duration.", as_json)
        operation = "trim"
        result = mixer.trim(
            input_file=input_paths[0],
            output_file=str(output),
            start_time=trim_start,
            duration=trim_duration,
            bitrate=bitrate,
        )
    elif crossfade > 0:
        operation = "crossfade"
        result = mixer.crossfade(
            input_files=input_paths,
            output_file=str(output),
            duration=crossfade,
            bitrate=bitrate,
        )
    elif mix_mode:
        if volume and len(volume) != len(input_paths):
            _error("Provide one --volume value per --input when using --mix.", as_json)
        operation = "mix"
        volumes = list(volume) if volume else [1.0] * len(input_paths)
        tracks = [
            AudioTrack(file_path=path, volume=volumes[index])
            for index, path in enumerate(input_paths)
        ]
        result = mixer.mix(
            tracks=tracks,
            output_file=str(output),
            bitrate=bitrate,
            sample_rate=sample_rate,
            normalize=normalize,
        )
    else:
        operation = "concat"
        result = mixer.concat(
            input_files=input_paths,
            output_file=str(output),
            bitrate=bitrate,
            sample_rate=sample_rate,
        )

    if not result.success:
        _error(result.error_message or f"Audio {operation} failed", as_json)

    payload = {
        "success": True,
        "operation": operation,
        "inputs": input_paths,
        "output": str(output),
    }
    if as_json:
        _output(payload, as_json=True)
    else:
        click.echo(f"Audio {operation} complete: {output}")


@mixer_group.command("video")
@click.argument("inputs", nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--operation",
    default="concat",
    show_default=True,
    type=click.Choice(
        ["concat", "overlay", "pip", "side-by-side", "watermark", "transition", "replace-audio", "extract-frame"],
        case_sensitive=False,
    ),
    help="Video mix operation to perform.",
)
@click.option("--output", required=True, type=click.Path(dir_okay=False, path_type=Path), help="Output file path.")
@click.option("--position", default="top-right", show_default=True, help="Overlay/PiP/watermark position (name or x,y).")
@click.option("--scale", default=None, type=float, help="Overlay/PiP/watermark scale factor.")
@click.option("--opacity", default=1.0, show_default=True, type=float, help="Overlay opacity for overlay/watermark.")
@click.option("--orientation", default="horizontal", show_default=True, type=click.Choice(["horizontal", "vertical"], case_sensitive=False), help="Side-by-side layout orientation.")
@click.option("--transition-duration", default=1.0, show_default=True, type=float, help="Transition duration in seconds.")
@click.option("--timestamp", default=0.0, show_default=True, type=float, help="Frame extraction timestamp in seconds.")
@click.option("--codec", default=None, help="Override output video codec.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def mixer_video_cmd(
    inputs: tuple[Path, ...],
    operation: str,
    output: Path,
    position: str,
    scale: Optional[float],
    opacity: float,
    orientation: str,
    transition_duration: float,
    timestamp: float,
    codec: Optional[str],
    as_json: bool,
):
    """Run video concat, overlay, PiP, watermark, transition, or frame extraction operations."""
    runner = VideoMixerRunner()
    input_paths = [str(path) for path in inputs]
    normalized_operation = operation.lower()

    if normalized_operation == "concat":
        result = runner.concat(input_files=input_paths, output_file=str(output), reencode=False, video_codec=codec)
    elif normalized_operation == "overlay":
        if len(input_paths) != 2:
            _error("Overlay requires exactly two input files.", as_json)
        result = runner.overlay(
            base_file=input_paths[0],
            overlay_file=input_paths[1],
            output_file=str(output),
            position=position,
            scale=scale,
            opacity=opacity,
            video_codec=codec,
        )
    elif normalized_operation == "pip":
        if len(input_paths) != 2:
            _error("PiP requires exactly two input files.", as_json)
        result = runner.picture_in_picture(
            main_file=input_paths[0],
            pip_file=input_paths[1],
            output_file=str(output),
            position=position,
            scale=scale or 0.25,
            video_codec=codec,
        )
    elif normalized_operation == "side-by-side":
        if len(input_paths) != 2:
            _error("Side-by-side requires exactly two input files.", as_json)
        result = runner.side_by_side(
            left_file=input_paths[0],
            right_file=input_paths[1],
            output_file=str(output),
            orientation=orientation,
            video_codec=codec,
        )
    elif normalized_operation == "watermark":
        if len(input_paths) != 2:
            _error("Watermark requires exactly two input files.", as_json)
        result = runner.watermark(
            video_file=input_paths[0],
            watermark_file=input_paths[1],
            output_file=str(output),
            position=position,
            scale=scale,
            opacity=opacity,
            video_codec=codec,
        )
    elif normalized_operation == "transition":
        if len(input_paths) != 2:
            _error("Transition requires exactly two input files.", as_json)
        result = runner.transition(
            first_file=input_paths[0],
            second_file=input_paths[1],
            output_file=str(output),
            duration=transition_duration,
            video_codec=codec,
        )
    elif normalized_operation == "replace-audio":
        if len(input_paths) != 2:
            _error("replace-audio requires exactly one video input and one audio input.", as_json)
        result = runner.replace_audio(
            video_file=input_paths[0],
            audio_file=input_paths[1],
            output_file=str(output),
        )
    elif normalized_operation == "extract-frame":
        if len(input_paths) != 1:
            _error("extract-frame requires exactly one input file.", as_json)
        result = runner.extract_frame(input_file=input_paths[0], output_file=str(output), timestamp=timestamp)
    else:
        _error(f"Unsupported video mixer operation: {operation}", as_json)
        return

    if not result.success:
        _error(result.error_message or f"Video {normalized_operation} failed", as_json)

    payload = {
        "success": True,
        "operation": normalized_operation,
        "inputs": input_paths,
        "output": str(output),
    }
    if as_json:
        _output(payload, as_json=True)
    else:
        click.echo(f"Video {normalized_operation} complete: {output}")


# ---------------------------------------------------------------------------
# ravn library
# ---------------------------------------------------------------------------

@cli.group("library")
def library_group():
    """Manage the Phase 7 local media library database."""


@library_group.command("add")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--title", default=None, help="Override the detected media title.")
@click.option("--tags", default="", help="Comma-separated tags to attach.")
@click.option("--thumbnail", default=None, help="Optional thumbnail path.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def library_add_cmd(file: Path, title: Optional[str], tags: str, thumbnail: Optional[str], as_json: bool):
    """Add a local file to the media library."""
    library = MediaLibrary()
    try:
        media_id = library.add_media(
            file_path=str(file),
            title=title,
            tags=_parse_csv_values(tags),
            thumbnail=thumbnail,
        )
    except Exception as exc:
        library.close()
        _error(str(exc), as_json)
    payload = {"success": True, "id": media_id, "file": str(file), "tags": _parse_csv_values(tags)}
    library.close()
    if as_json:
        _output(payload, as_json=True)
    else:
        click.echo(f"Added media item #{media_id}: {file}")


@library_group.command("search")
@click.option("--query", default="", help="Text search query.")
@click.option("--format", "fmt", default=None, help="Filter by container/format.")
@click.option("--tags", default="", help="Comma-separated tag filter (OR logic).")
@click.option("--duration-min", default=None, type=float, help="Minimum duration in seconds.")
@click.option("--duration-max", default=None, type=float, help="Maximum duration in seconds.")
@click.option("--size-min", default=None, type=int, help="Minimum file size in bytes.")
@click.option("--size-max", default=None, type=int, help="Maximum file size in bytes.")
@click.option("--sort", "sort_by", default="added_at", show_default=True, type=click.Choice(["added_at", "date", "size", "duration", "name", "title"], case_sensitive=False), help="Sort key.")
@click.option("--ascending", is_flag=True, default=False, help="Sort ascending instead of descending.")
@click.option("--limit", default=100, show_default=True, type=int, help="Maximum results to return.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def library_search_cmd(
    query: str,
    fmt: Optional[str],
    tags: str,
    duration_min: Optional[float],
    duration_max: Optional[float],
    size_min: Optional[int],
    size_max: Optional[int],
    sort_by: str,
    ascending: bool,
    limit: int,
    as_json: bool,
):
    """Search the local media library."""
    library = MediaLibrary()
    filters = MediaSearchFilters(
        format=fmt,
        duration_min=duration_min,
        duration_max=duration_max,
        size_min=size_min,
        size_max=size_max,
        tags=_parse_csv_values(tags),
        sort_by=sort_by,
        sort_desc=not ascending,
        limit=limit,
    )
    items = library.search_media(query=query, filters=filters)
    payload = {"count": len(items), "items": [asdict(item) for item in items]}
    library.close()
    if as_json:
        _output(payload, as_json=True)
    else:
        if not items:
            click.echo("No media items matched the current search.")
            return
        for item in items:
            click.echo(f"[{item.id}] {item.title} ({item.format}, {item.duration:.1f}s, {item.size} bytes)")


@library_group.command("create-collection")
@click.option("--name", required=True, help="Collection name.")
@click.option("--description", default="", help="Optional description.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def library_create_collection_cmd(name: str, description: str, as_json: bool):
    """Create a new collection."""
    library = MediaLibrary()
    try:
        collection_id = library.create_collection(name=name, description=description)
    except Exception as exc:
        library.close()
        _error(str(exc), as_json)
    payload = {"success": True, "id": collection_id, "name": name}
    library.close()
    if as_json:
        _output(payload, as_json=True)
    else:
        click.echo(f"Created collection #{collection_id}: {name}")


@library_group.command("add-to-collection")
@click.argument("media_id", type=int)
@click.argument("collection_id", type=int)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def library_add_to_collection_cmd(media_id: int, collection_id: int, as_json: bool):
    """Add a media item to a collection."""
    library = MediaLibrary()
    success = library.add_to_collection(media_id=media_id, collection_id=collection_id)
    library.close()
    if not success:
        _error("Could not add media item to the collection.", as_json)
    payload = {"success": True, "media_id": media_id, "collection_id": collection_id}
    if as_json:
        _output(payload, as_json=True)
    else:
        click.echo(f"Added media item #{media_id} to collection #{collection_id}")


@library_group.command("stats")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def library_stats_cmd(as_json: bool):
    """Show library statistics."""
    library = MediaLibrary()
    stats = library.get_statistics()
    library.close()
    if as_json:
        _output(stats, as_json=True)
    else:
        click.echo(f"Items: {stats['total_items']}")
        click.echo(f"Size : {stats['total_size']} bytes")
        click.echo(f"Duration: {stats['total_duration']:.1f}s")
        click.echo(f"Collections: {stats['collections']}")
        click.echo(f"Duplicate groups: {stats['duplicate_groups']}")


@library_group.command("export")
@click.option("--format", "export_format", required=True, type=click.Choice(["json", "csv"], case_sensitive=False), help="Export format.")
@click.option("--output", required=True, type=click.Path(dir_okay=False, path_type=Path), help="Export output file.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def library_export_cmd(export_format: str, output: Path, as_json: bool):
    """Export the media library to JSON or CSV."""
    library = MediaLibrary()
    try:
        success = library.export_library(export_format=export_format, output_file=str(output))
    except Exception as exc:
        library.close()
        _error(str(exc), as_json)
    library.close()
    if not success:
        _error("Library export failed.", as_json)
    payload = {"success": True, "format": export_format.lower(), "output": str(output)}
    if as_json:
        _output(payload, as_json=True)
    else:
        click.echo(f"Library exported to: {output}")


# ---------------------------------------------------------------------------
# ravn filters
# ---------------------------------------------------------------------------

@cli.command("filters")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--brightness", default=None, type=float, help="Brightness adjustment (-1..1 or percentage).")
@click.option("--contrast", default=None, type=float, help="Contrast multiplier.")
@click.option("--saturation", default=None, type=float, help="Saturation multiplier.")
@click.option("--hue", default=None, type=float, help="Hue rotation in degrees.")
@click.option("--gamma", default=None, type=float, help="Gamma correction value.")
@click.option("--crop-left", default=0, show_default=True, type=int, help="Pixels to crop from the left.")
@click.option("--crop-top", default=0, show_default=True, type=int, help="Pixels to crop from the top.")
@click.option("--crop-right", default=0, show_default=True, type=int, help="Pixels to crop from the right.")
@click.option("--crop-bottom", default=0, show_default=True, type=int, help="Pixels to crop from the bottom.")
@click.option("--rotate", default=None, type=float, help="Rotation in degrees.")
@click.option("--flip-horizontal", is_flag=True, default=False, help="Flip the video horizontally.")
@click.option("--flip-vertical", is_flag=True, default=False, help="Flip the video vertically.")
@click.option("--blur", default=None, type=float, help="Gaussian blur strength.")
@click.option("--sharpen", default=None, type=float, help="Sharpen strength.")
@click.option("--denoise", default=None, type=click.Choice(["light", "moderate", "strong", "ultra"], case_sensitive=False), help="Denoise preset.")
@click.option("--grayscale", is_flag=True, default=False, help="Convert output to grayscale.")
@click.option("--sepia", is_flag=True, default=False, help="Apply a sepia tone.")
@click.option("--invert", is_flag=True, default=False, help="Invert video colors.")
@click.option("--deinterlace", is_flag=True, default=False, help="Apply yadif deinterlacing.")
@click.option("--lut", "lut_file", default=None, type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Optional LUT (.cube/.3dl) file.")
@click.option("--codec", default=None, help="Override output video codec.")
@click.option("--bitrate", default=None, help="Target video bitrate (for example 6M).")
@click.option("--output", required=True, type=click.Path(dir_okay=False, path_type=Path), help="Filtered output file path.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def filters_cmd(
    file: Path,
    brightness: Optional[float],
    contrast: Optional[float],
    saturation: Optional[float],
    hue: Optional[float],
    gamma: Optional[float],
    crop_left: int,
    crop_top: int,
    crop_right: int,
    crop_bottom: int,
    rotate: Optional[float],
    flip_horizontal: bool,
    flip_vertical: bool,
    blur: Optional[float],
    sharpen: Optional[float],
    denoise: Optional[str],
    grayscale: bool,
    sepia: bool,
    invert: bool,
    deinterlace: bool,
    lut_file: Optional[Path],
    codec: Optional[str],
    bitrate: Optional[str],
    output: Path,
    as_json: bool,
):
    """Apply FFmpeg-based video filters to a local file."""
    runner = VideoMixerRunner()
    result = runner.apply_filters(
        input_file=str(file),
        output_file=str(output),
        brightness=brightness,
        contrast=contrast,
        saturation=saturation,
        hue=hue,
        gamma=gamma,
        crop_left=crop_left,
        crop_top=crop_top,
        crop_right=crop_right,
        crop_bottom=crop_bottom,
        rotate=rotate,
        flip_horizontal=flip_horizontal,
        flip_vertical=flip_vertical,
        blur=blur,
        sharpen=sharpen,
        denoise=denoise,
        grayscale=grayscale,
        sepia=sepia,
        invert=invert,
        deinterlace=deinterlace,
        lut_file=str(lut_file) if lut_file else None,
        video_codec=codec,
        bitrate=bitrate,
    )
    if not result.success:
        _error(result.error_message or "Video filters failed", as_json)

    payload = {
        "success": True,
        "input": str(file),
        "output": str(output),
        "filters": result.metadata.get("filters", []),
    }
    if as_json:
        _output(payload, as_json=True)
    else:
        click.echo(f"Filtered video written to: {output}")


# ---------------------------------------------------------------------------
# ravn serve  (placeholder)
# ---------------------------------------------------------------------------

@cli.command("serve")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def serve_cmd(as_json: bool):
    """Start the REST API server (not yet implemented)."""
    message = _tr("cli.serveNotImplemented")
    if as_json:
        _output({"success": False, "message": message}, as_json=True)
    else:
        click.echo(message)


# ---------------------------------------------------------------------------
# Entry-point guard
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
