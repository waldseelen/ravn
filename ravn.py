"""
RAVN - Media Pipeline Backend Entry Point
Launches the Python core services & FastAPI transport layer for the Tauri GUI & CLI.
"""

import logging
import sys

from ravn_app.api.main import serve
from ravn_app.core.config_paths import ensure_directories_exist, migrate_all_legacy_files
from ravn_app.core.crash_reporter import install_crash_handler
from ravn_app.core.logging_config import setup_logging
from ravn_app.core.tool_health import get_tool_health_checker
from ravn_app.utils.bundled_tools import configure_bundled_tools_path
from ravn_app.utils.ffmpeg_checker import configure_ffmpeg_runtime

logger = logging.getLogger(__name__)


def check_tool_dependencies():
    """Check tool dependencies and log status summary"""
    checker = get_tool_health_checker()
    summary = checker.get_health_summary()

    if summary['missing_required']:
        logger.error("CRITICAL: Missing required tools: %s", ", ".join(summary['missing_required']))
    if summary['missing_optional']:
        logger.warning("Missing optional tools: %s", ", ".join(summary['missing_optional']))
    if summary['overall_status'] == 'healthy':
        logger.info("Tool health check: All required and optional tools are available")


def main():
    """Start the RAVN backend API server"""
    setup_logging()
    install_crash_handler()
    ensure_directories_exist()
    migrate_all_legacy_files()
    configure_bundled_tools_path()
    configure_ffmpeg_runtime()
    check_tool_dependencies()

    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    logger.info("Starting RAVN Backend API Service...")
    serve(port=port)


if __name__ == "__main__":
    main()
