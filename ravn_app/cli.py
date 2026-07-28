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
from click.core import ParameterSource

from ravn_app import __version__
from ravn_app.core import tool_installer
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
from ravn_app.core.download_profiles import apply_profile_overrides, get_download_profile, resolve_profile_output_dir
from ravn_app.core.downloader import (
    DownloadFormat,
    DownloadQuality,
    DownloadResult,
    YouTubeDownloader,
)
from ravn_app.core.i18n import get_i18n
from ravn_app.core.media_helpers import get_media_helpers
from ravn_app.core.persistence.media_library import MediaLibrary, MediaSearchFilters
from ravn_app.core.runners import AudioMixerRunner, AudioTrack, FFmpegRunner, VideoMixerRunner
from ravn_app.core.subtitle_manager import SubtitleEmbedder
from ravn_app.core.tool_health import check_tool_availability, get_tool_health_checker
from ravn_app.core.torrent_downloader import TorrentDownloader, TorrentDownloadMode
from ravn_app.utils import bundled_tools
from ravn_app.utils.bundled_tools import configure_bundled_tools_path
from ravn_app.utils.ffmpeg_checker import configure_ffmpeg_runtime

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


def _option_was_provided(ctx: click.Context, name: str) -> bool:
    try:
        return ctx.get_parameter_source(name) not in {ParameterSource.DEFAULT, ParameterSource.DEFAULT_MAP}
    except Exception:
        return False


def _check_required_tools(tools: list[str], as_json: bool = False) -> None:
    """Check if required tools are available, exit with error if not."""
    checker = get_tool_health_checker()
    missing = []

    for tool in tools:
        if not check_tool_availability(tool):
            missing.append(tool)

    if missing:
        affected_features = set()
        for tool in missing:
            features = checker.get_affected_features(tool)
            affected_features.update(features)

        error_msg = f"Required tools missing: {', '.join(missing)}. "
        error_msg += f"This affects: {', '.join(affected_features)}. "
        error_msg += "Please install missing tools. See DEPENDENCIES.md for instructions."

        _error(error_msg, as_json)


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
    "aac": DownloadFormat.AAC,
    "flac": DownloadFormat.FLAC,
    "opus": DownloadFormat.OPUS,
    "wav": DownloadFormat.WAV,
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

_AUDIO_FORMAT_KEYS = {"mp3", "m4a", "aac", "flac", "opus", "wav"}
_PROFILE_CHOICES = ["custom", "music", "podcast", "archive", "social-clip"]
_NAMING_PRESET_CHOICES = ["standard", "clean", "playlist"]
_SUBTITLE_FALLBACK_CHOICES = ["none", "tr", "en", "de", "fr", "es"]
_AUDIO_BITRATE_CHOICES = ["best", "320k", "192k", "128k"]
_POSTPROCESS_AUDIO_FORMAT_CHOICES = ["mp3", "m4a", "aac", "flac", "opus", "wav"]
_POSTPROCESS_CONVERT_CHOICES = ["mp4", "mkv", "webm", "mp3", "m4a", "aac", "flac", "opus"]
_COOKIES_BROWSER_CHOICES = ["chrome", "firefox", "edge", "safari", "brave", "chromium", "opera"]


def _normalize_profile_key(value: str) -> str:
    return str(value or "custom").strip().lower().replace("-", "_")


def _quality_from_profile_label(label: str) -> DownloadQuality:
    normalized = str(label or "").strip().lower()
    if normalized in {"sadece ses", "audio only"}:
        return DownloadQuality.AUDIO_ONLY
    if normalized in {"1080p"}:
        return DownloadQuality.HIGH_1080P
    if normalized in {"720p"}:
        return DownloadQuality.MEDIUM_720P
    if normalized in {"480p", "360p"}:
        return DownloadQuality.LOW_480P
    return DownloadQuality.BEST


