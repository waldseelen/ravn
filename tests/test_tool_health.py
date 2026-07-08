"""Tests for tool health checking system."""

from unittest.mock import Mock, patch

from ravn_app.core.tool_health import (
    ToolHealthChecker,
    ToolStatus,
    check_tool_availability,
    get_missing_tools_message,
    get_tool_health_checker,
)


class TestToolHealthChecker:
    """Test the ToolHealthChecker class."""

    def test_check_tool_available(self):
        """Test checking an available tool."""
        checker = ToolHealthChecker()
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            with patch.object(checker, '_get_tool_version', return_value='ffmpeg version 4.4'):
                info = checker.check_tool('ffmpeg', use_cache=False)

                assert info.name == 'ffmpeg'
                assert info.status == ToolStatus.AVAILABLE
                assert info.path == '/usr/bin/ffmpeg'
                assert info.version == 'ffmpeg version 4.4'
                assert info.required is True
                assert 'video_conversion' in info.affected_features

    def test_check_tool_missing(self):
        """Test checking a missing tool."""
        checker = ToolHealthChecker()
        with patch('shutil.which', return_value=None):
            info = checker.check_tool('aria2c', use_cache=False)

            assert info.name == 'aria2c'
            assert info.status == ToolStatus.MISSING
            assert info.path is None
            assert info.required is False
            assert 'torrent_download' in info.affected_features

    def test_cache_behavior(self):
        """Test that caching works correctly."""
        checker = ToolHealthChecker()
        with patch('shutil.which', return_value='/usr/bin/ffmpeg') as mock_which:
            with patch.object(checker, '_get_tool_version', return_value='ffmpeg version 4.4'):
                # First call should hit shutil.which
                info1 = checker.check_tool('ffmpeg', use_cache=True)
                assert mock_which.call_count == 1

                # Second call with cache should not hit shutil.which again
                info2 = checker.check_tool('ffmpeg', use_cache=True)
                assert mock_which.call_count == 1
                assert info2 is info1  # cached call returns the same object

                # Third call without cache should hit shutil.which
                info3 = checker.check_tool('ffmpeg', use_cache=False)
                assert mock_which.call_count == 2
                assert info3.name == info1.name  # fresh check, same tool

    def test_clear_cache(self):
        """Test cache clearing."""
        checker = ToolHealthChecker()
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            with patch.object(checker, '_get_tool_version', return_value='ffmpeg version 4.4'):
                checker.check_tool('ffmpeg')
                assert len(checker._cache) > 0

                checker.clear_cache()
                assert len(checker._cache) == 0

    def test_get_all_tools(self):
        """Test checking all tools."""
        checker = ToolHealthChecker()
        with patch('shutil.which', return_value='/usr/bin/tool'):
            with patch.object(checker, '_get_tool_version', return_value='version 1.0'):
                results = checker.check_all_tools(use_cache=False)

                assert 'ffmpeg' in results
                assert 'ffprobe' in results
                assert 'yt-dlp' in results
                assert 'aria2c' in results
                assert len(results) == 4

    def test_get_missing_required_tools(self):
        """Test getting list of missing required tools."""
        checker = ToolHealthChecker()
        with patch('shutil.which', side_effect=lambda x: '/usr/bin/ffmpeg' if x == 'ffmpeg' else None):
            with patch.object(checker, '_get_tool_version', return_value='version 1.0'):
                missing = checker.get_missing_required_tools()

                # ffmpeg should be available, ffprobe and yt-dlp should be missing
                assert 'ffmpeg' not in missing
                assert 'ffprobe' in missing
                assert 'yt-dlp' in missing
                assert 'aria2c' not in missing  # aria2c is optional

    def test_get_missing_optional_tools(self):
        """Test getting list of missing optional tools."""
        checker = ToolHealthChecker()
        with patch('shutil.which', side_effect=lambda x: '/usr/bin/tool' if x != 'aria2c' else None):
            with patch.object(checker, '_get_tool_version', return_value='version 1.0'):
                missing = checker.get_missing_optional_tools()

                assert 'aria2c' in missing
                assert 'ffmpeg' not in missing
                assert len(missing) == 1

    def test_get_affected_features(self):
        """Test getting affected features for a tool."""
        checker = ToolHealthChecker()

        ffmpeg_features = checker.get_affected_features('ffmpeg')
        assert 'video_conversion' in ffmpeg_features
        assert 'audio_extraction' in ffmpeg_features
        assert 'filters' in ffmpeg_features

        aria2c_features = checker.get_affected_features('aria2c')
        assert 'torrent_download' in aria2c_features
        assert 'magnet_download' in aria2c_features

    def test_is_feature_available(self):
        """Test checking if a feature is available."""
        checker = ToolHealthChecker()
        with patch('shutil.which', side_effect=lambda x: '/usr/bin/tool' if x == 'ffmpeg' else None):
            with patch.object(checker, '_get_tool_version', return_value='version 1.0'):
                # video_conversion requires ffmpeg (available)
                assert checker.is_feature_available('video_conversion') is True

                # torrent_download requires aria2c (not available)
                assert checker.is_feature_available('torrent_download') is False

    def test_get_health_summary_healthy(self):
        """Test health summary when all tools are available."""
        checker = ToolHealthChecker()
        with patch('shutil.which', return_value='/usr/bin/tool'):
            with patch.object(checker, '_get_tool_version', return_value='version 1.0'):
                summary = checker.get_health_summary()

                assert summary['overall_status'] == 'healthy'
                assert summary['total_tools'] == 4
                assert summary['available_tools'] == 4
                assert len(summary['missing_required']) == 0
                assert len(summary['missing_optional']) == 0
                assert len(summary['unavailable_features']) == 0

    def test_get_health_summary_degraded(self):
        """Test health summary when optional tools are missing."""
        checker = ToolHealthChecker()
        with patch('shutil.which', side_effect=lambda x: '/usr/bin/tool' if x != 'aria2c' else None):
            with patch.object(checker, '_get_tool_version', return_value='version 1.0'):
                summary = checker.get_health_summary()

                assert summary['overall_status'] == 'degraded'
                assert summary['available_tools'] == 3
                assert len(summary['missing_required']) == 0
                assert 'aria2c' in summary['missing_optional']
                assert 'torrent_download' in summary['unavailable_features']

    def test_get_health_summary_critical(self):
        """Test health summary when required tools are missing."""
        checker = ToolHealthChecker()
        with patch('shutil.which', side_effect=lambda x: None if x == 'ffmpeg' else '/usr/bin/tool'):
            with patch.object(checker, '_get_tool_version', return_value='version 1.0'):
                summary = checker.get_health_summary()

                assert summary['overall_status'] == 'critical'
                assert 'ffmpeg' in summary['missing_required']

    def test_get_tool_version_passes_hidden_window_kwargs(self):
        checker = ToolHealthChecker()
        with patch('ravn_app.core.tool_health.get_hidden_subprocess_kwargs', return_value={'creationflags': 123}), patch(
            'subprocess.run',
            return_value=Mock(returncode=0, stdout='ffmpeg version 7.0\n'),
        ) as mock_run:
            version = checker._get_tool_version('ffmpeg', 'ffmpeg')

        assert version == 'ffmpeg version 7.0'
        assert mock_run.call_args.kwargs['creationflags'] == 123


