"""Tests for the shared bundled-tool lookup (assets/<tool>/<platform>/ resolution)."""

import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ravn_app.core import tool_health
from ravn_app.utils import bundled_tools


def _write_binary(root, asset_subdir, tool_name, platform_dir="win64"):
    """Create a fake bundled binary and return its path."""
    bundled_dir = root / "assets" / asset_subdir / platform_dir
    bundled_dir.mkdir(parents=True, exist_ok=True)
    binary = bundled_dir / (f"{tool_name}.exe" if os.name == "nt" else tool_name)
    binary.write_text("demo")
    return binary


@pytest.fixture
def bundled_root(tmp_path):
    """Point the lookup at tmp_path and pin the platform dir so layout is stable."""
    with patch("ravn_app.utils.bundled_tools.candidate_runtime_roots", return_value=[tmp_path]), patch(
        "ravn_app.utils.bundled_tools.PLATFORM_DIR", "win64"
    ):
        yield tmp_path


class TestFindTool:
    def test_finds_aria2c_in_its_own_asset_subdir(self, bundled_root):
        binary = _write_binary(bundled_root, "aria2", "aria2c")

        assert bundled_tools.find_tool("aria2c") == str(binary)

    def test_finds_ytdlp_in_its_own_asset_subdir(self, bundled_root):
        binary = _write_binary(bundled_root, "ytdlp", "yt-dlp")

        assert bundled_tools.find_tool("yt-dlp") == str(binary)

    def test_ffprobe_resolves_inside_the_ffmpeg_subdir(self, bundled_root):
        # ffprobe ships inside the FFmpeg archive rather than a directory of its own.
        binary = _write_binary(bundled_root, "ffmpeg", "ffprobe")

        assert bundled_tools.find_tool("ffprobe") == str(binary)

    def test_returns_none_when_tool_is_not_bundled(self, bundled_root):
        assert bundled_tools.find_tool("aria2c") is None

    def test_returns_none_for_unknown_tool_name(self, bundled_root):
        _write_binary(bundled_root, "mystery", "mystery")

        assert bundled_tools.find_tool("mystery") is None

    def test_does_not_confuse_tools_that_share_a_root(self, bundled_root):
        _write_binary(bundled_root, "aria2", "aria2c")

        # yt-dlp is not bundled even though aria2c is; the subdirs must stay distinct.
        assert bundled_tools.find_tool("yt-dlp") is None


class TestPreferBundled:
    def test_substitutes_bundled_copy_for_the_default_name(self, bundled_root):
        binary = _write_binary(bundled_root, "aria2", "aria2c")

        assert bundled_tools.prefer_bundled("aria2c", "aria2c") == str(binary)

    def test_passes_explicit_user_path_through_untouched(self, bundled_root):
        _write_binary(bundled_root, "aria2", "aria2c")
        explicit = r"D:\tools\my-aria2c.exe"

        assert bundled_tools.prefer_bundled(explicit, "aria2c") == explicit

    def test_keeps_bare_name_when_nothing_is_bundled(self, bundled_root):
        assert bundled_tools.prefer_bundled("aria2c", "aria2c") == "aria2c"

    def test_does_not_fall_back_to_path_lookup(self, bundled_root):
        """
        Regression guard: prefer_bundled must not bake an absolute PATH-resolved path
        into a runner at construction time. Runners resolve PATH lazily when they
        execute, so freezing a machine-specific path here would pin the object to one
        machine and go stale after the Settings "install missing tools" PATH refresh.
        """
        with patch(
            "ravn_app.utils.bundled_tools.shutil.which",
            return_value=r"C:\somewhere\aria2c.exe",
        ) as mock_which:
            resolved = bundled_tools.prefer_bundled("aria2c", "aria2c")

        assert resolved == "aria2c"
        mock_which.assert_not_called()


