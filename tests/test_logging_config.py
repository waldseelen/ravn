"""
Logging Configuration Tests
"""

import pytest
import os
import sys
import tempfile
import logging
from pathlib import Path
from unittest.mock import patch

from ravn_app.core.logging_config import (
    get_log_directory, setup_logging, get_logger,
    log_operation, log_ffmpeg_operation, log_ytdlp_operation,
    JsonFormatter, ColoredFormatter, SafeConsoleWriter
)


class TestLogDirectory:
    """Tests for log directory resolution"""

    def test_get_log_directory_returns_path(self):
        """Log directory should return a Path"""
        log_dir = get_log_directory()
        assert isinstance(log_dir, Path)

    @patch('sys.platform', 'win32')
    @patch.dict(os.environ, {'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming'})
    def test_windows_log_directory(self):
        """Windows should use APPDATA"""
        log_dir = get_log_directory()
        assert 'ravn' in str(log_dir)
        assert 'logs' in str(log_dir)

    @patch('sys.platform', 'linux')
    @patch.dict(os.environ, {'XDG_STATE_HOME': ''}, clear=False)
    def test_linux_log_directory(self):
        """Linux should use config directory"""
        log_dir = get_log_directory()
        assert 'ravn' in str(log_dir)
        assert 'logs' in str(log_dir)