def _quality_label_for_payload(value: DownloadQuality) -> str:
    labels = {
        DownloadQuality.BEST: "best",
        DownloadQuality.HIGH_1080P: "1080p",
        DownloadQuality.MEDIUM_720P: "720p",
        DownloadQuality.LOW_480P: "480p",
        DownloadQuality.AUDIO_ONLY: "audio-only",
    }
    return labels.get(value, "best")


def _format_key_for_payload(value: DownloadFormat) -> str:
    return value.extension.lower()


def _audio_bitrate_for_download(value: str) -> str:
    normalized = str(value or "best").strip().lower()
    if normalized == "best":
        return "0"
    return normalized.upper()


def _resolve_download_cli_settings(
    ctx: click.Context,
    *,
    profile_key: str,
    quality: str,
    fmt: str,
    output: Optional[Path],
    audio_bitrate: str,
    naming_preset: str,
    filename_template: str,
    subtitle_lang: Optional[str],
    subtitle_fallback: str,
    include_auto_generated: bool,
    auto_embed_subtitles: bool,
    extract_audio: bool,
    extract_audio_format: str,
    postprocess_audio_bitrate: str,
    convert_to: Optional[str],
    postprocess_embed_subtitles: bool,
    enable_archive: bool,
    detect_duplicates: bool,
    continue_partial: bool,
    format_fallback: bool,
    rate_limit_kbps: int,
    cookies_from_browser: Optional[str],
    cookies_profile: str,
    cookies_file: Optional[Path],
    concurrent_fragments: int,
    fragment_retries: int,
    socket_timeout: int,
) -> tuple[str, DownloadFormat, DownloadQuality, dict[str, object], str]:
    profile = get_download_profile(profile_key)
    base_output_dir = output or Path.home() / "Downloads" / "RAVN"
    effective_output_dir = Path(resolve_profile_output_dir(str(base_output_dir), profile))
    effective_output_dir.mkdir(parents=True, exist_ok=True)

    effective_format_key = profile.format_key.lower() if profile.format_key else fmt.lower()
    if _option_was_provided(ctx, "fmt"):
        effective_format_key = fmt.lower()
    format_type = _FORMAT_MAP[effective_format_key]

    if format_type.extension.lower() in _AUDIO_FORMAT_KEYS:
        effective_quality = DownloadQuality.AUDIO_ONLY
    else:
        effective_quality = _quality_from_profile_label(profile.quality_label)
        if _option_was_provided(ctx, "quality"):
            effective_quality = _QUALITY_MAP[quality.lower()]
        elif profile.key == "custom":
            effective_quality = _QUALITY_MAP[quality.lower()]

    preferred_subtitle_language = subtitle_lang or profile.preferred_subtitle_language or "tr"
    if not _option_was_provided(ctx, "subtitle_lang") and profile.key == "custom":
        preferred_subtitle_language = subtitle_lang or "tr"

    settings: dict[str, object] = {
        "embed_metadata": True,
        "embed_lyrics": True,
        "auto_sort_enabled": False,
        "auto_sort_mode": "artist",
        "auto_subtitle_download": False,
        "preferred_subtitle_language": preferred_subtitle_language,
        "subtitle_fallback_language": subtitle_fallback,
        "subtitle_include_auto_generated": include_auto_generated,
        "auto_embed_subtitles": auto_embed_subtitles,
        "naming_preset": naming_preset,
        "filename_template": filename_template.strip(),
        "postprocess_profile": {
            "extract_audio": extract_audio,
            "audio_format": extract_audio_format,
            "audio_bitrate": postprocess_audio_bitrate,
            "convert_enabled": bool(convert_to),
            "convert_format": str(convert_to or ""),
            "embed_subtitles": postprocess_embed_subtitles,
        },
        "robustness_profile": {
            "enable_archive": enable_archive,
            "detect_duplicates": detect_duplicates,
            "continue_partial": continue_partial,
            "format_fallback": format_fallback,
            "rate_limit_kbps": max(0, int(rate_limit_kbps or 0)),
        },
        "advanced_profile": {
            "cookies_mode": "none",
            "cookies_browser": "chrome",
            "cookies_profile": cookies_profile.strip(),
            "cookies_file": str(cookies_file) if cookies_file else "",
            "concurrent_fragments": max(1, int(concurrent_fragments or 1)),
            "fragment_retries": max(0, int(fragment_retries or 0)),
            "socket_timeout_seconds": max(0, int(socket_timeout or 0)),
        },
    }

    settings = apply_profile_overrides(settings, profile)

    if _option_was_provided(ctx, "naming_preset"):
        settings["naming_preset"] = naming_preset
    if _option_was_provided(ctx, "filename_template"):
        settings["filename_template"] = filename_template.strip()
    if _option_was_provided(ctx, "subtitle_lang"):
        settings["preferred_subtitle_language"] = subtitle_lang or "tr"
    if _option_was_provided(ctx, "subtitle_fallback"):
        settings["subtitle_fallback_language"] = subtitle_fallback
    if _option_was_provided(ctx, "include_auto_generated"):
        settings["subtitle_include_auto_generated"] = include_auto_generated
    if _option_was_provided(ctx, "auto_embed_subtitles"):
        settings["auto_embed_subtitles"] = auto_embed_subtitles
    if _option_was_provided(ctx, "extract_audio"):
        settings["postprocess_profile"]["extract_audio"] = extract_audio
    if _option_was_provided(ctx, "extract_audio_format"):
        settings["postprocess_profile"]["audio_format"] = extract_audio_format
    if _option_was_provided(ctx, "postprocess_audio_bitrate"):
        settings["postprocess_profile"]["audio_bitrate"] = postprocess_audio_bitrate
    if _option_was_provided(ctx, "convert_to"):
        settings["postprocess_profile"]["convert_enabled"] = bool(convert_to)
        settings["postprocess_profile"]["convert_format"] = str(convert_to or "")
    if _option_was_provided(ctx, "postprocess_embed_subtitles"):
        settings["postprocess_profile"]["embed_subtitles"] = postprocess_embed_subtitles

    if cookies_from_browser and cookies_file:
        raise click.ClickException("Choose either --cookies-from-browser or --cookies-file, not both.")
    if cookies_profile and not cookies_from_browser:
        raise click.ClickException("--cookies-profile requires --cookies-from-browser.")
    if cookies_from_browser:
        settings["advanced_profile"].update(
            {
                "cookies_mode": "browser",
                "cookies_browser": cookies_from_browser,
                "cookies_profile": cookies_profile.strip(),
                "cookies_file": "",
            }
        )
    elif cookies_file:
        settings["advanced_profile"].update(
            {
                "cookies_mode": "file",
                "cookies_file": str(cookies_file),
                "cookies_profile": "",
            }
        )

    effective_audio_bitrate = profile.audio_bitrate or _audio_bitrate_for_download(audio_bitrate)
    if _option_was_provided(ctx, "audio_bitrate"):
        effective_audio_bitrate = _audio_bitrate_for_download(audio_bitrate)
    if format_type.extension.lower() in _AUDIO_FORMAT_KEYS:
        settings["audio_bitrate"] = effective_audio_bitrate

    summary = {
        "profile": profile.key,
        "format": _format_key_for_payload(format_type),
        "quality": _quality_label_for_payload(effective_quality),
        "output_dir": str(effective_output_dir),
        "naming_preset": settings.get("naming_preset"),
        "filename_template": settings.get("filename_template") or "",
        "postprocess_profile": settings.get("postprocess_profile"),
        "robustness_profile": settings.get("robustness_profile"),
        "advanced_profile": settings.get("advanced_profile"),
    }
    return str(effective_output_dir), format_type, effective_quality, settings, json.dumps(summary, default=str)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version=__version__, prog_name="ravn")