class TestConfigureBundledToolsPath:
    def test_prepends_each_bundled_directory_to_path(self, bundled_root):
        ffmpeg_binary = _write_binary(bundled_root, "ffmpeg", "ffmpeg")
        aria2_binary = _write_binary(bundled_root, "aria2", "aria2c")

        with patch.dict(os.environ, {"PATH": "C:/existing"}, clear=True):
            configured = bundled_tools.configure_bundled_tools_path()
            path_parts = os.environ["PATH"].split(os.pathsep)

        assert str(ffmpeg_binary.parent) in configured
        assert str(aria2_binary.parent) in configured
        assert str(ffmpeg_binary.parent) in path_parts
        assert str(aria2_binary.parent) in path_parts
        assert "C:/existing" in path_parts

    def test_reports_nothing_when_no_tools_are_bundled(self, bundled_root):
        with patch.dict(os.environ, {"PATH": "C:/existing"}, clear=True):
            configured = bundled_tools.configure_bundled_tools_path()

            assert configured == []
            assert os.environ["PATH"] == "C:/existing"

    def test_is_idempotent_across_repeated_calls(self, bundled_root):
        _write_binary(bundled_root, "ffmpeg", "ffmpeg")

        with patch.dict(os.environ, {"PATH": "C:/existing"}, clear=True):
            bundled_tools.configure_bundled_tools_path()
            first = os.environ["PATH"]
            bundled_tools.configure_bundled_tools_path()
            second = os.environ["PATH"]

        assert first == second

    def test_reports_a_shared_directory_only_once(self, bundled_root):
        # ffmpeg and ffprobe live in the same directory; it must not be listed twice.
        _write_binary(bundled_root, "ffmpeg", "ffmpeg")
        _write_binary(bundled_root, "ffmpeg", "ffprobe")

        with patch.dict(os.environ, {"PATH": "C:/existing"}, clear=True):
            configured = bundled_tools.configure_bundled_tools_path()

        assert len(configured) == len(set(configured))


class TestToolHealthSeesBundledTools:
    """
    A packaged build ships its tools, so Settings must report them as available
    without the user installing anything -- previously tool_health only consulted
    PATH, so bundled binaries still showed up as missing.
    """

    def test_reports_bundled_tool_as_available_even_when_absent_from_path(self, bundled_root):
        binary = _write_binary(bundled_root, "aria2", "aria2c")
        checker = tool_health.ToolHealthChecker()

        with patch("ravn_app.core.tool_health.shutil.which", return_value=None), patch.object(
            checker, "_get_tool_version", return_value="1.37.0"
        ):
            info = checker.check_tool("aria2c", use_cache=False)

        assert info.status is tool_health.ToolStatus.AVAILABLE
        assert info.path == str(binary)

    def test_still_reports_missing_when_neither_bundled_nor_on_path(self, bundled_root):
        checker = tool_health.ToolHealthChecker()

        with patch("ravn_app.core.tool_health.shutil.which", return_value=None):
            info = checker.check_tool("aria2c", use_cache=False)

        assert info.status is tool_health.ToolStatus.MISSING

    def test_falls_back_to_path_when_nothing_is_bundled(self, bundled_root):
        checker = tool_health.ToolHealthChecker()

        with patch("ravn_app.core.tool_health.shutil.which", return_value="/usr/bin/aria2c"), patch.object(
            checker, "_get_tool_version", return_value="1.37.0"
        ):
            info = checker.check_tool("aria2c", use_cache=False)

        assert info.status is tool_health.ToolStatus.AVAILABLE
        assert info.path == "/usr/bin/aria2c"


class TestToolVersionFlags:
    """
    yt-dlp and aria2c want GNU-style --version; ffmpeg/ffprobe want -version.
    Getting this wrong fails silently: yt-dlp parses '-version' as short flags,
    prints usage, and still exits 0, so a blank line got reported as the version.
    """

    @pytest.mark.parametrize(
        "tool_name,expected_flag",
        [
            ("ffmpeg", "-version"),
            ("ffprobe", "-version"),
            ("yt-dlp", "--version"),
            ("aria2c", "--version"),
        ],
    )
    def test_each_tool_is_probed_with_the_flag_it_understands(self, tool_name, expected_flag):
        checker = tool_health.ToolHealthChecker()
        completed = SimpleNamespace(returncode=0, stdout="1.2.3\n")

        with patch("ravn_app.core.tool_health.subprocess.run", return_value=completed) as run_mock:
            version = checker._get_tool_version(tool_name, f"/usr/bin/{tool_name}")

        assert run_mock.call_args[0][0] == [f"/usr/bin/{tool_name}", expected_flag]
        assert version == "1.2.3"
