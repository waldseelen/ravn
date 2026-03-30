"""
RAVN - Medya Yöneticisi - Ana Uygulama Dosyası
YouTube indirme, video dönüştürme ve altyazı yönetimi
"""

import logging

from ravn_app.core.config_paths import ensure_directories_exist, migrate_all_legacy_files
from ravn_app.core.logging_config import setup_logging


logger = logging.getLogger(__name__)


def main():
    """Uygulamayı başlat"""
    setup_logging()
    ensure_directories_exist()
    migrate_all_legacy_files()

    app = None
    try:
        # Delay UI import so Ctrl+C during heavy stdlib imports does not print traceback.
        from ravn_app.ui.main_window import YouTubeDownloaderApp

        app = YouTubeDownloaderApp()
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
