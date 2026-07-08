"""
Video Converter UI Sekmesi - CustomTkinter ile oluşturulmuş
"""

import os
from pathlib import Path
from threading import Thread
from tkinter import filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk

from ravn_app.core.animation_manager import get_animation_manager
from ravn_app.core.converter import (
    AudioBitrate,
    CodecManager,
    ConversionSettings,
    VideoConverter,
    VideoQuality,
)
from ravn_app.core.i18n import t
from ravn_app.ui.components.error_panel import ErrorPanel
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Icons, Sizes, Spacing
from ravn_app.ui.ui_components import Tooltip, bind_focus_ring, set_button_loading_state, style_combo, style_entry

try:
    from tkinterdnd2 import DND_FILES
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

    def __init__(
        self,
        parent,
        db_manager=None,
        notify_callback: Optional[Callable[[str], None]] = None,
        auto_add_to_library_callback: Optional[Callable[..., None]] = None,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)
        self.configure(fg_color=Colors.BG_PRIMARY)

        self.converter = VideoConverter()
        self.batch_converter = None
        self.conversion_thread = None
        self.is_converting = False
        self.db_manager = db_manager  # Veritabanı yöneticisi
        self.notify_callback = notify_callback
        self.auto_add_to_library_callback = auto_add_to_library_callback
        self.animation_manager = get_animation_manager()  # Animation utilities
        self._spinner_animation_id = None  # Track active spinner
        self._progress_value = 0.0

        self.setup_ui()

    def setup_ui(self):
        """UI bileşenlerini kur"""
        # Başlık
        title = ctk.CTkLabel(
            self,
            text=t("converter.title"),
            font=Fonts.H1,
            text_color=Colors.TEXT_PRIMARY,
        )
        title.pack(pady=Spacing.SM, padx=Spacing.SM)

        # Ana frame
        main_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE)
        main_frame.pack(fill="both", expand=True, padx=Spacing.SM, pady=Spacing.SM)

        # ===== Giriş Dosyası =====
        input_frame = ctk.CTkFrame(main_frame, fg_color=Colors.BG_SURFACE)
        input_frame.pack(fill="x", pady=Spacing.MD)

        ctk.CTkLabel(input_frame, text=t("converter.inputFile"), font=Fonts.H2).pack(anchor="w")

        # Drop zone frame with dashed-border effect
        self._dnd_drop_zone = ctk.CTkFrame(
            input_frame,
            border_width=2,
            border_color=Colors.BORDER_STRONG
        )
        self._dnd_drop_zone.pack(fill="x", pady=Spacing.SM)

        self._dnd_hint_label = ctk.CTkLabel(
            self._dnd_drop_zone,
            text=t("converter.dropHint"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        self._dnd_hint_label.pack(pady=(4, 0))

        input_subframe = ctk.CTkFrame(self._dnd_drop_zone, fg_color="transparent")
        input_subframe.pack(fill="x", pady=Spacing.SM)

        self.input_path = ctk.CTkEntry(
            input_subframe,
            placeholder_text=t("converter.inputPlaceholder"),
            corner_radius=Sizes.CORNER_SM,  # POL-22
        )
        style_entry(self.input_path)
        bind_focus_ring(self.input_path)
        self.input_path.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.input_path.configure(cursor=Cursors.TEXT)  # POL-27

        browse_btn = ctk.CTkButton(
            input_subframe,
            text=f"{Icons.BROWSE} {t('common.select')}",
            width=100,
            command=self.select_input_file,
            corner_radius=Sizes.CORNER_SM,  # POL-22
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
        )
        browse_btn.pack(side="left")
        browse_btn.configure(cursor=Cursors.POINTER)  # POL-27

        # ===== Format ve Codec Seçimi =====
        options_frame = ctk.CTkFrame(main_frame, corner_radius=Sizes.CORNER_MD, fg_color=Colors.BG_CARD)  # POL-22
        options_frame.pack(fill="x", pady=Spacing.MD)

        # Video Codec
        video_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        video_frame.pack(side="left", fill="x", expand=True, padx=Spacing.XS)

        ctk.CTkLabel(video_frame, text=t("converter.videoCodec"), font=Fonts.LABEL_BOLD).pack(anchor="w")
        self.video_codec = ctk.CTkComboBox(
            video_frame,
            values=list(CodecManager.VIDEO_CODECS.keys()),
            state="readonly",
            corner_radius=Sizes.CORNER_SM,  # POL-22
        )
        self.video_codec.set("h264")
        style_combo(self.video_codec)
        bind_focus_ring(self.video_codec)
        self.video_codec.pack(fill="x", pady=Spacing.SM)
        Tooltip(self.video_codec, t("converter.videoCodecTooltip"))

        # Ses Codec
        audio_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        audio_frame.pack(side="left", fill="x", expand=True, padx=Spacing.XS)

        ctk.CTkLabel(audio_frame, text=t("converter.audioCodec"), font=Fonts.LABEL_BOLD).pack(anchor="w")
        self.audio_codec = ctk.CTkComboBox(
            audio_frame,
            values=list(CodecManager.AUDIO_CODECS.keys()),
            state="readonly",
            corner_radius=Sizes.CORNER_SM,  # POL-22
        )
        self.audio_codec.set("aac")
        style_combo(self.audio_codec)
        bind_focus_ring(self.audio_codec)
        self.audio_codec.pack(fill="x", pady=Spacing.SM)
        Tooltip(self.audio_codec, t("converter.audioCodecTooltip"))

        # Kalite
        quality_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        quality_frame.pack(side="left", fill="x", expand=True, padx=Spacing.XS)

        ctk.CTkLabel(quality_frame, text=t("converter.quality"), font=Fonts.LABEL_BOLD).pack(anchor="w")
        self.quality = ctk.CTkComboBox(
            quality_frame,
            values=["Kayıpsız", "Çok Yüksek", "Yüksek", "Orta", "Düşük", "Çok Düşük"],
            state="readonly",
            corner_radius=Sizes.CORNER_SM,  # POL-22
        )
        self.quality.set("Yüksek")
        style_combo(self.quality)
        bind_focus_ring(self.quality)
        self.quality.pack(fill="x", pady=Spacing.SM)
        Tooltip(self.quality, t("converter.converterQualityTooltip"))

        # ===== İleri Ayarlar =====
        advanced_frame = ctk.CTkFrame(main_frame, fg_color=Colors.BG_CARD)
        advanced_frame.pack(fill="x", pady=Spacing.MD)

        ctk.CTkLabel(advanced_frame, text=t("converter.advanced"), font=Fonts.LABEL_BOLD).pack(anchor="w", pady=Spacing.SM)

        # Hız Preset
        preset_frame = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        preset_frame.pack(fill="x", pady=Spacing.SM)

        ctk.CTkLabel(preset_frame, text=t("converter.speed")).pack(side="left", padx=Spacing.XS)
        self.preset = ctk.CTkComboBox(
            preset_frame,
            values=["Hızlı", "Orta", "Yavaş"],
            state="readonly",
            width=150
        )
        self.preset.set("Orta")
        style_combo(self.preset)
        bind_focus_ring(self.preset)
        self.preset.pack(side="left", padx=Spacing.XS)

        # Hardware Acceleration
        ctk.CTkLabel(preset_frame, text=t("converter.accel")).pack(side="left", padx=Spacing.XS)
        self.hwaccel = ctk.CTkComboBox(
            preset_frame,
            values=["Yok", "NVENC", "Quick Sync"],
            state="readonly",
            width=150
        )
        self.hwaccel.set("Yok")
        style_combo(self.hwaccel)
        bind_focus_ring(self.hwaccel)
        self.hwaccel.pack(side="left", padx=Spacing.XS)

        # Ses Bitrate
        bitrate_frame = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        bitrate_frame.pack(fill="x", pady=Spacing.SM)

        ctk.CTkLabel(bitrate_frame, text=t("converter.audioBitrate")).pack(side="left", padx=Spacing.XS)
        self.audio_bitrate = ctk.CTkComboBox(
            bitrate_frame,
            values=["320k (Çok Yüksek)", "192k (Yüksek)", "128k (Orta)", "96k (Düşük)"],
            state="readonly",
            width=200
        )
        self.audio_bitrate.set("128k (Orta)")
        style_combo(self.audio_bitrate)
        bind_focus_ring(self.audio_bitrate)
        self.audio_bitrate.pack(side="left", padx=Spacing.XS)

        # ===== Çıkış Dosyası =====
        output_frame = ctk.CTkFrame(main_frame, fg_color=Colors.BG_SURFACE)
        output_frame.pack(fill="x", pady=Spacing.MD)

        ctk.CTkLabel(output_frame, text=t("converter.outputFile"), font=Fonts.H2).pack(anchor="w")

        output_subframe = ctk.CTkFrame(output_frame, fg_color="transparent")
        output_subframe.pack(fill="x", pady=Spacing.SM)

        self.output_path = ctk.CTkEntry(output_subframe, placeholder_text=t("converter.outputPlaceholder"))
        style_entry(self.output_path)
        bind_focus_ring(self.output_path)
        self.output_path.pack(side="left", fill="x", expand=True, padx=(0, 5))
        Tooltip(self.output_path, t("converter.outputPathTooltip"))

        ctk.CTkButton(
            output_subframe,
            text=f"{Icons.BROWSE} {t('common.select')}",
            width=100,
            command=self.select_output_file,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
        ).pack(side="left")

        # ===== Progress Bar =====
        progress_frame = ctk.CTkFrame(main_frame, fg_color=Colors.BG_SURFACE)
        progress_frame.pack(fill="x", pady=Spacing.MD)

        self.progress_var = ctk.DoubleVar(value=0)
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            variable=self.progress_var
        )
        self.progress_bar.configure(
            progress_color=Colors.ACCENT,
            fg_color=Colors.PROGRESS_BG,
        )
        self.progress_bar.pack(fill="x", pady=Spacing.SM)

        # Status
        self.status_label = ctk.CTkLabel(
            progress_frame,
            text=t("converter.statusReady"),
            font=Fonts.LABEL,
            text_color=Colors.STATUS_IDLE
        )
        self.status_label.pack(anchor="w", pady=Spacing.SM)

        # ===== Log Alanı =====
        log_frame = ctk.CTkFrame(main_frame, fg_color=Colors.BG_SURFACE)
        log_frame.pack(fill="both", expand=True, pady=Spacing.MD)

        ctk.CTkLabel(log_frame, text=t("converter.logTitle"), font=Fonts.LABEL_BOLD).pack(anchor="w")

        scrollbar = ctk.CTkScrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_text = ctk.CTkTextbox(
            log_frame,
            yscrollcommand=scrollbar.set,
            height=150,
            font=Fonts.MONO,
            fg_color=Colors.BG_INPUT,
            text_color=Colors.TEXT_PRIMARY,
            border_color=Colors.BORDER,
        )
        self.log_text.pack(fill="both", expand=True, pady=Spacing.SM)
        scrollbar.configure(command=self.log_text.yview)

        # ===== Error Panel (hidden by default) =====
        self.error_panel = ErrorPanel(
            main_frame,
            animation_manager=self.animation_manager,
            on_retry=self.start_conversion,
        )

        # ===== Butonlar =====
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=Spacing.MD)

        self.convert_btn = ctk.CTkButton(
            button_frame,
            text=f"{Icons.CONVERT_BTN} {t('converter.convert')}",
            command=self.start_conversion,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            height=Sizes.BTN_HEIGHT_MD,
            font=Fonts.LABEL_BOLD
        )
        self.convert_btn.pack(side="left", padx=Spacing.XS)

        self.stop_btn = ctk.CTkButton(
            button_frame,
            text=f"{Icons.CANCEL_BTN} {t('converter.stop')}",
            command=self.stop_conversion,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
            height=Sizes.BTN_HEIGHT_MD,
            font=Fonts.LABEL_BOLD,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=Spacing.XS)

        self.clear_btn = ctk.CTkButton(
            button_frame,
            text=f"{Icons.CLEAR_BTN} {t('converter.clear')}",
            command=self.clear_fields,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            height=Sizes.BTN_HEIGHT_MD,
            font=Fonts.LABEL_BOLD
        )
        self.clear_btn.pack(side="left", padx=Spacing.XS)

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

    def _on_ctrl_enter(self, event=None):
        """Handle Ctrl+Enter - start conversion."""
        if not self.winfo_viewable():
            return
        if not self.is_converting:
            self.start_conversion()

    def _on_escape(self, event=None):
        """Handle Escape - stop conversion if active."""
        if not self.winfo_viewable():
            return
        if self.is_converting:
            self.stop_conversion()

    def _on_ctrl_l(self, event=None):
        """Handle Ctrl+L - clear input path."""
        if not self.winfo_viewable():
            return
        self.input_path.delete(0, "end")
        return "break"

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
                text=f"{Icons.ARROW_DOWN} {t('converter.dropFilePrompt')}"
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
                text=f"{Icons.FILE} {t('converter.dropVideoPrompt')}"
            )
        except Exception:
            pass

    def select_input_file(self):
        """Giriş dosyasını seç"""
        file = filedialog.askopenfilename(
            title=t("converter.selectInputTitle"),
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
            title=t("converter.selectOutputTitle"),
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
            messagebox.showerror(t("converter.errorTitle"), t("converter.inputRequired"))
            return

        if not os.path.exists(input_file):
            messagebox.showerror(t("converter.errorTitle"), t("converter.inputMissing"))
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
                messagebox.showerror(t("converter.errorTitle"), t("converter.invalidCodec"))
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
            messagebox.showerror(t("converter.errorTitle"), t("converter.settingsError", error=str(e)))
            return

        # Dönüştürmeyi ayrı thread'de çalıştır
        self.is_converting = True
        self._conversion_log_buffer = []  # Collect log messages for error details
        self.error_panel.hide_error()
        set_button_loading_state(self.convert_btn, True)
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

        self.log_add(t("converter.starting"))

        self.conversion_thread = Thread(
            target=self._conversion_worker,
            args=(settings,),
            daemon=True
        )
        self.conversion_thread.start()

    def _conversion_worker(self, settings: ConversionSettings):
        """Dönüştürme işçisi (thread'de çalışır)"""
        def collect_log(msg):
            self._conversion_log_buffer.append(msg)
            self.after(0, self.log_add, msg)

        self.converter.set_status_callback(collect_log)

        def update_progress(progress: float, status: str):
            self.after(0, self._apply_conversion_progress, progress, status)

        self.converter.set_progress_callback(update_progress)
        start_time = __import__('time').time()
        success = self.converter.convert(settings)
        duration = __import__('time').time() - start_time

        if success:
            self.after(0, self._on_conversion_success, settings, duration)
        else:
            raw_log = "\n".join(self._conversion_log_buffer)
            self.after(0, self._on_conversion_failure, raw_log)

    def _apply_conversion_progress(self, progress: float, status: str):
        """Main-thread: update progress bar and status label."""
        target = max(0.0, min(1.0, progress / 100.0))
        self._progress_value = self.animation_manager.smooth_progress(
            self._progress_value,
            target,
            max_step=0.08,
        )
        self.progress_var.set(self._progress_value * 100.0)
        if status:
            self.status_label.configure(text=status, text_color=Colors.STATUS_RUNNING)

    def _on_conversion_success(self, settings: ConversionSettings, duration: float):
        """Main-thread: handle successful conversion."""
        self.is_converting = False

        # Stop spinner and animate button enabled
        if self._spinner_animation_id:
            self.animation_manager.stop_animation(self._spinner_animation_id)
            self._spinner_animation_id = None

        set_button_loading_state(self.convert_btn, False)
        self.animation_manager.animate_button_enabled(
            self.convert_btn,
            duration=150,
            target_color="#f1f5f9"
        )

        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text=t("converter.successLabel"), text_color=Colors.STATUS_DONE)
        self.progress_var.set(100)
        self._progress_value = 1.0
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

        auto_add_callback = getattr(self, "auto_add_to_library_callback", None)
        if callable(auto_add_callback) and settings.output_file:
            try:
                auto_add_callback(
                    settings.output_file,
                    source_type="conversion",
                    metadata={
                        "input_file": settings.input_file,
                        "video_codec": getattr(settings.video_codec, "name", "").lower(),
                        "audio_codec": getattr(settings.audio_codec, "name", "").lower(),
                        "audio_only": settings.audio_only,
                        "video_only": settings.video_only,
                    },
                )
            except Exception:
                pass

        messagebox.showinfo(
            t("converter.successTitle"),
            t("converter.successMessage", output=settings.output_file),
        )

    def _on_conversion_failure(self, raw_log: str = ""):
        """Main-thread: handle failed conversion."""
        self.is_converting = False

        # Stop spinner and animate button enabled
        if self._spinner_animation_id:
            self.animation_manager.stop_animation(self._spinner_animation_id)
            self._spinner_animation_id = None

        set_button_loading_state(self.convert_btn, False)
        self.animation_manager.animate_button_enabled(
            self.convert_btn,
            duration=150,
            target_color="#f1f5f9"
        )

        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text=t("converter.failedLabel"), text_color=Colors.STATUS_ERROR)
        self.error_panel.show_error(
            message=t("converter.errorMessage"),
            raw_text=raw_log or t("converter.noErrorDetails"),
        )

    def stop_conversion(self):
        """Dönüştürmeyi durdur"""
        self.converter.stop()
        self.is_converting = False

        # Stop spinner and animate button enabled
        if self._spinner_animation_id:
            self.animation_manager.stop_animation(self._spinner_animation_id)
            self._spinner_animation_id = None

        set_button_loading_state(self.convert_btn, False)
        self.animation_manager.animate_button_enabled(
            self.convert_btn,
            duration=150,
            target_color="#f1f5f9"
        )

        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text=t("converter.stoppedLabel"), text_color=Colors.STATUS_PAUSED)
        self.log_add(t("converter.stoppedLog"))

    def clear_fields(self):
        """Alanları temizle"""
        self.input_path.delete(0, "end")
        self.output_path.delete(0, "end")
        self.log_text.delete("1.0", "end")
        self.progress_var.set(0)
        self.status_label.configure(text=t("converter.statusReady"), text_color=Colors.STATUS_IDLE)
        self.video_codec.set("h264")
        self.audio_codec.set("aac")
        self.quality.set("Yüksek")
        self.error_panel.hide_error()

    def log_add(self, message: str):
        """Günlüğe mesaj ekle"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
