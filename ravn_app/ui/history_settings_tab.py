"""
RAVN - History and Settings Tab (Faz 4)
Geçmiş ve ayarlar arayüzü
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
from pathlib import Path
from ..core.database import DatabaseManager, ConfigManager
from .advanced_features import SearchFilter
from ravn_app.ui.design_tokens import Colors, Fonts, Spacing, Sizes


class HistoryTab(ctk.CTkFrame):
    """Geçmiş görüntüleme sekmesi"""

    def __init__(self, parent, database_manager: DatabaseManager, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = database_manager

        self.setup_ui()
        self.load_history()

    def setup_ui(self):
        """UI'ı oluştur"""
        # Başlık
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(
            header_frame,
            text="İndirme Geçmişi",
            font=Fonts.H1
        ).pack(side="left", padx=Spacing.SM)

        # İstatistikler butonu
        ctk.CTkButton(
            header_frame,
            text="İstatistikler",
            command=self.show_statistics,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM
        ).pack(side="right", padx=Spacing.XS)

        # Temizle butonu
        ctk.CTkButton(
            header_frame,
            text="Temizle",
            command=self.clear_history,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM
        ).pack(side="right", padx=Spacing.XS)

        # Arama ve filtre
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.XS)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Ara...",
            width=300
        )
        self.search_entry.pack(side="left", padx=Spacing.XS)
        self.search_entry.bind("<KeyRelease>", lambda e: self.filter_history())

        ctk.CTkLabel(search_frame, text="Format:", font=Fonts.LABEL).pack(side="left", padx=Spacing.XS)
        self.format_filter = ctk.CTkComboBox(
            search_frame,
            values=["Tümü", "MP4", "MP3", "MKV", "AVI"],
            command=lambda v: self.filter_history(),
            width=100
        )
        self.format_filter.pack(side="left", padx=Spacing.XS)

        ctk.CTkLabel(search_frame, text="Durum:", font=Fonts.LABEL).pack(side="left", padx=Spacing.XS)
        self.status_filter = ctk.CTkComboBox(
            search_frame,
            values=["Tümü", "completed", "failed", "cancelled"],
            command=lambda v: self.filter_history(),
            width=120
        )
        self.status_filter.pack(side="left", padx=Spacing.XS)

        # Scrollable liste
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.pack(fill="both", expand=True, padx=Spacing.SM, pady=Spacing.SM)

    def load_history(self):
        """Geçmişi yükle"""
        # Mevcut öğeleri temizle
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        downloads = self.db.get_downloads(limit=100)

        if not downloads:
            ctk.CTkLabel(
                self.scrollable_frame,
                text="Henüz indirme geçmişi yok.",
                font=Fonts.LABEL,
                text_color=Colors.TEXT_MUTED
            ).pack(pady=Spacing.XL)
            return

        for download in downloads:
            self.create_history_item(download)

    def create_history_item(self, download):
        """Geçmiş öğesi oluştur"""
        item_frame = ctk.CTkFrame(self.scrollable_frame)
        item_frame.pack(fill="x", pady=3)

        # Sol taraf - Bilgiler
        info_frame = ctk.CTkFrame(item_frame)
        info_frame.pack(side="left", fill="x", expand=True, padx=Spacing.XS, pady=Spacing.XS)

        # Başlık
        title_label = ctk.CTkLabel(
            info_frame,
            text=download.title or "Başlık yok",
            font=Fonts.LABEL_BOLD,
            anchor="w"
        )
        title_label.pack(fill="x", padx=Spacing.XS, pady=2)

        # Detaylar
        details = f"📁 {download.format} | 🎯 {download.quality} | 📊 {self.format_size(download.file_size)}"
        details_label = ctk.CTkLabel(
            info_frame,
            text=details,
            font=Fonts.SMALL,
            anchor="w",
            text_color=Colors.TEXT_MUTED
        )
        details_label.pack(fill="x", padx=Spacing.XS, pady=2)

        # Tarih
        date_label = ctk.CTkLabel(
            info_frame,
            text=f"🕐 {download.download_date}",
            font=Fonts.SMALL,
            anchor="w",
            text_color=Colors.TEXT_MUTED
        )
        date_label.pack(fill="x", padx=Spacing.XS, pady=2)

        # Sağ taraf - Butonlar
        button_frame = ctk.CTkFrame(item_frame)
        button_frame.pack(side="right", padx=Spacing.XS)

        # Durum badge
        status_colors = {
            "completed": "green",
            "failed": "red",
            "cancelled": "orange"
        }
        status_label = ctk.CTkLabel(
            button_frame,
            text=download.status,
            fg_color=status_colors.get(download.status, "gray"),
            corner_radius=5,
            width=80
        )
        status_label.pack(pady=2)

        # Dosyayı aç butonu
        if download.file_path and Path(download.file_path).exists():
            ctk.CTkButton(
                button_frame,
                text="📂 Aç",
                width=80,
                command=lambda: self.open_file(download.file_path)
            ).pack(pady=2)

    def filter_history(self):
        """Geçmişi filtrele"""
        search_term = self.search_entry.get()
        format_filter = self.format_filter.get()
        status_filter = self.status_filter.get()

        # Tüm kayıtları al
        all_downloads = self.db.get_downloads(limit=1000)

        # Filtreleme uygula
        filtered = SearchFilter.filter_downloads(
            [d.__dict__ for d in all_downloads],
            search_term,
            None if format_filter == "Tümü" else format_filter,
            None if status_filter == "Tümü" else status_filter
        )

        # UI'ı güncelle
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        for download_dict in filtered:
            from ..core.database import DownloadRecord
            download = DownloadRecord(**download_dict)
            self.create_history_item(download)

    def show_statistics(self):
        """İstatistikleri göster"""
        stats = self.db.get_statistics()

        stats_text = f"""
📊 RAVN İstatistikleri

Toplam İndirme: {stats['total_downloads']}
Başarılı İndirme: {stats['successful_downloads']}
Toplam Boyut: {self.format_size(stats['total_size'])}
Toplam Dönüştürme: {stats['total_conversions']}

En Popüler Format: {stats['most_popular_format']['format'] if stats['most_popular_format'] else 'N/A'}
"""
        messagebox.showinfo("İstatistikler", stats_text)

    def clear_history(self):
        """Geçmişi temizle"""
        response = messagebox.askyesno(
            "Geçmişi Temizle",
            "Tüm geçmiş silinecek. Emin misiniz?"
        )
        if response:
            self.db.clear_history("downloads")
            self.load_history()
            messagebox.showinfo("Başarılı", "Geçmiş temizlendi")

    @staticmethod
    def open_file(file_path: str):
        """Dosyayı aç"""
        import os
        import platform

        if platform.system() == 'Windows':
            os.startfile(file_path)
        elif platform.system() == 'Darwin':  # macOS
            os.system(f'open "{file_path}"')
        else:  # Linux
            os.system(f'xdg-open "{file_path}"')

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Dosya boyutunu formatla"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


