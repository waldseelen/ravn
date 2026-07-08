"""
RAVN - Structured Logging System
Unified logging configuration for all modules
"""

import json
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def get_log_directory() -> Path:
    """Get the log directory based on OS"""
    if sys.platform == 'win32':
        base_dir = Path(os.environ.get('APPDATA', Path.home()))
        log_dir = base_dir / 'ravn' / 'logs'
    elif sys.platform == 'darwin':
        log_dir = Path.home() / 'Library' / 'Logs' / 'ravn'
    else:  # Linux and others
        xdg_state = os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local' / 'state'))
        log_dir = Path(xdg_state) / 'ravn' / 'logs'

        # Fallback to ~/.config/ravn/logs if state doesn't exist
        if not Path(xdg_state).exists():
            log_dir = Path.home() / '.config' / 'ravn' / 'logs'

    return log_dir


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        from datetime import timezone
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add extra fields if any
        if hasattr(record, 'extra_data'):
            log_entry['extra'] = record.extra_data

        return json.dumps(log_entry)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability"""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        # Don't colorize on Windows without proper terminal support
        if sys.platform == 'win32' and not os.environ.get('TERM'):
            return super().format(record)

        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class SafeConsoleWriter:
    """Write console logs without crashing on non-UTF terminals."""

    def __init__(self, stream):
        self._stream = stream

    def write(self, message: str) -> int:
        try:
            return self._stream.write(message)
        except UnicodeEncodeError:
            encoding = getattr(self._stream, "encoding", None) or "utf-8"
            safe_message = message.encode(encoding, errors="backslashreplace").decode(encoding, errors="ignore")
            return self._stream.write(safe_message)

    def flush(self) -> None:
        self._stream.flush()

    def isatty(self):
        return self._stream.isatty()

    @property
    def encoding(self):
        return getattr(self._stream, "encoding", None)


# Initialize logging when module is imported
_initialized = False


def setup_logging(
    level: int = logging.INFO,
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    log_file_name: str = 'ravn.log',
    max_file_size_mb: int = 10,
    backup_count: int = 5,
    json_format: bool = False
) -> logging.Logger:
    """
    Set up the RAVN logging system

    Args:
        level: Logging level (default: INFO)
        enable_file_logging: Write logs to file
        enable_console_logging: Write logs to console
        log_file_name: Name of the log file
        max_file_size_mb: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        json_format: Use JSON format for file logs

    Returns:
        Root logger instance
    """
    global _initialized

    # Get or create root logger for RAVN
    root_logger = logging.getLogger('ravn_app')

    # Make setup idempotent for repeated imports/startup paths.
    if getattr(root_logger, "_ravn_logging_initialized", False):
        root_logger.setLevel(level)
        return root_logger

    # Clear any existing handlers
    root_logger.handlers.clear()

    root_logger.setLevel(level)
    root_logger.propagate = False

    # Console handler
    if enable_console_logging:
        console_handler = logging.StreamHandler(SafeConsoleWriter(sys.stdout))
        console_handler.setLevel(level)

        console_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        console_handler.setFormatter(ColoredFormatter(console_format, datefmt='%H:%M:%S'))

        root_logger.addHandler(console_handler)

    # File handler
    if enable_file_logging:
        log_dir = get_log_directory()
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / log_file_name

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)

        if json_format:
            file_handler.setFormatter(JsonFormatter())
        else:
            file_format = '%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s'
            file_handler.setFormatter(logging.Formatter(file_format))

        root_logger.addHandler(file_handler)

    # Log startup info
    root_logger.info(f"RAVN logging initialized - level={logging.getLevelName(level)}")
    if enable_file_logging:
        root_logger.info(f"Log file: {log_dir / log_file_name}")

    # Custom idempotency flag read back via getattr() at the top of this function.
    root_logger._ravn_logging_initialized = True  # type: ignore[attr-defined]
    _initialized = True
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_operation(
    logger: logging.Logger,
    operation: str,
    success: bool,
    duration_seconds: Optional[float] = None,
    **extra_data
):
    """
    Log an operation result with structured data

    Args:
        logger: Logger instance
        operation: Name of the operation
        success: Whether the operation succeeded
        duration_seconds: Duration of the operation
        **extra_data: Additional data to log
    """
    status = "completed" if success else "failed"

    message = f"{operation} {status}"
    if duration_seconds is not None:
        message += f" in {duration_seconds:.2f}s"

    extra = {
        'operation': operation,
        'success': success,
        'duration_seconds': duration_seconds,
        **extra_data
    }

    record_level = logging.INFO if success else logging.ERROR

    # Create a record with extra data
    record = logger.makeRecord(
        logger.name,
        record_level,
        '',
        0,
        message,
        (),
        None
    )
    record.extra_data = extra

    logger.handle(record)


def log_ffmpeg_operation(
    logger: logging.Logger,
    command: str,
    return_code: int,
    stderr: str = "",
    duration_seconds: Optional[float] = None
):
    """Log an FFmpeg operation with stderr details"""
    success = return_code == 0

    log_operation(
        logger,
        "FFmpeg",
        success,
        duration_seconds,
        command=command,
        return_code=return_code,
        stderr=stderr[:500] if len(stderr) > 500 else stderr
    )


def log_ytdlp_operation(
    logger: logging.Logger,
    url: str,
    success: bool,
    output_file: Optional[str] = None,
    error: Optional[str] = None,
    duration_seconds: Optional[float] = None
):
    """Log a yt-dlp operation"""
    log_operation(
        logger,
        "yt-dlp download",
        success,
        duration_seconds,
        url=url,
        output_file=output_file,
        error=error
    )


def ensure_logging_initialized():
    """Ensure logging is initialized"""
    global _initialized
    if not _initialized:
        setup_logging()
        _initialized = True


# Auto-initialize with defaults when imported
ensure_logging_initialized()
