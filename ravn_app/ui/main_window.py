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
from ravn_app.core.platform_support import PlatformManager


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
        self.platform_manager = PlatformManager()  # Platform desteği

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
        """İndirme sekmesini kur - Platform desteğiyle"""
        # Başlık
        header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=10)

        title = ctk.CTkLabel(
            header_frame,
            text="📥 Video İndir",
            font=("Arial", 18, "bold")
        )
        title.pack(anchor="w")

        # Platform seçimi
        platform_frame = ctk.CTkFrame(tab, fg_color="transparent")
        platform_frame.pack(fill="x", padx=15, pady=10)

        platform_label = ctk.CTkLabel(
            platform_frame,
            text="Platform:",
            font=("Arial", 12)
        )
        platform_label.pack(side="left", padx=5)

        platforms = self.platform_manager.get_supported_platforms()
        platform_menu = ctk.CTkOptionMenu(
            platform_frame,
            values=platforms,
            command=lambda x: self._on_platform_selected(x)
        )
        platform_menu.pack(side="left", padx=5)

        # URL giriş alanı
        url_frame = ctk.CTkFrame(tab, fg_color="transparent")
        url_frame.pack(fill="x", padx=15, pady=10)

        url_label = ctk.CTkLabel(
            url_frame,
            text="URL:",
            font=("Arial", 12)
        )
        url_label.pack(side="left", padx=5)

        self.url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="Video URL'sini gir...",
            width=400
        )
        self.url_entry.pack(side="left", padx=5, fill="x", expand=True)

        # Bilgi etiketi
        self.info_label = ctk.CTkLabel(
            tab,
            text="Desteklenen platformlar: " + ", ".join(platforms),
            text_color="#999999",
            font=("Arial", 10)
        )
        self.info_label.pack(pady=10)

        # İndir butonu
        download_btn = ctk.CTkButton(
            tab,
            text="📥 İndir",
            command=self._download_video,
            font=("Arial", 14, "bold"),
            height=40
        )
        download_btn.pack(padx=15, pady=10, fill="x")

    def _on_platform_selected(self, platform: str):
        """Platform seçildiğinde çağrılır"""
        print(f"Platform seçildi: {platform}")

    def _download_video(self):
        """Videoyu indir"""
        url = self.url_entry.get()
        if not url:
            print("URL giriniz")
            return

        print(f"İndirme başlanıyor: {url}")
        # TODO: Indirme işlemini çalıştır

    def _setup_converter_tab(self, tab):
        """Dönüştürme sekmesini kur (Faz 2)"""
        converter = ConverterTab(tab, db_manager=self.db_manager, fg_color="transparent")
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
    app = YouTubeDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
