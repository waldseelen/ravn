"""
Tool installer testleri — winget üzerinden eksik araçların kurulumu ve
PATH'in çalışan process içinde anında yenilenmesi.
"""

import subprocess
from unittest.mock import Mock, patch

from ravn_app.core import tool_installer


class TestIsWingetAvailable:
    def test_true_when_winget_on_path(self):
        with patch("ravn_app.core.tool_installer.shutil.which", return_value=r"C:\winget.exe"):
            assert tool_installer.is_winget_available() is True

    def test_false_when_winget_missing(self):
        with patch("ravn_app.core.tool_installer.shutil.which", return_value=None):
            assert tool_installer.is_winget_available() is False


class TestPackageIdMapping:
    def test_known_tools_map_to_expected_winget_ids(self):
        assert tool_installer._package_id_for_tool("ffmpeg") == "Gyan.FFmpeg"
        assert tool_installer._package_id_for_tool("yt-dlp") == "yt-dlp.yt-dlp"
        assert tool_installer._package_id_for_tool("aria2c") == "aria2.aria2"

    def test_ffprobe_shares_the_ffmpeg_package(self):
        assert tool_installer._package_id_for_tool("ffprobe") == tool_installer._package_id_for_tool("ffmpeg")

    def test_unknown_tool_has_no_mapping(self):
        assert tool_installer._package_id_for_tool("not-a-real-tool") is None


class TestInstallTool:
    def test_unmapped_tool_fails_without_calling_winget(self):
        with patch("ravn_app.core.tool_installer.subprocess.run") as run_mock:
            result = tool_installer.install_tool("not-a-real-tool")

        assert result.success is False
        assert result.package_id is None
        run_mock.assert_not_called()

    def test_fails_gracefully_when_winget_missing(self):
        with patch("ravn_app.core.tool_installer.is_winget_available", return_value=False), \
             patch("ravn_app.core.tool_installer.subprocess.run") as run_mock:
            result = tool_installer.install_tool("yt-dlp")

        assert result.success is False
        assert "winget" in result.message.lower()
        run_mock.assert_not_called()

    def test_success_when_winget_returns_zero(self):
        completed = Mock(returncode=0, stdout="Successfully installed")
        with patch("ravn_app.core.tool_installer.is_winget_available", return_value=True), \
             patch("ravn_app.core.tool_installer.subprocess.run", return_value=completed) as run_mock:
            result = tool_installer.install_tool("yt-dlp")

        assert result.success is True
        assert result.package_id == "yt-dlp.yt-dlp"
        called_command = run_mock.call_args[0][0]
        assert called_command[:3] == ["winget", "install", "--id"]
        assert "yt-dlp.yt-dlp" in called_command

    def test_failure_when_winget_returns_nonzero(self):
        completed = Mock(returncode=1, stdout="No package found matching input criteria")
        with patch("ravn_app.core.tool_installer.is_winget_available", return_value=True), \
             patch("ravn_app.core.tool_installer.subprocess.run", return_value=completed):
            result = tool_installer.install_tool("aria2c")

        assert result.success is False
        assert "1" in result.message

    def test_timeout_reported_as_failure_not_raised(self):
        with patch("ravn_app.core.tool_installer.is_winget_available", return_value=True), \
             patch(
                 "ravn_app.core.tool_installer.subprocess.run",
                 side_effect=subprocess.TimeoutExpired(cmd="winget", timeout=5),
             ):
            result = tool_installer.install_tool("ffmpeg", timeout=5)

        assert result.success is False
        assert "timed out" in result.message.lower()


