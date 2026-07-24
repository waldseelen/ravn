import sys
from unittest.mock import patch

from ravn_app.utils import ffmpeg_checker
from ravn_app.utils.ffmpeg_checker import (
    FFmpegCodecChecker,
    _binary_name,
    _candidate_runtime_roots,
    configure_ffmpeg_runtime,
    find_bundled_tool,
    iter_bundled_ffmpeg_dirs,
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


def test_binary_name_leaves_existing_exe_suffix_untouched():
    assert _binary_name("ffmpeg.exe") == "ffmpeg.exe"


def test_resolve_tool_path_returns_normalized_when_explicit_path_missing(tmp_path):
    missing = tmp_path / "no-such-dir" / "ffmpeg"

    resolved = resolve_tool_path(str(missing), "ffmpeg")

    assert resolved == str(missing)


def test_resolve_tool_path_uses_shutil_which_for_custom_name():
    with patch("ravn_app.utils.ffmpeg_checker.shutil.which", return_value="/usr/bin/ffmpeg4"):
        resolved = resolve_tool_path("ffmpeg4", "ffmpeg")

    assert resolved == "/usr/bin/ffmpeg4"


def test_candidate_runtime_roots_includes_meipass_when_frozen(tmp_path):
    with patch.object(sys, "_MEIPASS", str(tmp_path), create=True):
        roots = _candidate_runtime_roots()

    assert tmp_path in roots


def test_candidate_runtime_roots_swallows_executable_resolve_failure():
    original_path = ffmpeg_checker.Path

    def fake_path(arg):
        if arg == sys.executable:
            raise OSError("cannot resolve executable path")
        return original_path(arg)

    with patch.object(ffmpeg_checker, "Path", fake_path):
        roots = _candidate_runtime_roots()

    # Falls through to the project-root fallback instead of raising.
    assert roots


def test_candidate_runtime_roots_deduplicates_equal_roots(tmp_path):
    with patch.object(sys, "_MEIPASS", str(tmp_path), create=True), patch(
        "ravn_app.utils.ffmpeg_checker._project_root", return_value=tmp_path
    ):
        roots = _candidate_runtime_roots()

    assert roots.count(tmp_path) == 1


def test_iter_bundled_ffmpeg_dirs_deduplicates_repeated_roots(tmp_path):
    with patch(
        "ravn_app.utils.ffmpeg_checker._candidate_runtime_roots",
        return_value=[tmp_path, tmp_path],
    ):
        dirs = list(iter_bundled_ffmpeg_dirs())

    assert len(dirs) == len(set(dirs))


class TestFFmpegCodecChecker:
    def test_get_supported_codecs_caches_result(self):
        checker = FFmpegCodecChecker()
        fake_data = {"codecs": [{"name": "h264"}, {"name": "aac"}, {"name": None}]}

        with patch.object(checker.runner, "run_ffprobe_json", return_value=fake_data) as mock_probe:
            first = checker.get_supported_codecs()
            second = checker.get_supported_codecs()

        assert first == ["h264", "aac"]
        assert second == ["h264", "aac"]
        assert mock_probe.call_count == 1

    def test_get_supported_codecs_returns_empty_when_probe_fails(self):
        checker = FFmpegCodecChecker()

        with patch.object(checker.runner, "run_ffprobe_json", return_value=None):
            assert checker.get_supported_codecs() == []

    def test_is_codec_supported(self):
        checker = FFmpegCodecChecker()

        with patch.object(checker, "get_supported_codecs", return_value=["libx264"]):
            assert checker.is_codec_supported("libx264") is True
            assert checker.is_codec_supported("libx265") is False

    def test_check_video_and_audio_codecs(self):
        checker = FFmpegCodecChecker()

        with patch.object(checker, "get_supported_codecs", return_value=["libx264", "aac"]):
            video = checker.check_video_codecs()
            audio = checker.check_audio_codecs()

        assert video == {"h264": True, "h265": False, "vp8": False, "vp9": False, "av1": False}
        assert audio == {"aac": True, "mp3": False, "opus": False, "vorbis": False, "flac": False}

    def test_get_ffmpeg_info_when_available(self):
        checker = FFmpegCodecChecker()

        with patch.object(checker.runner, "get_version", return_value="ffmpeg version 6.0"), patch.object(
            checker, "check_video_codecs", return_value={"h264": True}
        ), patch.object(checker, "check_audio_codecs", return_value={"aac": True}):
            info = checker.get_ffmpeg_info()

        assert info["available"] is True
        assert info["version"] == "ffmpeg version 6.0"
        assert info["video_codecs"] == {"h264": True}
        assert info["audio_codecs"] == {"aac": True}

    def test_get_ffmpeg_info_when_unavailable(self):
        checker = FFmpegCodecChecker()

        with patch.object(checker.runner, "get_version", return_value=None):
            info = checker.get_ffmpeg_info()

        assert info == {"available": False}
