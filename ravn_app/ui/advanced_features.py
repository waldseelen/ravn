"""
RAVN - Advanced UI/UX Features (Faz 5)
Gelişmiş kullanıcı arayüzü özellikleri
"""

import logging
import threading
import time
from tkinter import filedialog
from typing import Callable, List, Optional

import customtkinter as ctk

from ravn_app.core.theme_catalog import (
    THEMES,
    get_theme_definition,
    get_theme_display_name,
    get_theme_display_names,
    normalize_theme_id,
)
from ravn_app.ui.design_tokens import Icons, Spacing

logger = logging.getLogger(__name__)


class DragDropFrame(ctk.CTkFrame):
    """Drag & Drop desteği olan frame"""

    def __init__(self, parent, on_drop: Optional[Callable] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_drop = on_drop

        # Drag & Drop label
        self.drop_label = ctk.CTkLabel(
            self,
            text=f"{Icons.FOLDER} Dosyaları buraya sürükle\nveya tıklayarak seç",
            font=("Arial", 14),
            fg_color=("gray85", "gray25"),
            corner_radius=10,
            height=150
        )
        self.drop_label.pack(fill="both", expand=True, padx=Spacing.MD, pady=Spacing.MD)

        # Click to select
        self.drop_label.bind("<Button-1>", self._on_click)

        # Windows için drag & drop (tkinterdnd2 gerekli)
        try:
            from tkinterdnd2 import DND_FILES
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind('<<Drop>>', self._on_drop_event)
        except ImportError:
            pass  # Drag & Drop kütüphanesi yoksa sadece tıklama

    def _on_click(self, event):
        """Dosya seçim dialogunu aç"""
        files = filedialog.askopenfilenames(
            title="Dosyaları seç",
            filetypes=[
                ("Video Dosyaları", "*.mp4 *.mkv *.avi *.mov *.webm"),
                ("Tüm Dosyalar", "*.*")
            ]
        )
        if files and self.on_drop:
            self.on_drop(list(files))

    def _on_drop_event(self, event):
        """Drag & Drop eventi"""
        files = self.tk.splitlist(event.data)
        if self.on_drop:
            self.on_drop(files)


class SystemTrayIntegration:
    """Sistem tray entegrasyonu"""

    def __init__(
        self,
        app_name: str = "RAVN",
        on_open: Optional[Callable[[], None]] = None,
        on_pause_queue: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ):
        self.app_name = app_name
        self.icon = None
        self.available = False
        self.on_open = on_open
        self.on_pause_queue = on_pause_queue
        self.on_quit = on_quit

        try:
            from pystray import Icon, Menu, MenuItem

            self.Icon = Icon
            self.Menu = Menu
            self.MenuItem = MenuItem
            self._create_icon()
            self.available = True
        except ImportError:
            logger.info("Sistem tray desteği için pystray kütüphanesi gerekli")

    def _create_icon(self):
        """Tray ikonu oluştur"""
        # Basit bir ikon oluştur (Nordic kahverengi theme)
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (64, 64), color='#3D3230')  # kahverengi
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill='#D4C5B9')  # beige

        menu_items = [self.MenuItem('Aç', self._on_open)]
        if self.on_pause_queue:
            menu_items.append(self.MenuItem('Kuyruğu Duraklat', self._on_pause_queue))
        menu_items.append(self.MenuItem('Çıkış', self._on_quit))
        menu = self.Menu(*menu_items)

        self.icon = self.Icon(self.app_name, image, menu=menu)

    def run(self):
        """Tray icon'u çalıştır"""
        if self.icon:
            threading.Thread(target=self.icon.run, daemon=True).start()

    def stop(self):
        """Tray icon'u durdur"""
        if self.icon:
            self.icon.stop()

    def _on_open(self, icon, item):
        """Uygulama açıldığında"""
        if self.on_open:
            self.on_open()

    def _on_pause_queue(self, icon, item):
        """Kuyruğu duraklat/başlat callback'i."""
        if self.on_pause_queue:
            self.on_pause_queue()

    def _on_quit(self, icon, item):
        """Çıkış"""
        if self.on_quit:
            self.on_quit()
        icon.stop()


