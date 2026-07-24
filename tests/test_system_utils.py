"""Tests for system/platform detection helpers."""

from unittest.mock import Mock, patch

from ravn_app.utils.system_utils import (
    find_executable,
    get_ffmpeg_version,
    get_platform,
    is_ffmpeg_available,
)


def test_find_executable_prefers_local_script_dir_binary():
    with patch("ravn_app.utils.system_utils.os.path.exists", return_value=True):
        resolved = find_executable("ffmpeg")

    assert resolved is not None
    assert "ffmpeg" in resolved.lower()


def test_find_executable_falls_back_to_path_lookup():
    with patch("ravn_app.utils.system_utils.os.path.exists", return_value=False), patch(
        "ravn_app.utils.system_utils.which", return_value="/usr/bin/ffmpeg"
    ):
        resolved = find_executable("ffmpeg")

    assert resolved == "/usr/bin/ffmpeg"


def test_is_ffmpeg_available_true_when_found():
    with patch("ravn_app.utils.system_utils.find_executable", return_value="/usr/bin/ffmpeg"):
        assert is_ffmpeg_available() is True


def test_is_ffmpeg_available_false_when_missing():
    with patch("ravn_app.utils.system_utils.find_executable", return_value=None):
        assert is_ffmpeg_available() is False


def test_get_ffmpeg_version_delegates_to_runner():
    with patch("ravn_app.utils.system_utils.FFmpegRunner") as mock_runner_cls:
        mock_runner_cls.return_value = Mock(get_version=Mock(return_value="6.0"))
        assert get_ffmpeg_version() == "6.0"


def test_get_platform_windows():
    with patch("ravn_app.utils.system_utils.sys.platform", "win32"):
        assert get_platform() == "windows"


def test_get_platform_darwin():
    with patch("ravn_app.utils.system_utils.sys.platform", "darwin"):
        assert get_platform() == "darwin"


def test_get_platform_linux():
    with patch("ravn_app.utils.system_utils.sys.platform", "linux"):
        assert get_platform() == "linux"