class TestInstallMissingTools:
    def test_dedupes_ffmpeg_and_ffprobe_into_a_single_winget_call(self):
        completed = Mock(returncode=0, stdout="Installed")
        with patch("ravn_app.core.tool_installer.is_winget_available", return_value=True), \
             patch("ravn_app.core.tool_installer.subprocess.run", return_value=completed) as run_mock, \
             patch("ravn_app.core.tool_installer._refresh_process_environment_path"):
            results = tool_installer.install_missing_tools(["ffmpeg", "ffprobe"])

        assert run_mock.call_count == 1
        assert results["ffmpeg"].success is True
        assert results["ffprobe"].success is True
        assert results["ffmpeg"].package_id == results["ffprobe"].package_id

    def test_progress_callback_reports_installing_then_done(self):
        completed = Mock(returncode=0, stdout="Installed")
        stages = []
        with patch("ravn_app.core.tool_installer.is_winget_available", return_value=True), \
             patch("ravn_app.core.tool_installer.subprocess.run", return_value=completed), \
             patch("ravn_app.core.tool_installer._refresh_process_environment_path"):
            tool_installer.install_missing_tools(
                ["yt-dlp"],
                progress_callback=lambda tool, stage: stages.append((tool, stage)),
            )

        assert ("yt-dlp", "installing") in stages
        assert ("yt-dlp", "done") in stages

    def test_progress_callback_reports_error_on_failed_install(self):
        completed = Mock(returncode=1, stdout="failed")
        stages = []
        with patch("ravn_app.core.tool_installer.is_winget_available", return_value=True), \
             patch("ravn_app.core.tool_installer.subprocess.run", return_value=completed), \
             patch("ravn_app.core.tool_installer._refresh_process_environment_path"):
            tool_installer.install_missing_tools(
                ["aria2c"],
                progress_callback=lambda tool, stage: stages.append((tool, stage)),
            )

        assert ("aria2c", "error") in stages

    def test_refreshes_process_path_exactly_once_regardless_of_tool_count(self):
        completed = Mock(returncode=0, stdout="Installed")
        with patch("ravn_app.core.tool_installer.is_winget_available", return_value=True), \
             patch("ravn_app.core.tool_installer.subprocess.run", return_value=completed), \
             patch("ravn_app.core.tool_installer._refresh_process_environment_path") as refresh_mock:
            tool_installer.install_missing_tools(["ffmpeg", "ffprobe", "yt-dlp", "aria2c"])

        refresh_mock.assert_called_once()

    def test_unmapped_tool_reports_failure_without_blocking_others(self):
        completed = Mock(returncode=0, stdout="Installed")
        with patch("ravn_app.core.tool_installer.is_winget_available", return_value=True), \
             patch("ravn_app.core.tool_installer.subprocess.run", return_value=completed), \
             patch("ravn_app.core.tool_installer._refresh_process_environment_path"):
            results = tool_installer.install_missing_tools(["yt-dlp", "totally-unknown-tool"])

        assert results["yt-dlp"].success is True
        assert results["totally-unknown-tool"].success is False


class TestRefreshProcessEnvironmentPath:
    def _fake_winreg(self, hkcu_path: str, hklm_path: str):
        fake_winreg = Mock()
        fake_winreg.HKEY_CURRENT_USER = "HKCU"
        fake_winreg.HKEY_LOCAL_MACHINE = "HKLM"

        def _open_key(hive, subkey):
            cm = Mock()
            cm.__enter__ = Mock(return_value=cm)
            cm.__exit__ = Mock(return_value=False)
            cm._hive = hive
            return cm

        def _query_value(key, name):
            assert name == "Path"
            return (hkcu_path, 1) if key._hive == "HKCU" else (hklm_path, 1)

        fake_winreg.OpenKey = Mock(side_effect=_open_key)
        fake_winreg.QueryValueEx = Mock(side_effect=_query_value)
        return fake_winreg

    def test_merges_new_registry_paths_into_process_environment(self, monkeypatch):
        monkeypatch.setattr(tool_installer.os, "name", "nt")
        monkeypatch.setattr(tool_installer.os, "pathsep", ";")
        monkeypatch.setenv("PATH", r"C:\Existing")

        fake_winreg = self._fake_winreg(
            hkcu_path=r"C:\Existing;C:\Users\HP\AppData\Local\Microsoft\WinGet\Links",
            hklm_path=r"C:\Windows\System32",
        )
        with patch.dict("sys.modules", {"winreg": fake_winreg}):
            added = tool_installer._refresh_process_environment_path()

        assert added == 2
        current_path = tool_installer.os.environ["PATH"]
        assert r"C:\Users\HP\AppData\Local\Microsoft\WinGet\Links" in current_path
        assert r"C:\Windows\System32" in current_path

    def test_does_not_duplicate_existing_path_entries(self, monkeypatch):
        monkeypatch.setattr(tool_installer.os, "name", "nt")
        monkeypatch.setattr(tool_installer.os, "pathsep", ";")
        monkeypatch.setenv("PATH", r"C:\Existing;C:\Windows\System32")

        fake_winreg = self._fake_winreg(
            hkcu_path=r"C:\Existing",
            hklm_path=r"C:\Windows\System32",
        )
        with patch.dict("sys.modules", {"winreg": fake_winreg}):
            added = tool_installer._refresh_process_environment_path()

        assert added == 0

    def test_returns_zero_on_non_windows(self, monkeypatch):
        monkeypatch.setattr(tool_installer.os, "name", "posix")
        assert tool_installer._refresh_process_environment_path() == 0