class TestGlobalFunctions:
    """Test global helper functions."""

    def test_get_tool_health_checker_singleton(self):
        """Test that get_tool_health_checker returns singleton."""
        checker1 = get_tool_health_checker()
        checker2 = get_tool_health_checker()

        assert checker1 is checker2

    def test_check_tool_availability(self):
        """Test quick availability check."""
        checker = get_tool_health_checker()
        checker.clear_cache()
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            with patch('ravn_app.core.tool_health.ToolHealthChecker._get_tool_version', return_value='version 1.0'):
                assert check_tool_availability('ffmpeg') is True

        checker.clear_cache()
        with patch('shutil.which', return_value=None):
            assert check_tool_availability('nonexistent') is False

    def test_get_missing_tools_message_none(self):
        """Test missing tools message when all tools are available."""
        with patch('shutil.which', return_value='/usr/bin/tool'):
            with patch('ravn_app.core.tool_health.ToolHealthChecker._get_tool_version', return_value='version 1.0'):
                # Clear cache to ensure fresh check
                checker = get_tool_health_checker()
                checker.clear_cache()

                message = get_missing_tools_message()
                assert message is None

    def test_get_missing_tools_message_required(self):
        """Test missing tools message when required tools are missing."""
        with patch('shutil.which', return_value=None):
            # Clear cache to ensure fresh check
            checker = get_tool_health_checker()
            checker.clear_cache()

            message = get_missing_tools_message()
            assert message is not None
            assert 'ffmpeg' in message.lower()
            assert 'required' in message.lower()

    def test_get_missing_tools_message_optional(self):
        """Test missing tools message when only optional tools are missing."""
        with patch('shutil.which', side_effect=lambda x: '/usr/bin/tool' if x != 'aria2c' else None):
            with patch('ravn_app.core.tool_health.ToolHealthChecker._get_tool_version', return_value='version 1.0'):
                # Clear cache to ensure fresh check
                checker = get_tool_health_checker()
                checker.clear_cache()

                message = get_missing_tools_message()
                assert message is not None
                assert 'aria2c' in message.lower()
                assert 'optional' in message.lower()


class TestToolVersionExtraction:
    """Test version extraction from different tools."""

    def test_get_ffmpeg_version(self):
        """Test extracting FFmpeg version."""
        checker = ToolHealthChecker()
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg version 4.4.2-0ubuntu0.22.04.1 Copyright (c) 2000-2021"

        with patch('subprocess.run', return_value=mock_result):
            version = checker._get_tool_version('ffmpeg', '/usr/bin/ffmpeg')
            assert version == "ffmpeg version 4.4.2-0ubuntu0.22.04.1 Copyright (c) 2000-2021"

    def test_get_aria2c_version(self):
        """Test extracting aria2c version."""
        checker = ToolHealthChecker()
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "aria2 version 1.36.0"

        with patch('subprocess.run', return_value=mock_result):
            version = checker._get_tool_version('aria2c', '/usr/bin/aria2c')
            assert version == "aria2 version 1.36.0"

    def test_version_extraction_failure(self):
        """Test version extraction when command fails."""
        checker = ToolHealthChecker()
        mock_result = Mock()
        mock_result.returncode = 1

        with patch('subprocess.run', return_value=mock_result):
            version = checker._get_tool_version('ffmpeg', '/usr/bin/ffmpeg')
            assert version is None

    def test_version_extraction_timeout(self):
        """Test version extraction with timeout."""
        checker = ToolHealthChecker()

        with patch('subprocess.run', side_effect=TimeoutError):
            version = checker._get_tool_version('ffmpeg', '/usr/bin/ffmpeg')
            assert version is None
