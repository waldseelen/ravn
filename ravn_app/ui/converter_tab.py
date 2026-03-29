"""
Video Converter UI Sekmesi - CustomTkinter ile oluşturulmuş
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Optional, Callable
import os
from pathlib import Path
from threading import Thread

from ravn_app.core.converter import (
    VideoConverter, BatchConverter, ConversionSettings,
    VideoCodec, AudioCodec, VideoQuality, AudioBitrate, CodecManager
)
from ravn_app.core.animation_manager import get_animation_manager
from ravn_app.ui.design_tokens import Colors, Fonts, Spacing, Sizes, Icons

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False


def _setup_dnd(widget, callback, enter_callback=None, leave_callback=None):
    """Register a widget as a drop target if tkinterdnd2 is available."""
    if not HAS_DND:
        return
    try:
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind('<<Drop>>', callback)
        if enter_callback:
            widget.dnd_bind('<<DragEnter>>', enter_callback)
        if leave_callback:
            widget.dnd_bind('<<DragLeave>>', leave_callback)
    except Exception:
        pass


class ConverterTab(ctk.CTkFrame):
    """Video converter sekmesi"""

    def __init__(self, parent, db_manager=None, notify_callback: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.converter = VideoConverter()
        self.batch_converter = None
        self.conversion_thread = None
        self.is_converting = False
        self.db_manager = db_manager  # Veritabanı yöneticisi
        self.notify_callback = notify_callback
        self.animation_manager = get_animation_manager()  # Animation utilities
        self._spinner_animation_id = None  # Track active spinner

        self.setup_ui()

    def setup_ui(self):
        """UI bileşenlerini kur"""
        # Başlık
        title = ctk.CTkLabel(
            self,
            text="Video Dönüştürücü",
            font=Fonts.H1
        )
        title.pack(pady=Spacing.SM, padx=Spacing.SM)

        # Ana frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=Spacing.SM, pady=Spacing.SM)

        # ===== Giriş Dosyası =====
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="x", pady=Spacing.MD)

        ctk.CTkLabel(input_frame, text="Giriş Dosyası:", font=Fonts.H2).pack(anchor="w")

        # Drop zone frame with dashed-border effect
        self._dnd_drop_zone = ctk.CTkFrame(
            input_frame,
            border_width=2,
            border_color=Colors.BORDER_STRONG
        )
        self._dnd_drop_zone.pack(fill="x", pady=Spacing.SM)

        self._dnd_hint_label = ctk.CTkLabel(
            self._dnd_drop_zone,
            text="Dosya sürükle & bırak veya seç",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        self._dnd_hint_label.pack(pady=(4, 0))

        input_subframe = ctk.CTkFrame(self._dnd_drop_zone)
        input_subframe.pack(fill="x", pady=Spacing.SM)

        self.input_path = ctk.CTkEntry(input_subframe, placeholder_text="Video dosyasını seç...")
        self.input_path.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(
            input_subframe,
            text="Seç",
            width=100,
            command=self.select_input_file
        ).pack(side="left")

        # ===== Format ve Codec Seçimi =====
        options_frame = ctk.CTkFrame(main_frame)
        options_frame.pack(fill="x", pady=Spacing.MD)

        # Video Codec
        video_frame = ctk.CTkFrame(options_frame)
        video_frame.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkLabel(video_frame, text="Video Codec:", font=Fonts.LABEL_BOLD).pack(anchor="w")
        self.video_codec = ctk.CTkComboBox(
            video_frame,
            values=list(CodecManager.VIDEO_CODECS.keys()),
            state="readonly"
        )
        self.video_codec.set("h264")
        self.video_codec.pack(fill="x", pady=Spacing.SM)

        # Ses Codec
        audio_frame = ctk.CTkFrame(options_frame)
        audio_frame.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkLabel(audio_frame, text="Ses Codec:", font=Fonts.LABEL_BOLD).pack(anchor="w")
        self.audio_codec = ctk.CTkComboBox(
            audio_frame,
            values=list(CodecManager.AUDIO_CODECS.keys()),
            state="readonly"
        )
        self.audio_codec.set("aac")
        self.audio_codec.pack(fill="x", pady=Spacing.SM)

        # Kalite
        quality_frame = ctk.CTkFrame(options_frame)
        quality_frame.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkLabel(quality_frame, text="Kalite:", font=Fonts.LABEL_BOLD).pack(anchor="w")
        self.quality = ctk.CTkComboBox(
            quality_frame,
            values=["Kayıpsız", "Çok Yüksek", "Yüksek", "Orta", "Düşük", "Çok Düşük"],
            state="readonly"
        )
        self.quality.set("Yüksek")
        self.quality.pack(fill="x", pady=Spacing.SM)

        # ===== İleri Ayarlar =====
        advanced_frame = ctk.CTkFrame(main_frame)
        advanced_frame.pack(fill="x", pady=Spacing.MD)

        ctk.CTkLabel(advanced_frame, text="İleri Ayarlar:", font=Fonts.LABEL_BOLD).pack(anchor="w", pady=Spacing.SM)

        # Hız Preset
        preset_frame = ctk.CTkFrame(advanced_frame)
        preset_frame.pack(fill="x", pady=Spacing.SM)

        ctk.CTkLabel(preset_frame, text="Hız:").pack(side="left", padx=5)
        self.preset = ctk.CTkComboBox(
            preset_frame,
            values=["Hızlı", "Orta", "Yavaş"],
            state="readonly",
            width=150
        )
        self.preset.set("Orta")
        self.preset.pack(side="left", padx=5)

        # Hardware Acceleration
        ctk.CTkLabel(preset_frame, text="Hızlandırma:").pack(side="left", padx=5)
        self.hwaccel = ctk.CTkComboBox(
            preset_frame,
            values=["Yok", "NVENC", "Quick Sync"],
            state="readonly",
            width=150
        )
        self.hwaccel.set("Yok")
        self.hwaccel.pack(side="left", padx=5)

        # Ses Bitrate
        bitrate_frame = ctk.CTkFrame(advanced_frame)
        bitrate_frame.pack(fill="x", pady=Spacing.SM)

        ctk.CTkLabel(bitrate_frame, text="Ses Bitrate:").pack(side="left", padx=5)
        self.audio_bitrate = ctk.CTkComboBox(
            bitrate_frame,
            values=["320k (Çok Yüksek)", "192k (Yüksek)", "128k (Orta)", "96k (Düşük)"],
            state="readonly",
            width=200
        )
        self.audio_bitrate.set("128k (Orta)")
        self.audio_bitrate.pack(side="left", padx=5)

        # ===== Çıkış Dosyası =====
        output_frame = ctk.CTkFrame(main_frame)
        output_frame.pack(fill="x", pady=Spacing.MD)

        ctk.CTkLabel(output_frame, text="Çıkış Dosyası:", font=Fonts.H2).pack(anchor="w")

        output_subframe = ctk.CTkFrame(output_frame)
        output_subframe.pack(fill="x", pady=Spacing.SM)

        self.output_path = ctk.CTkEntry(output_subframe, placeholder_text="Otomatik olarak adlandırılacak...")
        self.output_path.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(
            output_subframe,
            text="Seç",
            width=100,
            command=self.select_output_file
        ).pack(side="left")

        # ===== Progress Bar =====
        progress_frame = ctk.CTkFrame(main_frame)
        progress_frame.pack(fill="x", pady=Spacing.MD)

        self.progress_var = ctk.DoubleVar(value=0)
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            variable=self.progress_var
        )
        self.progress_bar.pack(fill="x", pady=Spacing.SM)

        # Status
        self.status_label = ctk.CTkLabel(
            progress_frame,
            text="Hazır",
            font=Fonts.LABEL,
            text_color=Colors.STATUS_IDLE
        )
        self.status_label.pack(anchor="w", pady=Spacing.SM)

        # ===== Log Alanı =====
        log_frame = ctk.CTkFrame(main_frame)
        log_frame.pack(fill="both", expand=True, pady=Spacing.MD)

        ctk.CTkLabel(log_frame, text="İşlem Günlüğü:", font=Fonts.LABEL_BOLD).pack(anchor="w")

        scrollbar = ctk.CTkScrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_text = ctk.CTkTextbox(
            log_frame,
            yscrollcommand=scrollbar.set,
            height=150,
            font=Fonts.MONO
        )
        self.log_text.pack(fill="both", expand=True, pady=Spacing.SM)
        scrollbar.configure(command=self.log_text.yview)

        # ===== Butonlar =====
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=Spacing.MD)

        self.convert_btn = ctk.CTkButton(
            button_frame,
            text="▶ Dönüştür",
            command=self.start_conversion,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            height=Sizes.BTN_HEIGHT_MD,
            font=Fonts.LABEL_BOLD
        )
        self.convert_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            button_frame,
            text="⏹ Durdur",
            command=self.stop_conversion,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
            height=Sizes.BTN_HEIGHT_MD,
            font=Fonts.LABEL_BOLD,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

        self.clear_btn = ctk.CTkButton(
            button_frame,
            text="🗑 Temizle",
            command=self.clear_fields,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            height=Sizes.BTN_HEIGHT_MD,
            font=Fonts.LABEL_BOLD
        )
        self.clear_btn.pack(side="left", padx=5)

        # Register drop zone for drag & drop
        _setup_dnd(
            self._dnd_drop_zone,
            callback=self._on_file_drop,
            enter_callback=self._on_drag_enter,
            leave_callback=self._on_drag_leave,
        )
        _setup_dnd(
            self.input_path,
            callback=self._on_file_drop,
            enter_callback=self._on_drag_enter,
            leave_callback=self._on_drag_leave,
        )

    def _on_file_drop(self, event):
        """Handle a file dropped onto the input area."""
        try:
            raw = event.data.strip()
            # tkinterdnd2 may wrap paths in braces on Windows
            if raw.startswith("{") and raw.endswith("}"):
                raw = raw[1:-1]
            file_path = Path(raw)
            self.input_path.delete(0, "end")
            self.input_path.insert(0, str(file_path))
            self.log_add(f"Dosya bırakıldı: {file_path.name}")
            self._on_drag_leave(event)
        except Exception:
            pass

    def _on_drag_enter(self, event):
        """Highlight drop zone when a drag enters."""
        try:
            self._dnd_drop_zone.configure(
                border_color=Colors.ACCENT,
                fg_color=Colors.DRAG_OVER
            )
            self._dnd_hint_label.configure(
                text_color=Colors.ACCENT_LIGHT,
                text=f"{Icons.ARROW_DOWN} Dosyayı buraya bırak"
            )
        except Exception:
            pass

    def _on_drag_leave(self, event):
        """Restore drop zone appearance when drag leaves."""
        try:
            self._dnd_drop_zone.configure(
                border_color=Colors.BORDER_STRONG,
                fg_color="transparent"
            )
            self._dnd_hint_label.configure(
                text_color=Colors.TEXT_MUTED,
                text=f"{Icons.FILE} Video dosyasını buraya sürükle"
            )
        except Exception:
            pass

    def select_input_file(self):
        """Giriş dosyasını seç"""
        file = filedialog.askopenfilename(
            title="Video dosyasını seç",
            filetypes=[
                ("Tüm Video Dosyaları", "*.mp4 *.mkv *.avi *.mov *.webm *.flv"),
                ("MP4", "*.mp4"),
                ("MKV", "*.mkv"),
                ("AVI", "*.avi"),
                ("MOV", "*.mov"),
                ("WEBM", "*.webm"),
                ("FLV", "*.flv"),
                ("Tüm Dosyalar", "*.*")
            ]
        )

        if file:
            self.input_path.delete(0, "end")
            self.input_path.insert(0, file)
            self.log_add(f"Dosya seçildi: {Path(file).name}")

    def select_output_file(self):
        """Çıkış dosyasını seç"""
        file = filedialog.asksaveasfilename(
            title="Çıkış dosyasını seç",
            defaultextension=".mp4",
            filetypes=[
                ("MP4", "*.mp4"),
                ("MKV", "*.mkv"),
                ("WEBM", "*.webm"),
                ("AVI", "*.avi"),
                ("MOV", "*.mov"),
                ("FLV", "*.flv"),
                ("Tüm Dosyalar", "*.*")
            ]
        )

        if file:
            self.output_path.delete(0, "end")
            self.output_path.insert(0, file)
            self.log_add(f"Çıkış dosyası: {Path(file).name}")

    def get_quality(self) -> VideoQuality:
        """Seçilen kaliteyi al"""
        quality_map = {
            "Kayıpsız": VideoQuality.LOSSLESS,
            "Çok Yüksek": VideoQuality.VERYHIGH,
            "Yüksek": VideoQuality.HIGH,
            "Orta": VideoQuality.MEDIUM,
            "Düşük": VideoQuality.LOW,
            "Çok Düşük": VideoQuality.VERYLOW,
        }
        return quality_map.get(self.quality.get(), VideoQuality.HIGH)

    def get_audio_bitrate(self) -> AudioBitrate:
        """Seçilen ses bitrate'i al"""
        bitrate_map = {
            "320k (Çok Yüksek)": AudioBitrate.VERY_HIGH,
            "192k (Yüksek)": AudioBitrate.HIGH,
            "128k (Orta)": AudioBitrate.MEDIUM,
            "96k (Düşük)": AudioBitrate.LOW,
        }
        return bitrate_map.get(self.audio_bitrate.get(), AudioBitrate.MEDIUM)

    def start_conversion(self):
        """Dönüştürmeyi başlat"""
        input_file = self.input_path.get()
        output_file = self.output_path.get()

        if not input_file:
            messagebox.showerror("Hata", "Lütfen giriş dosyasını seçin")
            return

        if not os.path.exists(input_file):
            messagebox.showerror("Hata", "Giriş dosyası bulunamadı")
            return

        # Otomatik çıkış dosyası adlandırması
        if not output_file:
            input_path = Path(input_file)
            video_codec = CodecManager.get_video_codec(self.video_codec.get())
            output_ext = video_codec.container if video_codec else "mp4"
            output_file = str(input_path.with_suffix(f".{output_ext}"))
            self.output_path.delete(0, "end")
            self.output_path.insert(0, output_file)

        # Ayarları oluştur
        try:
            video_codec = CodecManager.get_video_codec(self.video_codec.get())
            audio_codec = CodecManager.get_audio_codec(self.audio_codec.get())

            if not video_codec or not audio_codec:
                messagebox.showerror("Hata", "Geçersiz codec seçimi")
                return

            preset_map = {"Hızlı": "fast", "Orta": "medium", "Yavaş": "slow"}

            settings = ConversionSettings(
                input_file=input_file,
                output_file=output_file,
                video_codec=video_codec,
                audio_codec=audio_codec,
                video_quality=self.get_quality(),
                audio_bitrate=self.get_audio_bitrate(),
                preset=preset_map.get(self.preset.get(), "medium")
            )
        except Exception as e:
            messagebox.showerror("Hata", f"Ayar hatası: {str(e)}")
            return

        # Dönüştürmeyi ayrı thread'de çalıştır
        self.is_converting = True
        self.convert_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        # Animate button disable and start spinner
        self.animation_manager.animate_button_disabled(
            self.convert_btn,
            duration=150,
            target_opacity=0.5
        )
        self._spinner_animation_id = self.animation_manager.start_spinner_loop(
            self.status_label,
            fps=3
        )

        self.log_add("Dönüştürme başlatılıyor...")

        self.conversion_thread = Thread(
            target=self._conversion_worker,
            args=(settings,),
            daemon=True
        )
        self.conversion_thread.start()

    def _conversion_worker(self, settings: ConversionSettings):
        """Dönüştürme işçisi (thread'de çalışır)"""
        self.converter.set_status_callback(
            lambda msg: self.after(0, self.log_add, msg)
        )

        def update_progress(progress: float, status: str):
            self.after(0, self._apply_conversion_progress, progress, status)

        self.converter.set_progress_callback(update_progress)
        start_time = __import__('time').time()
        success = self.converter.convert(settings)
        duration = __import__('time').time() - start_time

        if success:
            self.after(0, self._on_conversion_success, settings, duration)
        else:
            self.after(0, self._on_conversion_failure)

    def _apply_conversion_progress(self, progress: float, status: str):
        """Main-thread: update progress bar and status label."""
        self.progress_var.set(progress)
        if status:
            self.status_label.configure(text=status, text_color=Colors.STATUS_RUNNING)

    def _on_conversion_success(self, settings: ConversionSettings, duration: float):
        """Main-thread: handle successful conversion."""
        self.is_converting = False

        # Stop spinner and animate button enabled
        if self._spinner_animation_id:
            self.animation_manager.stop_animation(self._spinner_animation_id)
            self._spinner_animation_id = None

        self.convert_btn.configure(state="normal")
        self.animation_manager.animate_button_enabled(
            self.convert_btn,
            duration=150,
            target_color="#f1f5f9"
        )

        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="✓ Dönüştürme tamamlandı", text_color=Colors.STATUS_DONE)
        self.progress_var.set(100)
        if hasattr(self, 'db_manager') and self.db_manager:
            from ravn_app.core.database import ConversionRecord
            record = ConversionRecord(
                input_file=settings.input_file,
                output_file=settings.output_file,
                input_codec=settings.video_codec.name,
                output_codec=settings.video_codec.name,
                conversion_date=__import__('datetime').datetime.now().isoformat(),
                duration=duration,
                status="completed"
            )
            try:
                self.db_manager.add_conversion(record)
            except Exception:
                pass
        if self.notify_callback:
            self.notify_callback(settings.output_file)
        messagebox.showinfo("Başarılı", f"Video başarıyla dönüştürüldü:\n{settings.output_file}")

    def _on_conversion_failure(self):
        """Main-thread: handle failed conversion."""
        self.is_converting = False

        # Stop spinner and animate button enabled
        if self._spinner_animation_id:
            self.animation_manager.stop_animation(self._spinner_animation_id)
            self._spinner_animation_id = None

        self.convert_btn.configure(state="normal")
        self.animation_manager.animate_button_enabled(
            self.convert_btn,
            duration=150,
            target_color="#f1f5f9"
        )

        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="✕ Dönüştürme başarısız", text_color=Colors.STATUS_ERROR)
        messagebox.showerror("Hata", "Dönüştürme sırasında hata oluştu")

    def stop_conversion(self):
        """Dönüştürmeyi durdur"""
        self.converter.stop()
        self.is_converting = False

        # Stop spinner and animate button enabled
        if self._spinner_animation_id:
            self.animation_manager.stop_animation(self._spinner_animation_id)
            self._spinner_animation_id = None

        self.convert_btn.configure(state="normal")
        self.animation_manager.animate_button_enabled(
            self.convert_btn,
            duration=150,
            target_color="#f1f5f9"
        )

        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="⏸ Durduruldu", text_color=Colors.STATUS_PAUSED)
        self.log_add("Dönüştürme durduruldu")

    def clear_fields(self):
        """Alanları temizle"""
        self.input_path.delete(0, "end")
        self.output_path.delete(0, "end")
        self.log_text.delete("1.0", "end")
        self.progress_var.set(0)
        self.status_label.configure(text="Hazır", text_color=Colors.STATUS_IDLE)
        self.video_codec.set("h264")
        self.audio_codec.set("aac")
        self.quality.set("Yüksek")

    def log_add(self, message: str):
        """Günlüğe mesaj ekle"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
