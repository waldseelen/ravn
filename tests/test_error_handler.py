"""
Error Handler Tests
"""

import pytest

from ravn_app.core.error_handler import (
    ErrorCategory, ErrorInfo, FFmpegErrorParser, YtDlpErrorParser,
    format_error_for_user, format_error_for_log,
    parse_ffmpeg_error, parse_ytdlp_error
)


class TestErrorInfo:
    """Tests for ErrorInfo dataclass"""

    def test_error_info_creation(self):
        """Test creating ErrorInfo"""
        error = ErrorInfo(
            category=ErrorCategory.FILE_NOT_FOUND,
            message="File not found",
            detail="test.mp4",
            suggestion="Check the file path"
        )
        
        assert error.category == ErrorCategory.FILE_NOT_FOUND
        assert error.message == "File not found"
        assert error.detail == "test.mp4"
        assert error.suggestion == "Check the file path"
        assert not error.is_recoverable

    def test_error_info_defaults(self):
        """Test ErrorInfo default values"""
        error = ErrorInfo(
            category=ErrorCategory.UNKNOWN_ERROR,
            message="Unknown error"
        )
        
        assert error.detail == ""
        assert error.suggestion == ""
        assert not error.is_recoverable
        assert error.raw_error == ""


class TestFFmpegErrorParser:
    """Tests for FFmpeg error parsing"""

    def test_parse_file_not_found(self):
        """Test parsing file not found error"""
        stderr = "input.mp4: No such file or directory"
        error = FFmpegErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.FILE_NOT_FOUND
        assert "not found" in error.message.lower()
        assert error.suggestion != ""

    def test_parse_permission_denied(self):
        """Test parsing permission denied error"""
        stderr = "output.mp4: Permission denied"
        error = FFmpegErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.PERMISSION_ERROR
        assert "permission" in error.message.lower()

    def test_parse_invalid_input(self):
        """Test parsing invalid input error"""
        stderr = "Invalid data found when processing input"
        error = FFmpegErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.INVALID_INPUT
        assert "corrupt" in error.message.lower() or "invalid" in error.message.lower()

    def test_parse_no_streams(self):
        """Test parsing no streams error"""
        stderr = "Input does not contain any stream"
        error = FFmpegErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.INVALID_INPUT
        assert "stream" in error.message.lower()

    def test_parse_codec_error(self):
        """Test parsing codec error"""
        stderr = "Unknown encoder 'libx265'"
        error = FFmpegErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.CODEC_ERROR
        assert "encoder" in error.message.lower()

    def test_parse_disk_full(self):
        """Test parsing disk full error"""
        stderr = "No space left on device"
        error = FFmpegErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.RESOURCE_ERROR
        assert "disk" in error.message.lower() or "space" in error.message.lower()

    def test_parse_moov_atom_error(self):
        """Test parsing moov atom error"""
        stderr = "moov atom not found"
        error = FFmpegErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.INVALID_INPUT
        assert "mp4" in error.message.lower()

    def test_parse_success(self):
        """Test parsing with success return code"""
        stderr = "video:1234kB audio:567kB"
        error = FFmpegErrorParser.parse(stderr, 0)
        
        assert error.message == "No error"

    def test_parse_unknown_error_fallback(self):
        """Test fallback for unknown errors"""
        stderr = "Some strange error occurred"
        error = FFmpegErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.UNKNOWN_ERROR


