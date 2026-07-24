"""Local crash reporter for RAVN.

Captures unhandled exceptions and writes detailed crash report files locally.
No network calls or third-party SDKs are involved -- 100% offline file capture.
User can disable crash file creation via the `crash_reporting_enabled` config setting.
"""

import logging
import platform
import sys
import traceback
from datetime import datetime
from typing import Any, Optional, Type

from ravn_app import __version__
from ravn_app.core.database import ConfigManager
from ravn_app.core.logging_config import get_log_directory

logger = logging.getLogger(__name__)

_original_excepthook = sys.excepthook


def _handle_unhandled_exception(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_tb: Optional[Any],
) -> None:
    """Custom sys.excepthook to write crash report files when enabled."""
    try:
        config_mgr = ConfigManager()
        enabled = config_mgr.get("crash_reporting_enabled", True)
    except Exception:  # Defensive fallback if config fails to load
        enabled = True

    if not enabled:
        _original_excepthook(exc_type, exc_value, exc_tb)
        return

    try:
        log_dir = get_log_directory()
        crashes_dir = log_dir.parent / "crashes"
        crashes_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        crash_file = crashes_dir / f"crash_{timestamp}.txt"

        formatted_tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        report_lines = [
            f"Timestamp: {datetime.now().isoformat()}",
            f"RAVN Version: {__version__}",
            f"OS / Platform: {platform.platform()}",
            f"Python Version: {sys.version}",
            "--- Traceback ---",
            formatted_tb,
        ]

        crash_file.write_text("\n".join(report_lines), encoding="utf-8")
        logger.error("Unhandled exception caught -- crash report written to %s", crash_file)
    except Exception as err:
        logger.error("Failed to write crash report: %s", err)

    _original_excepthook(exc_type, exc_value, exc_tb)


def install_crash_handler() -> None:
    """Set sys.excepthook to RAVN's custom crash report handler."""
    sys.excepthook = _handle_unhandled_exception
