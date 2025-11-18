"""
Ana uygulama penceresi - CustomTkinter arayüzü (Sekmeli)
"""

import customtkinter as ctk
from customtkinter import filedialog
from PIL import Image
import os
import sys

from ravn_app.ui.converter_tab import ConverterTab
from ravn_app.ui.subtitle_tab import SubtitleTab
from ravn_app.ui.history_settings_tab import HistoryTab, SettingsTab
from ravn_app.core.database import DatabaseManager, ConfigManager

import logging
import warnings

# Suppress noisy RuntimeWarning about module found in sys.modules when running as -m
warnings.filterwarnings(
    "ignore",
    message=r".*found in sys.modules after import of package 'ravn_app.ui'.*",
    category=RuntimeWarning,
)

logger = logging.getLogger("ravn.ui.main")
if not logger.handlers:
    # Configure a simple console handler (won't override user-level logging)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[RAVN/UI] %(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)


class YouTubeDownloaderApp(ctk.CTk):
    """Ana uygulama penceresi - Sekmeli arayüz"""

    def __init__(self):
        super().__init__()

        # Tema ve pencere ayarları
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("RAVN - Media Manager")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        # Database ve Config yönetimi (Faz 4)
        self.db_manager = DatabaseManager("ravn_history.db")
        self.config_manager = ConfigManager("ravn_config.json")

        # Tema yönetimi
        self.current_theme = self.config_manager.get('theme', 'nordic')
        self._setup_ui()

    def __del__(self):
        """Uygulama kapanırken veritabanını kapat"""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()

    def _setup_ui(self):
        """UI bileşenlerini kur"""
        # Üst başlık
        header_frame = ctk.CTkFrame(self, fg_color="#1a1a1a")
        header_frame.pack(fill="x", padx=0, pady=0)

        title = ctk.CTkLabel(
            header_frame,
            text="🎬 RAVN - Media Manager",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(pady=15)

        # Sekmeli arayüz
        self.tabview = ctk.CTkTabview(self, anchor="nw")
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Sekme: İndir (Faz 1)
        download_tab = self.tabview.add("📥 İndir")
        self._setup_download_tab(download_tab)

        # Sekme: Dönüştür (Faz 2)
        converter_tab = self.tabview.add("🔄 Dönüştür")
        self._setup_converter_tab(converter_tab)

        # Sekme: Altyazı (Faz 3)
        subtitle_tab = self.tabview.add("📝 Altyazı")
        self._setup_subtitle_tab(subtitle_tab)

        # Sekme: Geçmiş (Faz 4)
        history_tab = self.tabview.add("📚 Geçmiş")
        self._setup_history_tab(history_tab)

        # Sekme: Ayarlar (Faz 4 & 5)
        settings_tab = self.tabview.add("⚙️ Ayarlar")
        self._setup_settings_tab_full(settings_tab)

        # Alt durum çubuğu
        footer_frame = ctk.CTkFrame(self, fg_color="#1a1a1a")
        footer_frame.pack(fill="x", padx=0, pady=0)

        status = ctk.CTkLabel(
            footer_frame,
            text="Hazır • v1.0.0",
            font=ctk.CTkFont(size=10),
            text_color="#888888"
        )
        status.pack(pady=5)

    def _setup_download_tab(self, tab):
        """İndirme sekmesini kur"""
        label = ctk.CTkLabel(
            tab,
            text="📥 YouTube İndirici",
            font=("Arial", 18, "bold")
        )
        label.pack(pady=20)

        info = ctk.CTkLabel(
            tab,
            text="Bu sekme Faz 0 bileşenleri ile doldurulacak\n(Mevcut downloader özelliği)",
            justify="center",
            text_color="#999999"
        )
        info.pack(pady=20)

        # TODO: Downloader UI'ı buraya ekle

    def _setup_converter_tab(self, tab):
        """Dönüştürme sekmesini kur (Faz 2)"""
        converter = ConverterTab(tab, fg_color="transparent")
        converter.pack(fill="both", expand=True)

    def _setup_subtitle_tab(self, tab):
        """Altyazı sekmesini kur (Faz 3)"""
        subtitle_manager = SubtitleTab(tab, fg_color="transparent")
        subtitle_manager.pack(fill="both", expand=True)

    def _setup_history_tab(self, tab):
        """Geçmiş sekmesini kur (Faz 4)"""
        history_viewer = HistoryTab(tab, self.db_manager, fg_color="transparent")
        history_viewer.pack(fill="both", expand=True)

    def _setup_settings_tab_full(self, tab):
        """Ayarlar sekmesini kur (Faz 4 & 5 - Gelişmiş)"""
        settings_manager = SettingsTab(tab, self.config_manager, fg_color="transparent")
        settings_manager.pack(fill="both", expand=True)

    def _change_appearance(self, choice):
        """Görünüm modunu değiştir"""
        ctk.set_appearance_mode(choice)

    def _change_theme(self, choice):
        """Tema rengini değiştir"""
        ctk.set_default_color_theme(choice)


def main():
    """Uygulamayı başlat"""
    try:
        logger.info("Starting RAVN UI")
        app = YouTubeDownloaderApp()
        app.mainloop()
    except Exception as e:
        logger.exception("Unhandled exception while running the GUI: %s", e)


if __name__ == "__main__":
    main()
