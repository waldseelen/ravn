from pathlib import Path
from unittest.mock import patch

from ravn_app.utils.ffmpeg_checker import (
    configure_ffmpeg_runtime,
    find_bundled_tool,
    prepend_bundled_ffmpeg_to_path,
    resolve_tool_path,
)


def test_find_bundled_tool_prefers_assets_layout(tmp_path):
    bundled_dir = tmp_path / "assets" / "ffmpeg" / "win64"
    bundled_dir.mkdir(parents=True)
    ffmpeg_binary = bundled_dir / ("ffmpeg.exe" if __import__("os").name == "nt" else "ffmpeg")
    ffmpeg_binary.write_text("demo")

    with patch("ravn_app.utils.ffmpeg_checker._candidate_runtime_roots", return_value=[tmp_path]):
        resolved = find_bundled_tool("ffmpeg")

    assert resolved == str(ffmpeg_binary)


def test_resolve_tool_path_respects_explicit_existing_path(tmp_path):
    explicit = tmp_path / "ffmpeg-custom.exe"
    explicit.write_text("demo")

    resolved = resolve_tool_path(str(explicit), "ffmpeg")

    assert resolved == str(explicit)


def test_resolve_tool_path_uses_bundled_before_path(tmp_path):
    bundled_dir = tmp_path / "assets" / "ffmpeg" / "win64"
    bundled_dir.mkdir(parents=True)
    ffprobe_binary = bundled_dir / ("ffprobe.exe" if __import__("os").name == "nt" else "ffprobe")
    ffprobe_binary.write_text("demo")

    with patch("ravn_app.utils.ffmpeg_checker._candidate_runtime_roots", return_value=[tmp_path]), patch(
        "ravn_app.utils.ffmpeg_checker.shutil.which", return_value="/usr/bin/ffprobe"
    ):
        resolved = resolve_tool_path("ffprobe", "ffprobe")

    assert resolved == str(ffprobe_binary)


def test_configure_ffmpeg_runtime_prepends_bundled_dir(tmp_path):
    bundled_dir = tmp_path / "assets" / "ffmpeg" / "win64"
    bundled_dir.mkdir(parents=True)
    ffmpeg_binary = bundled_dir / ("ffmpeg.exe" if __import__("os").name == "nt" else "ffmpeg")
    ffprobe_binary = bundled_dir / ("ffprobe.exe" if __import__("os").name == "nt" else "ffprobe")
    ffmpeg_binary.write_text("demo")
    ffprobe_binary.write_text("demo")

    with patch.dict("os.environ", {"PATH": "C:/existing"}, clear=True), patch(
        "ravn_app.utils.ffmpeg_checker._candidate_runtime_roots", return_value=[tmp_path]
    ):
        resolved_ffmpeg, resolved_ffprobe = configure_ffmpeg_runtime()

    assert resolved_ffmpeg == str(ffmpeg_binary)
    assert resolved_ffprobe == str(ffprobe_binary)


def test_prepend_bundled_ffmpeg_to_path_is_idempotent(tmp_path):
    bundled_dir = tmp_path / "assets" / "ffmpeg" / "win64"
    bundled_dir.mkdir(parents=True)
    ffmpeg_binary = bundled_dir / ("ffmpeg.exe" if __import__("os").name == "nt" else "ffmpeg")
    ffmpeg_binary.write_text("demo")

    with patch.dict("os.environ", {"PATH": str(bundled_dir)}, clear=True), patch(
        "ravn_app.utils.ffmpeg_checker._candidate_runtime_roots", return_value=[tmp_path]
    ):
        prepend_bundled_ffmpeg_to_path()
        path_value = __import__("os").environ["PATH"]

    assert path_value == str(bundled_dir)