class NotificationManager:
    """Bildirim yöneticisi"""

    @staticmethod
    def show_notification(
        title: str,
        message: str,
        duration: int = 5000
    ):
        """Sistem bildirimi göster"""
        try:
            # Windows 10+ toast bildirimleri
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            threading.Thread(
                target=toaster.show_toast,
                args=(title, message, None, duration / 1000),
                daemon=True
            ).start()
        except ImportError:
            # Fallback: plyer not available — surface the notification in the log
            logger.info("Bildirim: %s - %s", title, message)

    @staticmethod
    def show_download_complete(file_name: str):
        """İndirme tamamlandı bildirimi"""
        NotificationManager.show_notification(
            "İndirme Tamamlandı",
            f"{file_name} başarıyla indirildi"
        )

    @staticmethod
    def show_conversion_complete(file_name: str):
        """Dönüştürme tamamlandı bildirimi"""
        NotificationManager.show_notification(
            "Dönüştürme Tamamlandı",
            f"{file_name} başarıyla dönüştürüldü"
        )

    @staticmethod
    def show_error(message: str):
        """Hata bildirimi"""
        NotificationManager.show_notification(
            "Hata",
            message
        )


class KeyboardShortcuts:
    """Klavye kısayolları yöneticisi"""

    def __init__(self, root_window):
        self.root = root_window
        self.shortcuts = {}

    def register(self, key_combo: str, callback: Callable):
        """Kısayol kaydet"""
        self.shortcuts[key_combo] = callback
        self.root.bind(key_combo, lambda event: callback())

    def setup_default_shortcuts(
        self,
        paste_callback: Optional[Callable] = None,
        settings_callback: Optional[Callable] = None,
        quit_callback: Optional[Callable] = None
    ):
        """Varsayılan kısayolları kur"""
        if paste_callback:
            self.register("<Control-v>", paste_callback)

        if settings_callback:
            self.register("<Control-p>", settings_callback)

        if quit_callback:
            self.register("<Control-q>", quit_callback)


class ThemeManager:
    """Gelişmiş tema yöneticisi"""

    THEMES = THEMES

    @staticmethod
    def apply_theme(theme_name: str):
        """Tema uygula"""
        theme = get_theme_definition(theme_name)
        ctk.set_appearance_mode(theme["appearance_mode"])
        ctk.set_default_color_theme(theme["color_theme"])
        return theme

    @staticmethod
    def get_theme_names() -> List[str]:
        """Tema isimlerini al"""
        return get_theme_display_names()

    @staticmethod
    def get_theme_display_name(theme_name: str) -> str:
        """Normalize edilmiş tema için UI etiketini döndür."""
        return get_theme_display_name(theme_name)

    @staticmethod
    def normalize_theme_name(theme_name: str) -> str:
        """UI veya legacy config değerlerini desteklenen tema adına indirger."""
        return normalize_theme_id(theme_name)


class SearchFilter:
    """Arama ve filtreleme"""

    @staticmethod
    def filter_downloads(
        downloads: List,
        search_term: str,
        format_filter: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> List:
        """İndirmeleri filtrele"""
        filtered = downloads

        # Metin araması
        if search_term:
            search_term = search_term.lower()
            filtered = [
                d for d in filtered
                if search_term in d.get('title', '').lower()
                or search_term in d.get('url', '').lower()
            ]

        # Format filtresi
        if format_filter and format_filter != 'Tümü':
            filtered = [d for d in filtered if d.get('format') == format_filter]

        # Durum filtresi
        if status_filter and status_filter != 'Tümü':
            filtered = [d for d in filtered if d.get('status') == status_filter]

        return filtered


class ProgressAnimator:
    """İlerleme çubuğu animasyonu"""

    def __init__(self, progress_bar: ctk.CTkProgressBar):
        self.progress_bar = progress_bar
        self.is_animating = False
        self.animation_thread = None

    def start_indeterminate(self):
        """Belirsiz ilerleme animasyonu başlat"""
        self.is_animating = True
        self.animation_thread = threading.Thread(
            target=self._animate,
            daemon=True
        )
        self.animation_thread.start()

    def stop_indeterminate(self):
        """Animasyonu durdur"""
        self.is_animating = False
        if self.animation_thread:
            self.animation_thread.join(timeout=1)

    def _animate(self):
        """Animasyon döngüsü"""
        value = 0
        direction = 1
        while self.is_animating:
            value += 0.02 * direction
            if value >= 1:
                direction = -1
            elif value <= 0:
                direction = 1

            self.progress_bar.set(value)
            time.sleep(0.05)