class TestYtDlpErrorParser:
    """Tests for yt-dlp error parsing"""

    def test_parse_video_unavailable(self):
        """Test parsing video unavailable error"""
        stderr = "ERROR: Video unavailable"
        error = YtDlpErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.PLATFORM_ERROR
        assert "unavailable" in error.message.lower()

    def test_parse_private_video(self):
        """Test parsing private video error"""
        stderr = "ERROR: Private video"
        error = YtDlpErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.PERMISSION_ERROR
        assert "private" in error.message.lower()

    def test_parse_age_restricted(self):
        """Test parsing age-restricted error"""
        stderr = "ERROR: Sign in to confirm your age"
        error = YtDlpErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.PERMISSION_ERROR
        assert "age" in error.message.lower()

    def test_parse_geo_restricted(self):
        """Test parsing geo-restricted error"""
        stderr = "ERROR: Video is geo-restricted"
        error = YtDlpErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.PERMISSION_ERROR
        assert "region" in error.message.lower() or "geo" in error.message.lower()

    def test_parse_http_403(self):
        """Test parsing HTTP 403 error"""
        stderr = "ERROR: HTTP Error 403: Forbidden"
        error = YtDlpErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.PERMISSION_ERROR
        assert "denied" in error.message.lower() or "access" in error.message.lower()

    def test_parse_http_404(self):
        """Test parsing HTTP 404 error"""
        stderr = "ERROR: HTTP Error 404: Not Found"
        error = YtDlpErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.FILE_NOT_FOUND
        assert "not found" in error.message.lower()

    def test_parse_rate_limited(self):
        """Test parsing rate limit error"""
        stderr = "ERROR: HTTP Error 429: Too Many Requests"
        error = YtDlpErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.NETWORK_ERROR
        assert "rate" in error.message.lower() or "limit" in error.message.lower()

    def test_parse_network_error(self):
        """Test parsing network error"""
        stderr = "ERROR: Unable to download webpage"
        error = YtDlpErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.NETWORK_ERROR
        assert "network" in error.message.lower() or "connect" in error.message.lower()

    def test_parse_invalid_url(self):
        """Test parsing invalid URL error"""
        stderr = "ERROR: 'not-a-url' is not a valid URL"
        error = YtDlpErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.INVALID_INPUT
        assert "url" in error.message.lower()

    def test_parse_unsupported_url(self):
        """Test parsing unsupported URL error"""
        stderr = "ERROR: Unsupported URL: https://example.com"
        error = YtDlpErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.INVALID_INPUT
        assert "unsupported" in error.message.lower()

    def test_parse_members_only(self):
        """Test parsing members-only error"""
        stderr = "ERROR: This video is available to this channel's members"
        error = YtDlpErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.PERMISSION_ERROR
        assert "member" in error.message.lower()

    def test_parse_success(self):
        """Test parsing with success return code"""
        stderr = "[download] 100% of 50.00MiB"
        error = YtDlpErrorParser.parse(stderr, 0)
        
        assert error.message == "No error"

    def test_parse_unknown_error_fallback(self):
        """Test fallback for unknown errors"""
        stderr = "Some strange yt-dlp error"
        error = YtDlpErrorParser.parse(stderr, 1)
        
        assert error.category == ErrorCategory.UNKNOWN_ERROR


class TestErrorFormatting:
    """Tests for error formatting functions"""

    def test_format_for_user_basic(self):
        """Test basic user formatting"""
        error = ErrorInfo(
            category=ErrorCategory.FILE_NOT_FOUND,
            message="File not found"
        )
        
        formatted = format_error_for_user(error)
        assert "File not found" in formatted

    def test_format_for_user_with_detail(self):
        """Test user formatting with detail"""
        error = ErrorInfo(
            category=ErrorCategory.FILE_NOT_FOUND,
            message="File not found",
            detail="test.mp4"
        )
        
        formatted = format_error_for_user(error)
        assert "File not found" in formatted
        assert "test.mp4" in formatted

    def test_format_for_user_with_suggestion(self):
        """Test user formatting with suggestion"""
        error = ErrorInfo(
            category=ErrorCategory.FILE_NOT_FOUND,
            message="File not found",
            suggestion="Check the file path"
        )
        
        formatted = format_error_for_user(error, include_suggestion=True)
        assert "Check the file path" in formatted

    def test_format_for_user_without_suggestion(self):
        """Test user formatting without suggestion"""
        error = ErrorInfo(
            category=ErrorCategory.FILE_NOT_FOUND,
            message="File not found",
            suggestion="Check the file path"
        )
        
        formatted = format_error_for_user(error, include_suggestion=False)
        assert "Check the file path" not in formatted

    def test_format_for_log(self):
        """Test log formatting"""
        error = ErrorInfo(
            category=ErrorCategory.FILE_NOT_FOUND,
            message="File not found",
            detail="test.mp4"
        )
        
        formatted = format_error_for_log(error)
        assert "[file_not_found]" in formatted
        assert "File not found" in formatted
        assert "test.mp4" in formatted


class TestConvenienceFunctions:
    """Tests for convenience parsing functions"""

    def test_parse_ffmpeg_error(self):
        """Test quick FFmpeg error parsing"""
        message = parse_ffmpeg_error("No such file or directory", 1)
        assert "not found" in message.lower()

    def test_parse_ytdlp_error(self):
        """Test quick yt-dlp error parsing"""
        message = parse_ytdlp_error("ERROR: Video unavailable", 1)
        assert "unavailable" in message.lower()


class TestRecoverableErrors:
    """Tests for error recoverability"""

    def test_network_error_recoverable(self):
        """Network errors should be recoverable"""
        error = YtDlpErrorParser.parse("HTTP Error 429", 1)
        assert error.is_recoverable

    def test_permission_error_recoverable_ffmpeg(self):
        """FFmpeg permission errors should be recoverable"""
        error = FFmpegErrorParser.parse("Permission denied", 1)
        assert error.is_recoverable

    def test_invalid_input_not_recoverable(self):
        """Invalid input errors should not be recoverable"""
        error = FFmpegErrorParser.parse("Invalid data found", 1)
        assert not error.is_recoverable

    def test_platform_error_not_recoverable(self):
        """Platform errors should not be recoverable"""
        error = YtDlpErrorParser.parse("Video unavailable", 1)
        assert not error.is_recoverable
