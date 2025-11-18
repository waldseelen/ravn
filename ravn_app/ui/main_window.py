"""
Ana uygulama penceresi - CustomTkinter arayüzü (Sekmeli)
"""

import customtkinter as ctk
from customtkinter import filedialog
from PIL import Image
import os
import sys

from ravn_app.ui.converter_tab import ConverterTab


class YouTubeDownloaderApp(ctk.CTk):
    """Ana uygulama penceresi - Sekmeli arayüz"""

    def __init__(self):
        super().__init__()

        # Tema ve pencere ayarları
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("RAVN - Media Manager")
        self.geometry("1000x700")
        self.minsize(900, 600)

        # Tema yönetimi
        self.current_theme = 'nordic'
        self._setup_ui()

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
        
        # Sekme: İndir
        download_tab = self.tabview.add("📥 İndir")
        self._setup_download_tab(download_tab)
        
        # Sekme: Dönüştür
        converter_tab = self.tabview.add("🔄 Dönüştür")
        self._setup_converter_tab(converter_tab)
        
        # Sekme: Analiz
        analyzer_tab = self.tabview.add("🔍 Analiz")
        self._setup_analyzer_tab(analyzer_tab)
        
        # Sekme: Ayarlar
        settings_tab = self.tabview.add("⚙️ Ayarlar")
        self._setup_settings_tab(settings_tab)
        
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
        """Dönüştürme sekmesini kur"""
        converter = ConverterTab(tab, fg_color="transparent")
        converter.pack(fill="both", expand=True)
    
    def _setup_analyzer_tab(self, tab):
        """Analiz sekmesini kur"""
        label = ctk.CTkLabel(
            tab,
            text="🔍 Medya Analiz Aracı",
            font=("Arial", 18, "bold")
        )
        label.pack(pady=20)
        
        info = ctk.CTkLabel(
            tab,
            text="Bu sekme Faz 2 bileşenleri ile doldurulacak\n(Medya dosya analizi, codec detayları)",
            justify="center",
            text_color="#999999"
        )
        info.pack(pady=20)
        
        # TODO: Analyzer UI'ı buraya ekle
    
    def _setup_settings_tab(self, tab):
        """Ayarlar sekmesini kur"""
        label = ctk.CTkLabel(
            tab,
            text="⚙️ Uygulama Ayarları",
            font=("Arial", 18, "bold")
        )
        label.pack(pady=20)
        
        settings_frame = ctk.CTkFrame(tab)
        settings_frame.pack(fill="x", padx=20, pady=10)
        
        # Tema seçimi
        ctk.CTkLabel(settings_frame, text="Görünüm Modu:", font=("Arial", 11)).pack(anchor="w", pady=5)
        appearance_var = ctk.StringVar(value="Dark")
        appearance_menu = ctk.CTkOptionMenu(
            settings_frame,
            values=["Dark", "Light", "System"],
            variable=appearance_var,
            command=self._change_appearance
        )
        appearance_menu.pack(fill="x", pady=5)
        
        # Tema rengi
        ctk.CTkLabel(settings_frame, text="Tema Rengi:", font=("Arial", 11)).pack(anchor="w", pady=5)
        color_var = ctk.StringVar(value="blue")
        color_menu = ctk.CTkOptionMenu(
            settings_frame,
            values=["blue", "green", "dark-blue"],
            variable=color_var,
            command=self._change_theme
        )
        color_menu.pack(fill="x", pady=5)
        
        # Hakkında
        about_frame = ctk.CTkFrame(tab)
        about_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(about_frame, text="Hakkında", font=("Arial", 12, "bold")).pack(anchor="w")
        
        about_text = ctk.CTkLabel(
            about_frame,
            text="""RAVN - Rapid Audio-Video Networking
Sürüm: 1.0.0 (Faz 1: Video Converter)

Özellikler:
• YouTube Video İndirme
• Video Format Dönüştürme (MP4, MKV, WebM, vb.)
• Codec Seçimi (H.264, H.265, VP9, AV1)
• Toplu İşlem Desteği
• Medya Dosya Analizi (Faz 2)

Geliştirici: waldseelen
GitHub: https://github.com/waldseelen/ravn""",
            font=("Arial", 9),
            text_color="#CCCCCC",
            justify="left"
        )
        about_text.pack(anchor="w", pady=10)
    
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