def cli():
    """RAVN — Media download and conversion tool."""
    # Same bundled-tool resolution the desktop app does, so the packaged CLI works
    # from a freshly unzipped build without anything installed system-wide.
    configure_bundled_tools_path()
    configure_ffmpeg_runtime()


# ---------------------------------------------------------------------------
# ravn download
# ---------------------------------------------------------------------------

@cli.command("download")
@click.argument("url")
@click.option(
    "--profile",
    default="custom",
    type=click.Choice(_PROFILE_CHOICES, case_sensitive=False),
    show_default=True,
    help="Acquisition preset (custom, music, podcast, archive, social-clip).",
)
@click.option(
    "--quality",
    default="best",
    type=click.Choice(["360p", "480p", "720p", "1080p", "1440p", "2160p", "best"], case_sensitive=False),
    show_default=True,
    help="Preferred quality override for video-oriented presets.",
)
@click.option(
    "--format", "fmt",
    default="mp4",
    type=click.Choice(list(_FORMAT_MAP.keys()), case_sensitive=False),
    show_default=True,
    help="Preferred output format override.",
)
@click.option(
    "--audio-bitrate",
    default="best",
    type=click.Choice(_AUDIO_BITRATE_CHOICES, case_sensitive=False),
    show_default=True,
    help="Downloader audio bitrate intent for audio-only outputs.",
)
@click.option(
    "--naming-preset",
    default="standard",
    type=click.Choice(_NAMING_PRESET_CHOICES, case_sensitive=False),
    show_default=True,
    help="Naming preset used by the post-download naming pipeline.",
)
@click.option("--filename-template", default="", help="Optional filename template override, e.g. {playlist}/{title}.")
@click.option("--subtitle-lang", default=None, help="Preferred subtitle language for downloader automation.")
@click.option(
    "--subtitle-fallback",
    default="en",
    type=click.Choice(_SUBTITLE_FALLBACK_CHOICES, case_sensitive=False),
    show_default=True,
    help="Fallback subtitle language (use 'none' to disable fallback).",
)
@click.option("--include-auto-generated/--no-include-auto-generated", default=True, show_default=True, help="Allow auto-generated subtitles as downloader fallback.")
@click.option("--auto-embed-subtitles/--no-auto-embed-subtitles", default=False, show_default=True, help="Ask yt-dlp to embed subtitles during supported video downloads.")
@click.option("--extract-audio", is_flag=True, default=False, help="Run post-download audio extraction after acquisition.")
@click.option(
    "--extract-audio-format",
    default="mp3",
    type=click.Choice(_POSTPROCESS_AUDIO_FORMAT_CHOICES, case_sensitive=False),
    show_default=True,
    help="Target format for the post-download extract-audio step.",
)
@click.option(
    "--postprocess-audio-bitrate",
    default="192k",
    type=click.Choice(["128k", "192k", "320k"], case_sensitive=False),
    show_default=True,
    help="Audio bitrate used by post-download extract/convert steps.",
)
@click.option(
    "--convert-to",
    default=None,
    type=click.Choice(_POSTPROCESS_CONVERT_CHOICES, case_sensitive=False),
    help="Optional final conversion target after download.",
)
@click.option("--postprocess-embed-subtitles/--no-postprocess-embed-subtitles", default=False, show_default=True, help="Embed matching subtitle sidecars during the FFmpeg post-process pipeline.")
@click.option("--archive/--no-archive", "enable_archive", default=True, show_default=True, help="Track completed downloads in the shared archive.")
@click.option("--detect-duplicates/--no-detect-duplicates", default=True, show_default=True, help="Skip items already present in the shared archive.")
@click.option("--continue-partial/--no-continue-partial", default=True, show_default=True, help="Resume partial downloads when possible.")
@click.option("--format-fallback/--no-format-fallback", default=True, show_default=True, help="Retry with fallback format specs before failing.")
@click.option("--rate-limit-kbps", default=0, type=int, show_default=True, help="Optional bandwidth limit in KB/s (0 = unlimited).")
@click.option("--cookies-from-browser", default=None, type=click.Choice(_COOKIES_BROWSER_CHOICES, case_sensitive=False), help="Load authenticated cookies from a supported browser.")
@click.option("--cookies-profile", default="", help="Optional browser profile/container name used with --cookies-from-browser.")
@click.option("--cookies-file", default=None, type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Use an exported cookies.txt file for authenticated sources.")
@click.option("--concurrent-fragments", default=1, type=int, show_default=True, help="Concurrent fragment downloads for segmented sources.")
@click.option("--fragment-retries", default=0, type=int, show_default=True, help="Retry count for fragment failures.")
@click.option("--socket-timeout", default=0, type=int, show_default=True, help="Socket timeout in seconds (0 = default).")
@click.option(
    "--output",
    default=None,
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory base (profile subfolders still apply).",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
@click.option("--dry-run", is_flag=True, default=False, help="Print intent and skip actual download.")
@click.pass_context
def download_cmd(
    ctx: click.Context,
    url: str,
    profile: str,
    quality: str,
    fmt: str,
    audio_bitrate: str,
    naming_preset: str,
    filename_template: str,
    subtitle_lang: Optional[str],
    subtitle_fallback: str,
    include_auto_generated: bool,
    auto_embed_subtitles: bool,
    extract_audio: bool,
    extract_audio_format: str,
    postprocess_audio_bitrate: str,
    convert_to: Optional[str],
    postprocess_embed_subtitles: bool,
    enable_archive: bool,
    detect_duplicates: bool,
    continue_partial: bool,
    format_fallback: bool,
    rate_limit_kbps: int,
    cookies_from_browser: Optional[str],
    cookies_profile: str,
    cookies_file: Optional[Path],
    concurrent_fragments: int,
    fragment_retries: int,
    socket_timeout: int,
    output: Optional[Path],
    as_json: bool,
    dry_run: bool,
):
    """Download media from URL using intent-driven acquisition settings."""
    # Check required tools
    _check_required_tools(['yt-dlp'], as_json)

    try:
        output_dir, dl_format, dl_quality, download_settings, summary_json = _resolve_download_cli_settings(
            ctx,
            profile_key=_normalize_profile_key(profile),
            quality=quality,
            fmt=fmt,
            output=output,
            audio_bitrate=audio_bitrate,
            naming_preset=naming_preset,
            filename_template=filename_template,
            subtitle_lang=subtitle_lang,
            subtitle_fallback=subtitle_fallback,
            include_auto_generated=include_auto_generated,
            auto_embed_subtitles=auto_embed_subtitles,
            extract_audio=extract_audio,
            extract_audio_format=extract_audio_format,
            postprocess_audio_bitrate=postprocess_audio_bitrate,
            convert_to=convert_to.lower() if convert_to else None,
            postprocess_embed_subtitles=postprocess_embed_subtitles,
            enable_archive=enable_archive,
            detect_duplicates=detect_duplicates,
            continue_partial=continue_partial,
            format_fallback=format_fallback,
            rate_limit_kbps=rate_limit_kbps,
            cookies_from_browser=cookies_from_browser.lower() if cookies_from_browser else None,
            cookies_profile=cookies_profile,
            cookies_file=cookies_file,
            concurrent_fragments=concurrent_fragments,
            fragment_retries=fragment_retries,
            socket_timeout=socket_timeout,
        )
    except click.ClickException as exc:
        _error(exc.message, as_json)

    if not as_json:
        click.echo(_tr("cli.downloadStarting", url=url))
        click.echo(_tr("cli.downloadStatus", quality=_quality_label_for_payload(dl_quality), format=_format_key_for_payload(dl_format), output=str(output_dir)))
        click.echo(f"  preset: {_normalize_profile_key(profile)}")

    if dry_run:
        if as_json:
            _output(json.loads(summary_json), as_json=True)
        else:
            click.echo("\n--- DRY RUN SUMMARY ---")
            _output(json.loads(summary_json), as_json=False)
        return

    def _progress(percent: int, status: str) -> None:
        if not as_json:
            click.echo(f"\r  {percent:3d}%  {status}", nl=False)

    downloader = YouTubeDownloader()
    try:
        from ravn_app.core.downloader import DownloadRequest
        req = DownloadRequest(
            url=url,
            output_dir=str(output_dir),
            format=dl_format,
            quality=dl_quality,
            progress_callback=_progress,
            **download_settings,
        )
        result: DownloadResult = downloader.download(req)
    except Exception as exc:
        _error(str(exc), as_json)

    if not as_json:
        click.echo()

    if not result.success:
        _error(result.error_message or _tr("cli.downloadFailed"), as_json)

    try:
        db = DatabaseManager()
        record = DownloadRecord(
            url=url,
            title=result.title or "",
            format=_format_key_for_payload(dl_format),
            quality=_quality_label_for_payload(dl_quality),
            file_path=result.output_files[0] if result.output_files else "",
            download_date=datetime.now().isoformat(),
            status="completed",
            duration=result.duration,
        )
        db.add_download(record)
        db.close()
    except Exception:
        pass

    payload = {
        "success": True,
        "url": result.url,
        "files": result.output_files,
        "title": result.title,
        "duration": result.duration,
        "profile": _normalize_profile_key(profile),
        "effective": json.loads(summary_json),
        "metadata": getattr(result, "metadata", {}) or {},
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
    # Check required tools
    _check_required_tools(['ffmpeg'], as_json)

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
    # Check required tools
    _check_required_tools(['ffprobe'], as_json)

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
    _check_required_tools(['ffmpeg'], as_json)
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
    _check_required_tools(['ffmpeg'], as_json)
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
    _check_required_tools(['ffmpeg'], as_json)
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
    _check_required_tools(['ffmpeg'], as_json)
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
# ravn utilities  - Quick media helpers
# ---------------------------------------------------------------------------

@cli.command("utilities")
@click.option("--operation", "-o", required=True,
              type=click.Choice(["remux", "extract-audio", "mute", "trim", "preview", "thumbnail",
                                "volume", "fade", "bitrate", "channels", "silence-detect", "loudnorm",
                                "scale", "crop", "pad", "rotate", "fps", "color", "blur", "deinterlace",
                                "blackdetect", "scene-preview", "scene-thumbnail"], case_sensitive=False),
              help="Utility operation to perform")
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--output", "-out", type=click.Path(dir_okay=False, path_type=Path), help="Output file path")
@click.option("--start", type=float, help="Start time in seconds (for trim/preview)")
@click.option("--end", type=float, help="End time in seconds (for trim)")
@click.option("--duration", "-d", type=float, help="Duration in seconds (for trim/preview/fade)")
@click.option("--volume", type=float, help="Volume adjustment in dB")
@click.option("--fade-in", type=float, help="Fade in duration in seconds")
@click.option("--fade-out", type=float, help="Fade out duration in seconds")
@click.option("--bitrate", type=str, help="Audio bitrate (e.g., 192k)")
@click.option("--sample-rate", type=int, help="Audio sample rate (e.g., 44100)")
@click.option("--channels", type=int, help="Audio channels (1=mono, 2=stereo)")
@click.option("--width", "-w", type=int, help="Width for scale/crop/pad")
@click.option("--height", "-h", type=int, help="Height for scale/crop/pad")
@click.option("--rotation", type=click.Choice(["90", "180", "270"]), help="Rotation angle")
@click.option("--fps", type=int, help="Target frame rate")
@click.option("--brightness", type=float, help="Brightness (-1.0 to 1.0)")
@click.option("--contrast", type=float, help="Contrast (0.0 to 2.0)")
@click.option("--saturation", type=float, help="Saturation (0.0 to 3.0)")
@click.option("--blur-amount", type=float, help="Blur amount (0-5)")
@click.option("--sharpen-amount", type=float, help="Sharpen amount (0-5)")
@click.option("--scene-count", type=int, default=10, help="Number of scenes (for scene operations)")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def utilities_cmd(
    operation: str,
    input_file: Path,
    output: Optional[Path],
    start: Optional[float],
    end: Optional[float],
    duration: Optional[float],
    volume: Optional[float],
    fade_in: Optional[float],
    fade_out: Optional[float],
    bitrate: Optional[str],
    sample_rate: Optional[int],
    channels: Optional[int],
    width: Optional[int],
    height: Optional[int],
    rotation: Optional[str],
    fps: Optional[int],
    brightness: Optional[float],
    contrast: Optional[float],
    saturation: Optional[float],
    blur_amount: Optional[float],
    sharpen_amount: Optional[float],
    scene_count: int,
    as_json: bool,
):
    """Run utility media helper operations."""
    _check_required_tools(['ffmpeg'], as_json)
    helpers = get_media_helpers()
    op = operation.lower()

    # Auto-generate output file if not provided (except for detection operations)
    if not output and op not in ("silence-detect", "blackdetect"):
        output = input_file.parent / f"{input_file.stem}_{op}{input_file.suffix}"

    try:
        # Quick Helpers
        if op == "remux":
            result = helpers.remux(str(input_file), str(output))
        elif op == "extract-audio":
            result = helpers.extract_audio(str(input_file), str(output), audio_bitrate=bitrate)
        elif op == "mute":
            result = helpers.mute(str(input_file), str(output))
        elif op == "trim":
            if start is None:
                _error("--start is required for trim operation", as_json)
            result = helpers.trim(str(input_file), str(output), start, end_time=end, duration=duration)
        elif op == "preview":
            dur = duration or 10.0
            st = start or 0.0
            result = helpers.preview_clip(str(input_file), str(output), duration=dur, start_time=st)
        elif op == "thumbnail":
            ts = start or 1.0
            result = helpers.thumbnail(str(input_file), str(output), timestamp=ts, width=width)

        # Audio Utilities
        elif op == "volume":
            if volume is None:
                _error("--volume is required for volume operation", as_json)
            result = helpers.adjust_volume(str(input_file), str(output), volume)
        elif op == "fade":
            result = helpers.fade_audio(str(input_file), str(output),
                                       fade_in_duration=fade_in or 0.0,
                                       fade_out_duration=fade_out or 0.0)
        elif op == "bitrate":
            if not bitrate:
                _error("--bitrate is required for bitrate operation", as_json)
            result = helpers.convert_audio_bitrate(str(input_file), str(output), bitrate, sample_rate=sample_rate)
        elif op == "channels":
            if not channels:
                _error("--channels is required for channels operation", as_json)
            result = helpers.convert_channels(str(input_file), str(output), channels)
        elif op == "silence-detect":
            result = helpers.detect_silence(str(input_file))
            if result.success:
                periods = result.metadata.get("silence_periods", [])
                if as_json:
                    _output({"success": True, "silence_periods": periods}, as_json=True)
                else:
                    click.echo(f"Found {len(periods)} silent periods:")
                    for start_t, end_t, dur in periods:
                        click.echo(f"  {start_t:.2f}s - {end_t:.2f}s (duration: {dur:.2f}s)")
                return
        elif op == "loudnorm":
            result = helpers.loudness_normalize(str(input_file), str(output))

        # Video Utilities
        elif op == "scale":
            result = helpers.scale_video(str(input_file), str(output), width=width, height=height)
        elif op == "crop":
            if not width or not height:
                _error("--width and --height are required for crop operation", as_json)
            result = helpers.crop_video(str(input_file), str(output), width, height)
        elif op == "pad":
            if not width or not height:
                _error("--width and --height are required for pad operation", as_json)
            result = helpers.pad_video(str(input_file), str(output), width, height)
        elif op == "rotate":
            if not rotation:
                _error("--rotation is required for rotate operation", as_json)
            result = helpers.rotate_video(str(input_file), str(output), int(rotation))
        elif op == "fps":
            if not fps:
                _error("--fps is required for fps operation", as_json)
            result = helpers.change_fps(str(input_file), str(output), fps)
        elif op == "color":
            result = helpers.adjust_color(str(input_file), str(output),
                                         brightness=brightness or 0.0,
                                         contrast=contrast or 1.0,
                                         saturation=saturation or 1.0)
        elif op == "blur":
            result = helpers.blur_sharpen(str(input_file), str(output),
                                         blur_amount=blur_amount or 0.0,
                                         sharpen_amount=sharpen_amount or 0.0)
        elif op == "deinterlace":
            result = helpers.deinterlace(str(input_file), str(output))

        # Smart Helpers
        elif op == "blackdetect":
            result = helpers.detect_black_frames(str(input_file))
            if result.success:
                periods = result.metadata.get("black_periods", [])
                if as_json:
                    _output({"success": True, "black_periods": periods}, as_json=True)
                else:
                    click.echo(f"Found {len(periods)} black periods:")
                    for start_t, end_t, dur in periods:
                        click.echo(f"  {start_t:.2f}s - {end_t:.2f}s (duration: {dur:.2f}s)")
                return
        elif op == "scene-preview":
            output_dir = output or input_file.parent / f"{input_file.stem}_scene_previews"
            result = helpers.generate_scene_previews(str(input_file), str(output_dir), scene_count=scene_count)
            if result.success:
                files = result.metadata.get("preview_files", [])
                if as_json:
                    _output({"success": True, "preview_files": files, "count": len(files)}, as_json=True)
                else:
                    click.echo(f"Generated {len(files)} scene preview clips in: {output_dir}")
                return
        elif op == "scene-thumbnail":
            output_dir = output or input_file.parent / f"{input_file.stem}_scene_thumbnails"
            result = helpers.generate_scene_thumbnails(str(input_file), str(output_dir), scene_count=scene_count)
            if result.success:
                files = result.metadata.get("thumbnail_files", [])
                if as_json:
                    _output({"success": True, "thumbnail_files": files, "count": len(files)}, as_json=True)
                else:
                    click.echo(f"Generated {len(files)} scene thumbnails in: {output_dir}")
                return
        else:
            _error(f"Unknown operation: {operation}", as_json)

        # Handle result
        if result.success:
            if as_json:
                _output({
                    "success": True,
                    "input": str(input_file),
                    "output": result.metadata.get("output_file", str(output)),
                    "operation": op,
                }, as_json=True)
            else:
                click.echo(f"✓ {op.title()} completed: {result.metadata.get('output_file', output)}")
        else:
            _error(result.error_message or f"{op} operation failed", as_json)

    except Exception as e:
        _error(f"Utility operation failed: {str(e)}", as_json)


# ---------------------------------------------------------------------------
# ravn serve  (placeholder)
# ---------------------------------------------------------------------------

@cli.command("tools")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def tools_cmd(as_json: bool):
    """
    Report external tool availability (ffmpeg, ffprobe, yt-dlp, aria2c).

    Answers "why does RAVN say a tool is missing?" without opening the GUI: it shows
    where each tool resolved from, so a bundled copy can be told apart from a
    system-installed one. On Linux it also prints the command to install what is
    missing. Doubles as the headless check that a packaged build found its own tools.
    """
    checker = get_tool_health_checker()
    checker.clear_cache()
    summary = checker.get_health_summary()

    tools_payload = {}
    for tool_name, tool_info in summary["tools"].items():
        tools_payload[tool_name] = {
            "status": tool_info.status.value,
            "path": tool_info.path,
            "version": tool_info.version,
            "required": tool_info.required,
            "bundled": bool(bundled_tools.find_tool(tool_name)),
        }

    missing = summary["missing_required"] + summary["missing_optional"]
    install_command = tool_installer.get_manual_install_command(missing) if missing else None

    if as_json:
        _output(
            {
                "overall_status": summary["overall_status"],
                "available": summary["available_tools"],
                "total": summary["total_tools"],
                "tools": tools_payload,
                "missing": missing,
                "install_command": install_command,
            },
            as_json=True,
        )
        return

    for tool_name, info in tools_payload.items():
        marker = "OK " if info["status"] == "available" else "-- "
        origin = " (bundled)" if info["bundled"] else ""
        click.echo(f"{marker}{tool_name}: {info['status']}{origin}")
        if info["path"]:
            click.echo(f"     path: {info['path']}")
        if info["version"]:
            click.echo(f"     version: {info['version']}")

    if install_command:
        click.echo("")
        click.echo(f"Install missing tools with:\n  {install_command}")
    elif missing:
        click.echo("")
        click.echo(f"Missing: {', '.join(missing)}")


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
