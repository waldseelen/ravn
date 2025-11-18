"""
RAVN - Medya Yöneticisi - Ana Uygulama Dosyası
YouTube indirme, video dönüştürme ve altyazı yönetimi
"""

from ravn_app.ui.main_window import YouTubeDownloaderApp


def main():
    """Uygulamayı başlat"""
    app = YouTubeDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
