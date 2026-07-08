"""
RAVN - Error Handling System
Unified error handling with human-readable messages and localization support.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors for grouping and handling"""
    FILE_NOT_FOUND = "file_not_found"
    FILE_ACCESS = "file_access"
    INVALID_INPUT = "invalid_input"
    CODEC_ERROR = "codec_error"
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    RESOURCE_ERROR = "resource_error"
    PLATFORM_ERROR = "platform_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorInfo:
    """Structured error information"""
    category: ErrorCategory
    message: str
    detail: str = ""
    suggestion: str = ""
    is_recoverable: bool = False
    raw_error: str = ""


class FFmpegErrorParser:
    """
    Parse FFmpeg/FFprobe stderr to extract human-readable error messages.
    Maps technical FFmpeg errors to user-friendly messages.
    """

    # Error patterns: (regex, category, message, suggestion)
    ERROR_PATTERNS: List[Tuple[str, ErrorCategory, str, str]] = [
        # File errors
        (r"No such file or directory",
         ErrorCategory.FILE_NOT_FOUND,
         "File not found",
         "Check that the file path is correct and the file exists."),

        (r"Permission denied",
         ErrorCategory.PERMISSION_ERROR,
         "Permission denied",
         "Check file permissions or try running as administrator."),

        (r"Could not open file",
         ErrorCategory.FILE_ACCESS,
         "Cannot open file",
         "The file may be locked by another program or corrupted."),

        (r"No space left on device",
         ErrorCategory.RESOURCE_ERROR,
         "Disk full",
         "Free up disk space and try again."),

        # Input/format errors
        (r"Invalid data found when processing input",
         ErrorCategory.INVALID_INPUT,
         "Invalid or corrupted input file",
         "The file may be corrupted. Try re-downloading or using a different file."),

        (r"does not contain any stream",
         ErrorCategory.INVALID_INPUT,
         "No media streams found",
         "The file does not contain valid video or audio data."),

        (r"moov atom not found",
         ErrorCategory.INVALID_INPUT,
         "Invalid MP4 file",
         "The MP4 file is incomplete or corrupted. Try downloading again."),

        (r"decode_slice_header error",
         ErrorCategory.INVALID_INPUT,
         "Video decoding error",
         "The video file may be corrupted or use an unsupported format."),

        (r"Invalid argument",
         ErrorCategory.INVALID_INPUT,
         "Invalid parameter",
         "One of the conversion parameters is not valid."),

        # Codec errors
        (r"Unknown encoder '([^']+)'",
         ErrorCategory.CODEC_ERROR,
         "Unknown encoder",
         "The requested encoder is not installed. Try using a different codec."),

        (r"Encoder .+ not found",
         ErrorCategory.CODEC_ERROR,
         "Encoder not available",
         "Install the required codec or use a different format."),

        (r"Unknown decoder",
         ErrorCategory.CODEC_ERROR,
         "Unknown decoder",
         "The input file uses an unsupported codec."),

        (r"Unsupported codec",
         ErrorCategory.CODEC_ERROR,
         "Unsupported codec",
         "This codec is not supported by your FFmpeg installation."),

        # Size/limit errors
        (r"Avi file size limit",
         ErrorCategory.RESOURCE_ERROR,
         "Output file too large",
         "The output exceeds the format's size limit. Try splitting the file."),

        (r"Output file is empty",
         ErrorCategory.INVALID_INPUT,
         "No output produced",
         "The conversion produced no output. Check input file and settings."),

        # Hardware errors
        (r"Cannot initialize .* codec",
         ErrorCategory.CODEC_ERROR,
         "Codec initialization failed",
         "The codec could not be initialized. Try using software encoding."),

        (r"hw accel",
         ErrorCategory.CODEC_ERROR,
         "Hardware acceleration error",
         "Hardware acceleration failed. Try disabling GPU encoding."),
    ]

    @classmethod
    def parse(cls, stderr: str, return_code: int = 1) -> ErrorInfo:
        """
        Parse FFmpeg stderr and return structured error info.

        Args:
            stderr: FFmpeg stderr output
            return_code: Process return code

        Returns:
            ErrorInfo with parsed error details
        """
        if return_code == 0:
            return ErrorInfo(
                category=ErrorCategory.UNKNOWN_ERROR,
                message="No error",
                raw_error=stderr
            )

        for pattern, category, message, suggestion in cls.ERROR_PATTERNS:
            match = re.search(pattern, stderr, re.IGNORECASE)
            if match:
                # Extract matched groups if any
                detail = ""
                if match.groups():
                    detail = match.group(1)

                return ErrorInfo(
                    category=category,
                    message=message,
                    detail=detail,
                    suggestion=suggestion,
                    is_recoverable=category in (
                        ErrorCategory.RESOURCE_ERROR,
                        ErrorCategory.PERMISSION_ERROR
                    ),
                    raw_error=stderr
                )

        # Fallback: extract last error line
        lines = [line.strip() for line in stderr.split('\n') if line.strip()]
        error_line = ""
        for line in reversed(lines):
            if 'error' in line.lower() or 'failed' in line.lower():
                error_line = line[:200]
                break

        return ErrorInfo(
            category=ErrorCategory.UNKNOWN_ERROR,
            message=error_line or "FFmpeg operation failed",
            suggestion="Check the technical details for more information.",
            raw_error=stderr
        )


