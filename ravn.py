"""
RAVN - Medya Yöneticisi - Ana Uygulama Dosyası
YouTube indirme, video dönüştürme ve altyazı yönetimi
"""

import logging

from ravn_app.core.config_paths import ensure_directories_exist, migrate_all_legacy_files
from ravn_app.core.logging_config import setup_logging
from ravn_app.core.tool_health import get_tool_health_checker
from ravn_app.utils.bundled_tools import configure_bundled_tools_path
from ravn_app.utils.ffmpeg_checker import configure_ffmpeg_runtime


logger = logging.getLogger(__name__)


def check_tool_dependencies():
    """Check tool dependencies and log warnings for missing tools"""
    checker = get_tool_health_checker()
    summary = checker.get_health_summary()
    
    if summary['missing_required']:
        logger.error("="*60)
        logger.error("CRITICAL: Required tools are missing!")
        logger.error("Missing tools: %s", ", ".join(summary['missing_required']))
        logger.error("="*60)
        logger.error("The application cannot function properly without these tools.")
        logger.error("Please install the missing tools before continuing.")
        logger.error("See README.md for installation instructions.")
        logger.error("="*60)
        
        # List affected features
        for tool in summary['missing_required']:
            features = checker.get_affected_features(tool)
            if features:
                logger.error("  %s affects: %s", tool, ", ".join(features))
        logger.error("="*60)
        
    if summary['missing_optional']:
        logger.warning("="*60)
        logger.warning("Optional tools are missing - some features will be unavailable")
        logger.warning("Missing optional tools: %s", ", ".join(summary['missing_optional']))
        
        # List affected features
        for tool in summary['missing_optional']:
            features = checker.get_affected_features(tool)
            if features:
                logger.warning("  %s affects: %s", tool, ", ".join(features))
        
        logger.warning("The application will continue with limited functionality.")
        logger.warning("Install these tools to enable all features.")
        logger.warning("="*60)
    
    if summary['overall_status'] == 'healthy':
        logger.info("Tool health check: All required and optional tools are available")
        for tool_name, tool_info in summary['tools'].items():
            if tool_info.status.value == "available":
                logger.debug("%s: %s", tool_name, tool_info.version or "version unknown")


from ravn_app.core.crash_reporter import install_crash_handler


def main():
    """Uygulamayı başlat"""
    setup_logging()
    install_crash_handler()
    ensure_directories_exist()
    migrate_all_legacy_files()
    
    # Make every bundled tool (ffmpeg/ffprobe, yt-dlp, aria2c) visible before any
    # runtime/tool checks, so a freshly unzipped build finds what it shipped with
    # and child processes (yt-dlp muxing via ffmpeg) resolve them too.
    configure_bundled_tools_path()
    configure_ffmpeg_runtime()

    # Check tool dependencies at startup
    check_tool_dependencies()

    app = None
    try:
        # Delay UI import so Ctrl+C during heavy stdlib imports does not print traceback.
        from ravn_app.ui.main_window import YouTubeDownloaderApp

        app = YouTubeDownloaderApp()
        
        try:
            import sys
            if hasattr(sys, "frozen"):
                import pyi_splash
                if pyi_splash.is_alive():
                    pyi_splash.update_text("Arayüz yükleniyor...")
                    pyi_splash.close()
        except Exception:
            pass

        app.mainloop()
    except KeyboardInterrupt:
        logger.info("Uygulama Ctrl+C ile kapatildi")
        if app is not None:
            try:
                quit_app = getattr(app, "_quit_app", None)
                if callable(quit_app):
                    quit_app()
                else:
                    app.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    main()