class TestSetupLogging:
    """Tests for logging setup"""

    def teardown_method(self):
        """Clean up loggers after each test"""
        logger = logging.getLogger('ravn_app')
        logger.handlers.clear()
        if hasattr(logger, '_ravn_logging_initialized'):
            delattr(logger, '_ravn_logging_initialized')

    def test_setup_logging_returns_logger(self):
        """setup_logging should return a logger"""
        logger = setup_logging(enable_file_logging=False)
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'ravn_app'

    def test_setup_logging_sets_level(self):
        """Logging level should be configurable"""
        logger = setup_logging(level=logging.DEBUG, enable_file_logging=False)
        assert logger.level == logging.DEBUG

    def test_setup_logging_console_handler(self):
        """Console handler should be added when enabled"""
        logger = setup_logging(
            enable_console_logging=True,
            enable_file_logging=False
        )
        
        console_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
        ]
        assert len(console_handlers) == 1

    def test_setup_logging_no_console(self):
        """Console handler should not be added when disabled"""
        logger = setup_logging(
            enable_console_logging=False,
            enable_file_logging=False
        )
        
        console_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
        ]
        assert len(console_handlers) == 0

    def test_setup_logging_file_handler(self):
        """File handler should be added when enabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('ravn_app.core.logging_config.get_log_directory',
                       return_value=Path(tmpdir)):
                logger = setup_logging(
                    enable_console_logging=False,
                    enable_file_logging=True
                )
                
                from logging.handlers import RotatingFileHandler
                file_handlers = [
                    h for h in logger.handlers
                    if isinstance(h, RotatingFileHandler)
                ]
                assert len(file_handlers) == 1
                
                # Close handlers to release file lock (Windows)
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)

    def test_setup_logging_is_idempotent(self):
        """Repeated setup should not duplicate handlers or startup logs."""
        logger = setup_logging(enable_file_logging=False)
        first_handlers = list(logger.handlers)

        logger_again = setup_logging(enable_file_logging=False)

        assert logger_again is logger
        assert logger.handlers == first_handlers
        assert len(logger.handlers) == 1


class TestSafeConsoleWriter:
    """Tests for console output safety wrapper."""

    def test_safe_console_writer_falls_back_on_unicode_encode_error(self):
        """Writer should escape unsupported characters instead of crashing."""
        class Cp1252LikeStream:
            encoding = 'cp1252'

            def __init__(self):
                self.writes = []

            def write(self, message):
                message.encode(self.encoding)
                self.writes.append(message)
                return len(message)

            def flush(self):
                return None

            def isatty(self):
                return False

        stream = Cp1252LikeStream()
        writer = SafeConsoleWriter(stream)

        count = writer.write('Varsayılan platform indiricileri kaydedildi')

        assert count > 0
        assert stream.writes
        assert '\\u0131' in stream.writes[-1]


class TestGetLogger:
    """Tests for get_logger function"""

    def test_get_logger_returns_logger(self):
        """get_logger should return a logger"""
        logger = get_logger('test.module')
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'test.module'

    def test_get_logger_same_name_same_instance(self):
        """Same name should return same logger"""
        logger1 = get_logger('test.same')
        logger2 = get_logger('test.same')
        assert logger1 is logger2


class TestJsonFormatter:
    """Tests for JSON formatter"""

    def test_json_formatter_output(self):
        """JSON formatter should produce valid JSON"""
        import json
        
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed['level'] == 'INFO'
        assert parsed['message'] == 'Test message'
        assert 'timestamp' in parsed

    def test_json_formatter_with_exception(self):
        """JSON formatter should include exception info"""
        import json
        
        formatter = JsonFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            record = logging.LogRecord(
                name='test',
                level=logging.ERROR,
                pathname='test.py',
                lineno=10,
                msg='Error occurred',
                args=(),
                exc_info=sys.exc_info()
            )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert 'exception' in parsed
        assert 'ValueError' in parsed['exception']


class TestColoredFormatter:
    """Tests for colored formatter"""

    def test_colored_formatter_formats(self):
        """Colored formatter should format messages"""
        formatter = ColoredFormatter('%(levelname)s: %(message)s')
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        assert 'Test message' in output


class TestLogOperations:
    """Tests for operation logging helpers"""

    def setup_method(self):
        """Setup test logger"""
        self.logger = logging.getLogger('test.operations')
        self.logger.setLevel(logging.DEBUG)
        self.handler = logging.handlers.MemoryHandler(capacity=100)
        self.logger.addHandler(self.handler)

    def teardown_method(self):
        """Clean up"""
        self.logger.handlers.clear()

    def test_log_operation_success(self):
        """log_operation should log successful operations"""
        log_operation(
            self.logger,
            "Test Operation",
            success=True,
            duration_seconds=1.5
        )
        
        self.handler.flush()
        assert len(self.handler.buffer) == 1
        record = self.handler.buffer[0]
        assert record.levelno == logging.INFO

    def test_log_operation_failure(self):
        """log_operation should log failed operations at ERROR level"""
        log_operation(
            self.logger,
            "Test Operation",
            success=False,
            duration_seconds=1.5
        )
        
        self.handler.flush()
        assert len(self.handler.buffer) == 1
        record = self.handler.buffer[0]
        assert record.levelno == logging.ERROR

    def test_log_ffmpeg_operation(self):
        """log_ffmpeg_operation should log FFmpeg operations"""
        log_ffmpeg_operation(
            self.logger,
            command="ffmpeg -i input.mp4 output.mp4",
            return_code=0,
            stderr="",
            duration_seconds=5.0
        )
        
        self.handler.flush()
        assert len(self.handler.buffer) == 1

    def test_log_ytdlp_operation(self):
        """log_ytdlp_operation should log yt-dlp operations"""
        log_ytdlp_operation(
            self.logger,
            url="https://youtube.com/watch?v=test",
            success=True,
            output_file="/path/to/video.mp4",
            duration_seconds=30.0
        )
        
        self.handler.flush()
        assert len(self.handler.buffer) == 1


class TestLogDirectoryCreation:
    """Test log directory creation"""

    def test_log_directory_created(self):
        """Log directory should be created if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / 'subdir' / 'logs'
            
            with patch('ravn_app.core.logging_config.get_log_directory',
                       return_value=log_dir):
                logger = setup_logging(
                    enable_console_logging=False,
                    enable_file_logging=True
                )
                
                assert log_dir.exists()
                
                # Close handlers to release file lock (Windows)
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)