class YtDlpErrorParser:
    """
    Parse yt-dlp stderr to extract human-readable error messages.
    Maps yt-dlp errors to user-friendly messages.
    """

    # Error patterns: (regex, category, message, suggestion)
    ERROR_PATTERNS: List[Tuple[str, ErrorCategory, str, str]] = [
        # Availability errors
        (r"Video unavailable",
         ErrorCategory.PLATFORM_ERROR,
         "Video is unavailable",
         "The video may have been removed or made private."),

        (r"Private video",
         ErrorCategory.PERMISSION_ERROR,
         "Video is private",
         "This is a private video. You need the owner's permission to access it."),

        (r"Sign in to confirm your age",
         ErrorCategory.PERMISSION_ERROR,
         "Age-restricted video",
         "Log in to your account to access age-restricted content."),

        (r"members-only|channel.s members",
         ErrorCategory.PERMISSION_ERROR,
         "Members-only content",
         "This content is only available to channel members."),

        (r"Premiere will begin",
         ErrorCategory.PLATFORM_ERROR,
         "Video not yet available",
         "This is a scheduled premiere that hasn't started yet."),

        (r"live event will begin",
         ErrorCategory.PLATFORM_ERROR,
         "Live stream not started",
         "The live stream hasn't started yet."),

        # Extraction errors
        (r"Unable to extract",
         ErrorCategory.PLATFORM_ERROR,
         "Extraction failed",
         "Could not extract video information. The site may have changed."),

        (r"Unsupported URL",
         ErrorCategory.INVALID_INPUT,
         "Unsupported URL",
         "This URL is not supported. Try a different platform."),

        (r"is not a valid URL",
         ErrorCategory.INVALID_INPUT,
         "Invalid URL",
         "Please enter a valid video URL."),

        (r"No video formats",
         ErrorCategory.PLATFORM_ERROR,
         "No formats available",
         "No downloadable video formats found."),

        # Network errors
        (r"HTTP Error 403",
         ErrorCategory.PERMISSION_ERROR,
         "Access denied",
         "The server denied access. The video may be geo-restricted."),

        (r"HTTP Error 404",
         ErrorCategory.FILE_NOT_FOUND,
         "Video not found",
         "The video could not be found. It may have been deleted."),

        (r"HTTP Error 429",
         ErrorCategory.NETWORK_ERROR,
         "Rate limited",
         "Too many requests. Wait a few minutes and try again."),

        (r"HTTP Error 5\d\d",
         ErrorCategory.NETWORK_ERROR,
         "Server error",
         "The server is experiencing issues. Try again later."),

        (r"Unable to download webpage",
         ErrorCategory.NETWORK_ERROR,
         "Network error",
         "Could not connect to the server. Check your internet connection."),

        (r"Connection reset|Connection refused",
         ErrorCategory.NETWORK_ERROR,
         "Connection failed",
         "Connection was interrupted. Check your internet connection."),

        (r"timed? out",
         ErrorCategory.NETWORK_ERROR,
         "Connection timeout",
         "The server took too long to respond. Try again."),

        # Geo-restriction
        (r"Geo-restricted|geo.restricted|not available in your",
         ErrorCategory.PERMISSION_ERROR,
         "Geo-restricted content",
         "This content is not available in your region."),

        # Copyright
        (r"copyright|blocked|DMCA",
         ErrorCategory.PERMISSION_ERROR,
         "Content blocked",
         "This content has been blocked due to copyright."),
    ]

    @classmethod
    def parse(cls, stderr: str, return_code: int = 1) -> ErrorInfo:
        """
        Parse yt-dlp stderr and return structured error info.

        Args:
            stderr: yt-dlp stderr output
            return_code: Process return code

        Returns:
            ErrorInfo with parsed error details
        """
        if return_code == 0:
            return ErrorInfo(
                category=ErrorCategory.UNKNOWN_ERROR,
                message="No error",
                raw_error=stderr
            )

        for pattern, category, message, suggestion in cls.ERROR_PATTERNS:
            if re.search(pattern, stderr, re.IGNORECASE):
                return ErrorInfo(
                    category=category,
                    message=message,
                    suggestion=suggestion,
                    is_recoverable=category == ErrorCategory.NETWORK_ERROR,
                    raw_error=stderr
                )

        # Fallback: extract error message
        lines = [line.strip() for line in stderr.split('\n') if line.strip()]
        error_line = ""
        for line in reversed(lines):
            if 'error' in line.lower():
                # Clean up the line
                error_line = re.sub(r'^ERROR:\s*', '', line, flags=re.IGNORECASE)
                error_line = error_line[:200]
                break

        return ErrorInfo(
            category=ErrorCategory.UNKNOWN_ERROR,
            message=error_line or "Download failed",
            suggestion="Check the URL and try again.",
            raw_error=stderr
        )


