"""
Ana uygulama penceresi - CustomTkinter arayüzü
"""

import customtkinter as ctk
from customtkinter import filedialog
from PIL import Image
import os
import sys

# Platform-agnostik tema görselleri
THEME_IMAGES = {
    'nordic': 'vgh0i1co9d18_manus_s_2025-08-01_13-14-03_5845.webp',
    'forest': 'vgh0i1co9d18_manus_s_2025-08-01_13-14-16_3607.webp',
    'aurora': 'vgh0i1co9d18_manus_s_2025-08-01_13-14-42_1489.webp',
}


class YouTubeDownloaderApp(ctk.CTk):
    """Ana uygulama penceresi"""
    
    def __init__(self):
        super().__init__()
        
        # Tema ve pencere ayarları
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        self.title("RAVN - Media Downloader")
        self.geometry("850x650")
        self.minsize(800, 500)
        
        # Tema yönetimi
        self.current_theme = 'nordic'
        self._setup_ui()
    
    def _setup_ui(self):
        """UI bileşenlerini kur"""
        # Basit bir başlık
        header = ctk.CTkLabel(
            self,
            text="RAVN - Media Downloader",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header.pack(pady=20)
        
        # Placeholder: Kalan bileşenler ravn.py'den taşınacak
        info = ctk.CTkLabel(
            self,
            text="Uygulama yapısı güncelleniyor...\nDetaylı arayüz kodu ravn.py'de bulunmaktadır.",
            justify="center"
        )
        info.pack(pady=20)


def main():
    """Uygulamayı başlat"""
    app = YouTubeDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
