"""Legacy-compatible subtitle implementation module.

Canonical desktop imports should use ``ravn_app.ui.tabs.subtitle_tab``.
This module remains in place so older imports still resolve while Phase 5 keeps
wrapper/compatibility cleanup behavior-safe.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading
from typing import Any
from ..core.subtitle_manager import (
    SubtitleDownloader,
    SubtitleConverter,
    SubtitleEditor,
    SubtitleEmbedder,
    SubtitleFormat
)
from ravn_app.core.animation_manager import get_animation_manager
from ravn_app.core.i18n import t
from ravn_app.ui.components.error_panel import ErrorPanel
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Spacing, Sizes, Icons
from ravn_app.ui.ui_components import style_combo, style_entry, bind_focus_ring, Tooltip, set_button_loading_state

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

_VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".avi", ".mov"}
_SUBTITLE_EXTS = {".srt", ".ass", ".vtt", ".sub", ".ssa"}


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


class SubtitleTab(ctk.CTkFrame):
    """Altyazı yönetim sekmesi"""

    def __init__(self, parent, config_manager: Any = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color=Colors.BG_PRIMARY)

        self.config_manager = config_manager
        self.subtitle_downloader = SubtitleDownloader()
        self.subtitle_converter = SubtitleConverter()
        self.subtitle_editor = SubtitleEditor()
        self.subtitle_embedder = SubtitleEmbedder()
        self.animation_manager = get_animation_manager()

        self.current_video_file = None
        self.current_subtitle_file = None
        self.language_vars = {}

        self.setup_ui()

    def _language_label_key(self, language_code: str) -> str:
        mapping = {
            "tr": "subtitle.turkish",
            "en": "subtitle.english",
            "de": "subtitle.german",
            "fr": "subtitle.french",
            "es": "subtitle.spanish",
        }
        return mapping.get(language_code, "subtitle.english")

    def _apply_config_defaults(self) -> None:
        if self.config_manager is None:
            return

        preferred_language = str(self.config_manager.get("preferred_subtitle_language", "tr") or "tr").lower()
        fallback_language = str(self.config_manager.get("subtitle_fallback_language", "en") or "en").lower()
        selected_languages = {code for code in (preferred_language, fallback_language) if code and code != "none"}
        if not selected_languages:
            selected_languages = {"tr", "en"}

        for language_code, variable in self.language_vars.items():
            variable.set(language_code in selected_languages)

        self.auto_sub_var.set(bool(self.config_manager.get("subtitle_include_auto_generated", True)))

    def setup_ui(self):
        """UI'ı oluştur"""
        # Sol panel - Altyazı İndirme
        download_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE)
        download_frame.pack(side="left", fill="both", expand=True, padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(
            download_frame,
            text=t("subtitle.downloadTitle"),
            font=Fonts.H1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(pady=Spacing.SM)

        # Video URL
        ctk.CTkLabel(download_frame, text=t("subtitle.url"), font=Fonts.LABEL).pack(pady=Spacing.XS)
        self.url_entry = ctk.CTkEntry(download_frame, width=400)
        style_entry(self.url_entry)
        bind_focus_ring(self.url_entry)
        self.url_entry.pack(pady=Spacing.XS)

        # Dil seçimi
        ctk.CTkLabel(download_frame, text=t("subtitle.languages"), font=Fonts.LABEL).pack(pady=Spacing.XS)
        lang_frame = ctk.CTkFrame(download_frame, fg_color="transparent")
        lang_frame.pack(pady=Spacing.XS)

        for index, language_code in enumerate(SubtitleDownloader.SUPPORTED_LANGUAGE_CODES):
            variable = ctk.BooleanVar(value=language_code in {"tr", "en"})
            checkbox = ctk.CTkCheckBox(
                lang_frame,
                text=t(self._language_label_key(language_code)),
                variable=variable,
            )
            checkbox.grid(row=index // 3, column=index % 3, padx=Spacing.XS, pady=Spacing.XS, sticky="w")
            Tooltip(checkbox, t("subtitle.languageTooltip"))
            self.language_vars[language_code] = variable
            setattr(self, f"lang_{language_code}_var", variable)
            setattr(self, f"lang_{language_code}_cb", checkbox)

        # Otomatik altyazı
        self.auto_sub_var = ctk.BooleanVar(value=True)
        self.auto_sub_cb = ctk.CTkCheckBox(
            download_frame,
            text=t("subtitle.autoSubtitles"),
            variable=self.auto_sub_var
        )
        self.auto_sub_cb.pack(pady=Spacing.XS)
        Tooltip(self.auto_sub_cb, t("subtitle.autoSubtitlesTooltip"))
        self._apply_config_defaults()

        # Çıkış dizini
        ctk.CTkLabel(download_frame, text=t("subtitle.outputDir"), font=Fonts.LABEL).pack(pady=Spacing.XS)
        dir_frame = ctk.CTkFrame(download_frame, fg_color="transparent")
        dir_frame.pack(pady=Spacing.XS, fill="x", padx=Spacing.SM)

        self.output_dir_entry = ctk.CTkEntry(dir_frame, width=300)
        style_entry(self.output_dir_entry)
        bind_focus_ring(self.output_dir_entry)
        self.output_dir_entry.pack(side="left", padx=Spacing.XS)
        self.output_dir_entry.insert(0, str(Path.home() / "Downloads"))

        ctk.CTkButton(
            dir_frame,
            text=f"{Icons.BROWSE} {t('common.browse')}",
            width=80,
            command=self.select_output_dir,
            font=Fonts.LABEL,
            cursor=Cursors.POINTER,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
        ).pack(side="left")

        # İndir butonu
        self.download_subtitle_btn = ctk.CTkButton(
            download_frame,
            text=t("subtitle.downloadBtn"),
            command=self.download_subtitles,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            font=Fonts.LABEL_BOLD,
            cursor=Cursors.POINTER,
        )
        self.download_subtitle_btn.pack(pady=Spacing.LG)

        # Sağ panel - Altyazı İşleme
        process_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE)
        process_frame.pack(side="right", fill="both", expand=True, padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(
            process_frame,
            text=t("subtitle.processTitle"),
            font=Fonts.H1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(pady=Spacing.SM)

        # Dosya seçimi
        file_frame = ctk.CTkFrame(process_frame, fg_color="transparent")
        file_frame.pack(pady=Spacing.SM, fill="x", padx=Spacing.SM)

        # Video drop zone
        self._video_drop_zone = ctk.CTkFrame(
            file_frame,
            border_width=2,
            border_color=Colors.BORDER_STRONG
        )
        self._video_drop_zone.pack(fill="x", pady=Spacing.XS)

        self._video_dnd_hint = ctk.CTkLabel(
            self._video_drop_zone,
            text=t("subtitle.videoHint"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        self._video_dnd_hint.pack(pady=(4, 0))

        ctk.CTkButton(
            self._video_drop_zone,
            text=f"{Icons.BROWSE} {t('subtitle.videoSelect')}",
            command=self.select_video_file,
            width=150,
            font=Fonts.LABEL,
            cursor=Cursors.POINTER,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
        ).pack(pady=Spacing.XS)

        self.video_label = ctk.CTkLabel(self._video_drop_zone, text=t("subtitle.videoNotSelected"), font=Fonts.LABEL)
        self.video_label.pack(pady=(0, Spacing.XS))

        # Subtitle drop zone
        self._subtitle_drop_zone = ctk.CTkFrame(
            file_frame,
            border_width=2,
            border_color=Colors.BORDER_STRONG
        )
        self._subtitle_drop_zone.pack(fill="x", pady=Spacing.XS)

        self._subtitle_dnd_hint = ctk.CTkLabel(
            self._subtitle_drop_zone,
            text=t("subtitle.subtitleHint"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        self._subtitle_dnd_hint.pack(pady=(4, 0))

        ctk.CTkButton(
            self._subtitle_drop_zone,
            text=f"{Icons.BROWSE} {t('subtitle.subtitleSelect')}",
            command=self.select_subtitle_file,
            width=150,
            font=Fonts.LABEL,
            cursor=Cursors.POINTER,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
        ).pack(pady=Spacing.XS)

        self.subtitle_label = ctk.CTkLabel(self._subtitle_drop_zone, text=t("subtitle.subtitleNotSelected"), font=Fonts.LABEL)
        self.subtitle_label.pack(pady=(0, Spacing.XS))

        # Dönüştürme
        convert_frame = ctk.CTkFrame(process_frame, fg_color=Colors.BG_CARD)
        convert_frame.pack(pady=Spacing.SM, fill="x", padx=Spacing.SM)

        ctk.CTkLabel(convert_frame, text=t("subtitle.formatConvert"), font=Fonts.LABEL_BOLD).pack(pady=Spacing.XS)
        self.format_combo = ctk.CTkComboBox(
            convert_frame,
            values=["SRT", "VTT", "ASS", "SSA"]
        )
        style_combo(self.format_combo)
        bind_focus_ring(self.format_combo)
        self.format_combo.pack(pady=Spacing.XS)
        Tooltip(self.format_combo, t("subtitle.formatConvertTooltip"))

        ctk.CTkButton(
            convert_frame,
            text=f"{Icons.CONVERT_BTN} {t('subtitle.convert')}",
            command=self.convert_subtitle,
            font=Fonts.LABEL,
            cursor=Cursors.POINTER,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
        ).pack(pady=Spacing.XS)

        # Zamanlama düzenleme
        timing_frame = ctk.CTkFrame(process_frame, fg_color=Colors.BG_CARD)
        timing_frame.pack(pady=Spacing.SM, fill="x", padx=Spacing.SM)

        ctk.CTkLabel(timing_frame, text=t("subtitle.timingShift"), font=Fonts.LABEL_BOLD).pack(pady=Spacing.XS)
        self.shift_slider = ctk.CTkSlider(
            timing_frame,
            from_=-10,
            to=10,
            number_of_steps=40
        )
        self.shift_slider.pack(pady=Spacing.XS, fill="x", padx=20)
        self.shift_slider.set(0)
        Tooltip(self.shift_slider, t("subtitle.timingShiftTooltip"))

        self.shift_label = ctk.CTkLabel(timing_frame, text="0.0s", font=Fonts.LABEL)
        self.shift_label.pack(pady=Spacing.XS)
        self.shift_slider.configure(command=lambda v: self.shift_label.configure(text=f"{v:.1f}s"))

        ctk.CTkButton(
            timing_frame,
            text=t("subtitle.adjustTiming"),
            command=self.shift_timing,
            font=Fonts.LABEL,
            cursor=Cursors.POINTER,
        ).pack(pady=Spacing.XS)

        # Videoya gömme
        embed_frame = ctk.CTkFrame(process_frame, fg_color=Colors.BG_CARD)
        embed_frame.pack(pady=Spacing.SM, fill="x", padx=Spacing.SM)

        ctk.CTkLabel(embed_frame, text=t("subtitle.embedToVideo"), font=Fonts.LABEL_BOLD).pack(pady=Spacing.XS)

        embed_type_frame = ctk.CTkFrame(embed_frame, fg_color="transparent")
        embed_type_frame.pack(pady=Spacing.XS)

        self.soft_subtitle_btn = ctk.CTkButton(
            embed_type_frame,
            text=t("subtitle.softSubtitle"),
            command=lambda: self.embed_subtitle("soft"),
            width=150,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            cursor=Cursors.POINTER,
        )
        self.soft_subtitle_btn.pack(side="left", padx=Spacing.XS)
        Tooltip(self.soft_subtitle_btn, t("subtitle.softSubtitleTooltip"))

        self.hard_subtitle_btn = ctk.CTkButton(
            embed_type_frame,
            text=t("subtitle.hardSubtitle"),
            command=lambda: self.embed_subtitle("hard"),
            width=150,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            cursor=Cursors.POINTER,
        )
        self.hard_subtitle_btn.pack(side="left", padx=Spacing.XS)
        Tooltip(self.hard_subtitle_btn, t("subtitle.hardSubtitleTooltip"))

        # Log
        log_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE)
        log_frame.pack(side="bottom", fill="x", padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(log_frame, text=t("subtitle.logTitle"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.log_text = ctk.CTkTextbox(
            log_frame,
            height=100,
            font=Fonts.MONO,
            fg_color=Colors.BG_INPUT,
            text_color=Colors.TEXT_PRIMARY,
            border_color=Colors.BORDER,
        )
        self.log_text.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        # ===== Error Panel (hidden by default) =====
        self.error_panel = ErrorPanel(
            log_frame,
            animation_manager=self.animation_manager,
        )

        # Register drop zones for drag & drop
        _setup_dnd(
            self._video_drop_zone,
            callback=self._on_video_drop,
            enter_callback=lambda e: self._highlight_zone(self._video_drop_zone, self._video_dnd_hint, True),
            leave_callback=lambda e: self._highlight_zone(self._video_drop_zone, self._video_dnd_hint, False),
        )
        _setup_dnd(
            self._subtitle_drop_zone,
            callback=self._on_subtitle_drop,
            enter_callback=lambda e: self._highlight_zone(self._subtitle_drop_zone, self._subtitle_dnd_hint, True),
            leave_callback=lambda e: self._highlight_zone(self._subtitle_drop_zone, self._subtitle_dnd_hint, False),
        )

    def _on_ctrl_enter(self, event=None):
        """Handle Ctrl+Enter - download subtitles."""
        if not self.winfo_viewable():
            return
        # Only trigger if button is not disabled (not already downloading)
        if self.download_subtitle_btn.cget("state") != "disabled":
            self.download_subtitles()

    def _on_escape(self, event=None):
        """Handle Escape - no cancellation available for subtitle downloads."""
        if not self.winfo_viewable():
            return
        # Subtitle downloads run in a simple thread without cancellation support

    def _on_ctrl_l(self, event=None):
        """Handle Ctrl+L - clear URL entry."""
        if not self.winfo_viewable():
            return
        self.url_entry.delete(0, "end")
        return "break"

    def _parse_drop_path(self, event) -> Path:
        """Extract a Path from a tkinterdnd2 drop event."""
        raw = event.data.strip()
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        return Path(raw)

    def _highlight_zone(self, zone_frame, hint_label, active: bool):
        """Toggle highlight on a drop zone frame."""
        try:
            if active:
                zone_frame.configure(border_color=Colors.BORDER_ACCENT)
                hint_label.configure(text_color=Colors.BORDER_ACCENT)
            else:
                zone_frame.configure(border_color=Colors.BORDER_STRONG)
                hint_label.configure(text_color=Colors.TEXT_MUTED)
        except Exception:
            pass

    def _on_video_drop(self, event):
        """Handle a file dropped onto the video drop zone."""
        try:
            file_path = self._parse_drop_path(event)
            self._highlight_zone(self._video_drop_zone, self._video_dnd_hint, False)
            if file_path.suffix.lower() not in _VIDEO_EXTS:
                messagebox.showwarning(
                    t("subtitle.warningTitle"),
                    t("subtitle.videoDropInvalid", name=file_path.name, formats=", ".join(sorted(_VIDEO_EXTS)))
                )
                return
            self.current_video_file = str(file_path)
            self.video_label.configure(text=file_path.name)
            self.log(t("subtitle.videoDropped", name=file_path.name))
        except Exception:
            pass

    def _on_subtitle_drop(self, event):
        """Handle a file dropped onto the subtitle drop zone."""
        try:
            file_path = self._parse_drop_path(event)
            self._highlight_zone(self._subtitle_drop_zone, self._subtitle_dnd_hint, False)
            if file_path.suffix.lower() not in _SUBTITLE_EXTS:
                messagebox.showwarning(
                    t("subtitle.warningTitle"),
                    t("subtitle.subtitleDropInvalid", name=file_path.name, formats=", ".join(sorted(_SUBTITLE_EXTS)))
                )
                return
            self.current_subtitle_file = str(file_path)
            self.subtitle_label.configure(text=file_path.name)
            self.log(t("subtitle.subtitleDropped", name=file_path.name))
        except Exception:
            pass

    def log(self, message: str):
        """Log mesajı ekle"""
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")

    def select_output_dir(self):
        """Çıkış dizini seç"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.output_dir_entry.delete(0, "end")
            self.output_dir_entry.insert(0, dir_path)

    def select_video_file(self):
        """Video dosyası seç"""
        file_path = filedialog.askopenfilename(
            title=t("subtitle.videoSelect"),
            filetypes=[
                ("Video Dosyaları", "*.mp4 *.mkv *.avi *.mov"),
                ("Tüm Dosyalar", "*.*")
            ]
        )
        if file_path:
            self.current_video_file = file_path
            self.video_label.configure(text=Path(file_path).name)
            self.log(t("subtitle.videoSelected", name=Path(file_path).name))

    def select_subtitle_file(self):
        """Altyazı dosyası seç"""
        file_path = filedialog.askopenfilename(
            title=t("subtitle.subtitleSelect"),
            filetypes=[
                ("Altyazı Dosyaları", "*.srt *.vtt *.ass *.ssa"),
                ("Tüm Dosyalar", "*.*")
            ]
        )
        if file_path:
            self.current_subtitle_file = file_path
            self.subtitle_label.configure(text=Path(file_path).name)
            self.log(t("subtitle.subtitleSelected", name=Path(file_path).name))

    def download_subtitles(self):
        """Altyazıları indir"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning(t("subtitle.warningTitle"), t("subtitle.urlRequired"))
            return

        output_dir = self.output_dir_entry.get()

        languages = [
            language_code
            for language_code, variable in self.language_vars.items()
            if variable.get()
        ]

        if not languages:
            messagebox.showwarning(t("subtitle.warningTitle"), t("subtitle.selectLanguage"))
            return

        self.log(t("subtitle.subtitlesDownloading", url=url))
        self.error_panel.hide_error()
        set_button_loading_state(self.download_subtitle_btn, True, loading_text=t("subtitle.downloadingBtn"))

        def download_thread():
            try:
                subtitles = self.subtitle_downloader.download_subtitles(
                    url,
                    output_dir,
                    languages,
                    self.auto_sub_var.get()
                )

                if subtitles:
                    self.log(t("subtitle.subtitlesDownloaded", count=len(subtitles)))
                    for sub in subtitles:
                        self.log(t("subtitle.subtitleLine", language=sub.language, name=Path(sub.file_path).name))
                else:
                    self.log(t("subtitle.subtitleNotFound"))

            except Exception as e:
                error_msg = str(e)
                self.log(t("subtitle.errorLine", error=error_msg))
                self.after(0, lambda: self.error_panel.show_error(
                    message=t("subtitle.downloadError"),
                    raw_text=error_msg,
                ))

            finally:
                self.after(0, lambda: set_button_loading_state(self.download_subtitle_btn, False, original_text=t("subtitle.downloadBtn")))

        threading.Thread(target=download_thread, daemon=True).start()

    def convert_subtitle(self):
        """Altyazı formatını dönüştür"""
        if not self.current_subtitle_file:
            messagebox.showwarning(t("subtitle.warningTitle"), t("subtitle.selectSubtitleFirst"))
            return

        target_format = self.format_combo.get().lower()
        output_file = str(Path(self.current_subtitle_file).with_suffix(f".{target_format}"))

        self.log(t("subtitle.converting", format=target_format.upper()))
        self.error_panel.hide_error()

        success = self.subtitle_converter.convert(
            self.current_subtitle_file,
            SubtitleFormat[target_format.upper()],
            output_file
        )

        if success:
            self.log(t("subtitle.converted", name=Path(output_file).name))
            self.current_subtitle_file = output_file
            self.subtitle_label.configure(text=Path(output_file).name)
        else:
            self.log(t("subtitle.convertFailed"))
            self.error_panel.show_error(
                message=t("subtitle.convertError"),
                raw_text=t("subtitle.convertFailed"),
            )

    def shift_timing(self):
        """Altyazı zamanlamasını kaydır"""
        if not self.current_subtitle_file:
            messagebox.showwarning(t("subtitle.warningTitle"), t("subtitle.selectSubtitleFirst"))
            return

        shift_seconds = self.shift_slider.get()
        shift_ms = int(shift_seconds * 1000)

        output_file = str(Path(self.current_subtitle_file).with_stem(
            Path(self.current_subtitle_file).stem + "_shifted"
        ))

        self.log(t("subtitle.timingShiftRunning", seconds=f"{shift_seconds:.1f}"))
        self.error_panel.hide_error()

        success = self.subtitle_editor.shift_timing(
            self.current_subtitle_file,
            output_file,
            shift_ms
        )

        if success:
            self.log(t("subtitle.timingShiftDone", name=Path(output_file).name))
            self.current_subtitle_file = output_file
            self.subtitle_label.configure(text=Path(output_file).name)
        else:
            self.log(t("subtitle.timingShiftFailed"))
            self.error_panel.show_error(
                message=t("subtitle.timingError"),
                raw_text=t("subtitle.timingShiftFailed"),
            )

    def embed_subtitle(self, embed_type: str):
        """Altyazıyı videoya göm"""
        if not self.current_video_file or not self.current_subtitle_file:
            messagebox.showwarning(t("subtitle.warningTitle"), t("subtitle.selectVideoAndSubtitle"))
            return

        output_file = str(Path(self.current_video_file).with_stem(
            Path(self.current_video_file).stem + f"_{embed_type}_sub"
        ))

        self.log(t("subtitle.embedding", mode=embed_type))
        self.error_panel.hide_error()

        def embed_thread():
            try:
                if embed_type == "soft":
                    preferred_language = "tr"
                    if self.config_manager is not None:
                        preferred_language = str(self.config_manager.get("preferred_subtitle_language", "tr") or "tr")
                    success = self.subtitle_embedder.embed_soft(
                        self.current_video_file,
                        self.current_subtitle_file,
                        output_file,
                        language=preferred_language,
                    )
                else:
                    success = self.subtitle_embedder.embed_hard(
                        self.current_video_file,
                        self.current_subtitle_file,
                        output_file
                    )

                if success:
                    self.log(t("subtitle.embedDone", name=Path(output_file).name))
                else:
                    self.log(t("subtitle.embedFailed"))
                    self.after(0, lambda: self.error_panel.show_error(
                        message=t("subtitle.embedError"),
                        raw_text=t("subtitle.embedFailed"),
                    ))

            except Exception as e:
                error_msg = str(e)
                self.log(t("subtitle.errorLine", error=error_msg))
                self.after(0, lambda: self.error_panel.show_error(
                    message=t("subtitle.embedError"),
                    raw_text=error_msg,
                ))

        threading.Thread(target=embed_thread, daemon=True).start()