def format_error_for_user(error_info: ErrorInfo, include_suggestion: bool = True) -> str:
    """
    Format error info for display to user.

    Args:
        error_info: Structured error information
        include_suggestion: Whether to include the suggestion

    Returns:
        Formatted error string
    """
    parts = [error_info.message]

    if error_info.detail:
        parts.append(f"({error_info.detail})")

    if include_suggestion and error_info.suggestion:
        parts.append(f"\n{error_info.suggestion}")

    return " ".join(parts) if not include_suggestion else "\n".join(parts)


def format_error_for_log(error_info: ErrorInfo) -> str:
    """
    Format error info for logging.

    Args:
        error_info: Structured error information

    Returns:
        Formatted log string
    """
    return (
        f"[{error_info.category.value}] {error_info.message}"
        f"{f' - {error_info.detail}' if error_info.detail else ''}"
    )


# Convenience functions for quick error parsing
def parse_ffmpeg_error(stderr: str, return_code: int = 1) -> str:
    """Quick parse FFmpeg error to user message"""
    error = FFmpegErrorParser.parse(stderr, return_code)
    return error.message


def parse_ytdlp_error(stderr: str, return_code: int = 1) -> str:
    """Quick parse yt-dlp error to user message"""
    error = YtDlpErrorParser.parse(stderr, return_code)
    return error.message


class Aria2cErrorParser:
    """
    Parse aria2c stderr/exit codes to extract human-readable error messages.
    Maps aria2c errorCode values to Turkish user-friendly messages.
    """

    ERROR_PATTERNS: List[Tuple[str, ErrorCategory, str, str]] = [
        (r"errorCode=2|timed? out",
         ErrorCategory.NETWORK_ERROR,
         "Zaman aşımı",
         "Bağlantı zaman aşımına uğradı. Tekrar deneyin."),

        (r"errorCode=3|resource not found",
         ErrorCategory.FILE_NOT_FOUND,
         "Kaynak bulunamadı",
         "İndirme kaynağı bulunamadı. Bağlantıyı kontrol edin."),

        (r"errorCode=6|network problem|connection refused",
         ErrorCategory.NETWORK_ERROR,
         "Ağ hatası",
         "İnternet bağlantınızı kontrol edin ve tekrar deneyin."),

        (r"errorCode=9|not enough disk|no space left",
         ErrorCategory.RESOURCE_ERROR,
         "Disk dolu",
         "Disk alanı yetersiz. Alan açıp tekrar deneyin."),

        (r"errorCode=13|file already exists",
         ErrorCategory.FILE_ACCESS,
         "Dosya zaten mevcut",
         "Hedef dosya zaten mevcut. Farklı bir konum seçin."),

        (r"errorCode=24|unauthorized|authentication",
         ErrorCategory.PERMISSION_ERROR,
         "Kimlik doğrulama hatası",
         "Erişim için kimlik bilgileri gerekiyor."),

        (r"errorCode=1|unknown error",
         ErrorCategory.UNKNOWN_ERROR,
         "Bilinmeyen hata",
         "Teknik detaylar için günlükleri inceleyin."),
    ]

    @classmethod
    def parse(cls, stderr: str, return_code: int = 1) -> ErrorInfo:
        """
        Parse aria2c stderr and return structured error info.

        Args:
            stderr: aria2c stderr output
            return_code: Process return code

        Returns:
            ErrorInfo with parsed error details
        """
        if return_code == 0:
            return ErrorInfo(
                category=ErrorCategory.UNKNOWN_ERROR,
                message="No error",
                raw_error=stderr,
            )

        for pattern, category, message, suggestion in cls.ERROR_PATTERNS:
            if re.search(pattern, stderr, re.IGNORECASE):
                return ErrorInfo(
                    category=category,
                    message=message,
                    suggestion=suggestion,
                    is_recoverable=category in (
                        ErrorCategory.NETWORK_ERROR,
                        ErrorCategory.RESOURCE_ERROR,
                    ),
                    raw_error=stderr,
                )

        lines = [ln.strip() for ln in stderr.splitlines() if ln.strip()]
        error_line = ""
        for line in reversed(lines):
            if "error" in line.lower():
                error_line = line[:200]
                break

        return ErrorInfo(
            category=ErrorCategory.UNKNOWN_ERROR,
            message=error_line or "İndirme başarısız",
            suggestion="Teknik detaylar için günlükleri inceleyin.",
            raw_error=stderr,
        )


def parse_aria2c_error(stderr: str, return_code: int = 1) -> str:
    """Quick parse aria2c error to user message"""
    error = Aria2cErrorParser.parse(stderr, return_code)
    return error.message