class SettingsTab(ctk.CTkFrame):
    """Ayarlar sekmesi"""

    def __init__(self, parent, config_manager: ConfigManager, **kwargs):
        super().__init__(parent, **kwargs)
        self.config = config_manager

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """UI'ı oluştur"""
        # Başlık
        ctk.CTkLabel(
            self,
            text="Ayarlar",
            font=Fonts.H1
        ).pack(pady=Spacing.LG)

        # Tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=Spacing.LG, pady=Spacing.SM)

        # Genel sekmesi
        general_tab = self.tabview.add("Genel")
        self.create_general_settings(general_tab)

        # İndirme sekmesi
        download_tab = self.tabview.add("İndirme")
        self.create_download_settings(download_tab)

        # Dönüştürme sekmesi
        conversion_tab = self.tabview.add("Dönüştürme")
        self.create_conversion_settings(conversion_tab)

        # Gelişmiş sekmesi
        advanced_tab = self.tabview.add("Gelişmiş")
        self.create_advanced_settings(advanced_tab)

        # Alt butonlar
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=Spacing.LG, pady=Spacing.SM)

        ctk.CTkButton(
            button_frame,
            text="Kaydet",
            command=self.save_settings,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            font=Fonts.LABEL_BOLD,
            height=Sizes.BTN_HEIGHT_MD
        ).pack(side="left", padx=Spacing.XS)

        ctk.CTkButton(
            button_frame,
            text="Sıfırla",
            command=self.reset_settings,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD
        ).pack(side="left", padx=Spacing.XS)

        ctk.CTkButton(
            button_frame,
            text="Dışa Aktar",
            command=self.export_settings,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD
        ).pack(side="left", padx=Spacing.XS)

        ctk.CTkButton(
            button_frame,
            text="İçe Aktar",
            command=self.import_settings,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD
        ).pack(side="left", padx=Spacing.XS)

    def create_general_settings(self, parent):
        """Genel ayarlar"""
        # Tema
        theme_frame = ctk.CTkFrame(parent)
        theme_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(theme_frame, text="Tema:", font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.theme_combo = ctk.CTkComboBox(
            theme_frame,
            values=["Nordic", "Forest", "Aurora", "Dark", "Light"]
        )
        self.theme_combo.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        # Dil
        lang_frame = ctk.CTkFrame(parent)
        lang_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(lang_frame, text="Dil:", font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.language_combo = ctk.CTkComboBox(
            lang_frame,
            values=["Türkçe", "English"]
        )
        self.language_combo.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        # Bildirimler
        notification_frame = ctk.CTkFrame(parent)
        notification_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        self.notifications_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            notification_frame,
            text="Bildirimleri etkinleştir",
            variable=self.notifications_var,
            font=Fonts.LABEL
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        self.auto_update_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            notification_frame,
            text="Otomatik güncelleme kontrolü",
            variable=self.auto_update_var,
            font=Fonts.LABEL
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

    def create_download_settings(self, parent):
        """İndirme ayarları"""
        # Varsayılan dizin
        dir_frame = ctk.CTkFrame(parent)
        dir_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(dir_frame, text="Varsayılan İndirme Dizini:", font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        dir_select_frame = ctk.CTkFrame(dir_frame)
        dir_select_frame.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        self.download_dir_entry = ctk.CTkEntry(dir_select_frame)
        self.download_dir_entry.pack(side="left", fill="x", expand=True, padx=Spacing.XS)

        ctk.CTkButton(
            dir_select_frame,
            text="Gözat",
            width=80,
            command=self.select_download_dir,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.LABEL
        ).pack(side="right", padx=Spacing.XS)

        # Varsayılan format ve kalite
        format_frame = ctk.CTkFrame(parent)
        format_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(format_frame, text="Varsayılan Format:", font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.default_format_combo = ctk.CTkComboBox(
            format_frame,
            values=["MP4", "MP3", "MKV"]
        )
        self.default_format_combo.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(format_frame, text="Varsayılan Kalite:", font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.default_quality_combo = ctk.CTkComboBox(
            format_frame,
            values=["En İyi", "1080p", "720p", "480p"]
        )
        self.default_quality_combo.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        # Eşzamanlı indirme
        concurrent_frame = ctk.CTkFrame(parent)
        concurrent_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(concurrent_frame, text="Eşzamanlı İndirme Sayısı:", font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.concurrent_slider = ctk.CTkSlider(
            concurrent_frame,
            from_=1,
            to=5,
            number_of_steps=4
        )
        self.concurrent_slider.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        self.concurrent_label = ctk.CTkLabel(concurrent_frame, text="1", font=Fonts.LABEL)
        self.concurrent_label.pack(padx=Spacing.XS, pady=Spacing.XS)
        self.concurrent_slider.configure(
            command=lambda v: self.concurrent_label.configure(text=str(int(v)))
        )

    def create_conversion_settings(self, parent):
        """Dönüştürme ayarları"""
        # FFmpeg yolu
        ffmpeg_frame = ctk.CTkFrame(parent)
        ffmpeg_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(ffmpeg_frame, text="FFmpeg Yolu:", font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.ffmpeg_entry = ctk.CTkEntry(ffmpeg_frame)
        self.ffmpeg_entry.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        # Otomatik temizlik
        cleanup_frame = ctk.CTkFrame(parent)
        cleanup_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        self.auto_cleanup_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            cleanup_frame,
            text="Dönüştürmeden sonra kaynak dosyayı sil",
            variable=self.auto_cleanup_var,
            font=Fonts.LABEL
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

    def create_advanced_settings(self, parent):
        """Gelişmiş ayarlar"""
        # Geçmiş limiti
        history_frame = ctk.CTkFrame(parent)
        history_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(history_frame, text="Geçmiş Kayıt Limiti:", font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.history_limit_entry = ctk.CTkEntry(history_frame)
        self.history_limit_entry.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        # Altyazı ayarları
        subtitle_frame = ctk.CTkFrame(parent)
        subtitle_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        self.auto_subtitle_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            subtitle_frame,
            text="Otomatik altyazı indir",
            variable=self.auto_subtitle_var,
            font=Fonts.LABEL
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(subtitle_frame, text="Tercih Edilen Altyazı Dili:", font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.subtitle_lang_combo = ctk.CTkComboBox(
            subtitle_frame,
            values=["tr", "en", "de", "fr", "es"]
        )
        self.subtitle_lang_combo.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

    def load_settings(self):
        """Ayarları yükle"""
        self.theme_combo.set(self.config.get('theme', 'nordic').title())
        self.language_combo.set("Türkçe" if self.config.get('language') == 'tr' else "English")
        self.notifications_var.set(self.config.get('notifications_enabled', True))
        self.auto_update_var.set(self.config.get('auto_update_check', True))

        self.download_dir_entry.insert(0, self.config.get('default_download_path', ''))
        self.default_format_combo.set(self.config.get('default_format', 'MP4'))
        self.default_quality_combo.set(self.config.get('default_quality', '1080p'))
        self.concurrent_slider.set(self.config.get('concurrent_downloads', 1))
        self.concurrent_label.configure(text=str(self.config.get('concurrent_downloads', 1)))

        self.ffmpeg_entry.insert(0, self.config.get('ffmpeg_path', 'ffmpeg'))
        self.auto_cleanup_var.set(self.config.get('auto_cleanup', False))

        self.history_limit_entry.insert(0, str(self.config.get('history_limit', 1000)))
        self.auto_subtitle_var.set(self.config.get('auto_subtitle_download', False))
        self.subtitle_lang_combo.set(self.config.get('preferred_subtitle_language', 'tr'))

    def save_settings(self):
        """Ayarları kaydet"""
        self.config.set('theme', self.theme_combo.get().lower())
        self.config.set('language', 'tr' if self.language_combo.get() == "Türkçe" else 'en')
        self.config.set('notifications_enabled', self.notifications_var.get())
        self.config.set('auto_update_check', self.auto_update_var.get())

        self.config.set('default_download_path', self.download_dir_entry.get())
        self.config.set('default_format', self.default_format_combo.get())
        self.config.set('default_quality', self.default_quality_combo.get())
        self.config.set('concurrent_downloads', int(self.concurrent_slider.get()))

        self.config.set('ffmpeg_path', self.ffmpeg_entry.get())
        self.config.set('auto_cleanup', self.auto_cleanup_var.get())

        self.config.set('history_limit', int(self.history_limit_entry.get()))
        self.config.set('auto_subtitle_download', self.auto_subtitle_var.get())
        self.config.set('preferred_subtitle_language', self.subtitle_lang_combo.get())

        messagebox.showinfo("Başarılı", "Ayarlar kaydedildi")

    def reset_settings(self):
        """Ayarları sıfırla"""
        response = messagebox.askyesno(
            "Ayarları Sıfırla",
            "Tüm ayarlar varsayılana döndürülecek. Emin misiniz?"
        )
        if response:
            self.config.reset()
            self.load_settings()
            messagebox.showinfo("Başarılı", "Ayarlar sıfırlandı")

    def select_download_dir(self):
        """İndirme dizini seç"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.download_dir_entry.delete(0, "end")
            self.download_dir_entry.insert(0, dir_path)

    def export_settings(self):
        """Ayarları dışa aktar"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")]
        )
        if file_path:
            if self.config.export_config(file_path):
                messagebox.showinfo("Başarılı", "Ayarlar dışa aktarıldı")

    def import_settings(self):
        """Ayarları içe aktar"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")]
        )
        if file_path:
            if self.config.import_config(file_path):
                self.load_settings()
                messagebox.showinfo("Başarılı", "Ayarlar içe aktarıldı")
