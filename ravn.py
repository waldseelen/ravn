"""
RAVN - Medya Yöneticisi - Ana Uygulama Dosyası
YouTube indirme, video dönüştürme ve altyazı yönetimi
"""

from ravn_app.ui.main_window import YouTubeDownloaderApp
from ravn_app.core.config_paths import ensure_directories_exist, migrate_all_legacy_files
from ravn_app.core.logging_config import setup_logging


def main():
    """Uygulamayı başlat"""
    setup_logging()
    ensure_directories_exist()
    migrate_all_legacy_files()
    app = YouTubeDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
