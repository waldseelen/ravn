"""
RAVN CLI — Command-line interface for the RAVN media application.
Entry point: ravn_app.cli:cli
"""

import json
import os
import sys
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
from ravn_app.core.runners import FFmpegRunner
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
