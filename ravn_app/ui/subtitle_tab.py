"""
RAVN - Subtitle Manager Tab (Faz 3)
Altyazı yönetim arayüzü
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading
from ..core.subtitle_manager import (
    SubtitleDownloader,
    SubtitleConverter,
    SubtitleEditor,
    SubtitleEmbedder,
    SubtitleFormat
)
from ravn_app.ui.design_tokens import Colors, Fonts, Spacing, Sizes, Icons

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

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.subtitle_downloader = SubtitleDownloader()
        self.subtitle_converter = SubtitleConverter()
        self.subtitle_editor = SubtitleEditor()
        self.subtitle_embedder = SubtitleEmbedder()

        self.current_video_file = None
        self.current_subtitle_file = None

        self.setup_ui()

    def setup_ui(self):
        """UI'ı oluştur"""
        # Sol panel - Altyazı İndirme
        download_frame = ctk.CTkFrame(self)
        download_frame.pack(side="left", fill="both", expand=True, padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(
            download_frame,
            text="Altyazı İndir",
            font=Fonts.H1
        ).pack(pady=Spacing.SM)

        # Video URL
        ctk.CTkLabel(download_frame, text="Video URL:", font=Fonts.LABEL).pack(pady=Spacing.XS)
        self.url_entry = ctk.CTkEntry(download_frame, width=400)
        self.url_entry.pack(pady=Spacing.XS)

        # Dil seçimi
        ctk.CTkLabel(download_frame, text="Diller:", font=Fonts.LABEL).pack(pady=Spacing.XS)
        lang_frame = ctk.CTkFrame(download_frame)
        lang_frame.pack(pady=Spacing.XS)

        self.lang_tr_var = ctk.BooleanVar(value=True)
        self.lang_en_var = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(lang_frame, text="Türkçe", variable=self.lang_tr_var).pack(side="left", padx=Spacing.XS)
        ctk.CTkCheckBox(lang_frame, text="İngilizce", variable=self.lang_en_var).pack(side="left", padx=Spacing.XS)

        # Otomatik altyazı
        self.auto_sub_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            download_frame,
            text="Otomatik altyazıları da indir",
            variable=self.auto_sub_var
        ).pack(pady=Spacing.XS)

        # Çıkış dizini
        ctk.CTkLabel(download_frame, text="Kayıt Konumu:", font=Fonts.LABEL).pack(pady=Spacing.XS)
        dir_frame = ctk.CTkFrame(download_frame)
        dir_frame.pack(pady=Spacing.XS, fill="x", padx=Spacing.SM)

        self.output_dir_entry = ctk.CTkEntry(dir_frame, width=300)
        self.output_dir_entry.pack(side="left", padx=Spacing.XS)
        self.output_dir_entry.insert(0, str(Path.home() / "Downloads"))

        ctk.CTkButton(
            dir_frame,
            text=f"{Icons.BROWSE} Gözat",
            width=80,
            command=self.select_output_dir,
            font=Fonts.LABEL
        ).pack(side="left")

        # İndir butonu
        self.download_subtitle_btn = ctk.CTkButton(
            download_frame,
            text="Altyazıları İndir",
            command=self.download_subtitles,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            font=Fonts.LABEL_BOLD
        )
        self.download_subtitle_btn.pack(pady=Spacing.LG)

        # Sağ panel - Altyazı İşleme
        process_frame = ctk.CTkFrame(self)
        process_frame.pack(side="right", fill="both", expand=True, padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(
            process_frame,
            text="Altyazı İşleme",
            font=Fonts.H1
        ).pack(pady=Spacing.SM)

        # Dosya seçimi
        file_frame = ctk.CTkFrame(process_frame)
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
            text="Video sürükle & bırak veya seç",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        self._video_dnd_hint.pack(pady=(4, 0))

        ctk.CTkButton(
            self._video_drop_zone,
            text=f"{Icons.BROWSE} Video Seç",
            command=self.select_video_file,
            width=150,
            font=Fonts.LABEL
        ).pack(pady=Spacing.XS)

        self.video_label = ctk.CTkLabel(self._video_drop_zone, text="Video seçilmedi", font=Fonts.LABEL)
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
            text="Altyazı sürükle & bırak veya seç",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        self._subtitle_dnd_hint.pack(pady=(4, 0))

        ctk.CTkButton(
            self._subtitle_drop_zone,
            text=f"{Icons.BROWSE} Altyazı Seç",
            command=self.select_subtitle_file,
            width=150,
            font=Fonts.LABEL
        ).pack(pady=Spacing.XS)

        self.subtitle_label = ctk.CTkLabel(self._subtitle_drop_zone, text="Altyazı seçilmedi", font=Fonts.LABEL)
        self.subtitle_label.pack(pady=(0, Spacing.XS))

        # Dönüştürme
        convert_frame = ctk.CTkFrame(process_frame)
        convert_frame.pack(pady=Spacing.SM, fill="x", padx=Spacing.SM)

        ctk.CTkLabel(convert_frame, text="Format Dönüştür:", font=Fonts.LABEL_BOLD).pack(pady=Spacing.XS)
        self.format_combo = ctk.CTkComboBox(
            convert_frame,
            values=["SRT", "VTT", "ASS", "SSA"]
        )
        self.format_combo.pack(pady=Spacing.XS)

        ctk.CTkButton(
            convert_frame,
            text=f"{Icons.CONVERT_BTN} Dönüştür",
            command=self.convert_subtitle,
            font=Fonts.LABEL
        ).pack(pady=Spacing.XS)

        # Zamanlama düzenleme
        timing_frame = ctk.CTkFrame(process_frame)
        timing_frame.pack(pady=Spacing.SM, fill="x", padx=Spacing.SM)

        ctk.CTkLabel(timing_frame, text="Zaman Kaydırma (saniye):", font=Fonts.LABEL_BOLD).pack(pady=Spacing.XS)
        self.shift_slider = ctk.CTkSlider(
            timing_frame,
            from_=-10,
            to=10,
            number_of_steps=40
        )
        self.shift_slider.pack(pady=Spacing.XS, fill="x", padx=20)
        self.shift_slider.set(0)

        self.shift_label = ctk.CTkLabel(timing_frame, text="0.0s", font=Fonts.LABEL)
        self.shift_label.pack(pady=Spacing.XS)
        self.shift_slider.configure(command=lambda v: self.shift_label.configure(text=f"{v:.1f}s"))

        ctk.CTkButton(
            timing_frame,
            text="Zamanlamayı Ayarla",
            command=self.shift_timing,
            font=Fonts.LABEL
        ).pack(pady=Spacing.XS)

        # Videoya gömme
        embed_frame = ctk.CTkFrame(process_frame)
        embed_frame.pack(pady=Spacing.SM, fill="x", padx=Spacing.SM)

        ctk.CTkLabel(embed_frame, text="Videoya Ekle:", font=Fonts.LABEL_BOLD).pack(pady=Spacing.XS)

        embed_type_frame = ctk.CTkFrame(embed_frame)
        embed_type_frame.pack(pady=Spacing.XS)

        ctk.CTkButton(
            embed_type_frame,
            text="Soft Subtitle",
            command=lambda: self.embed_subtitle("soft"),
            width=150,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD
        ).pack(side="left", padx=Spacing.XS)

        ctk.CTkButton(
            embed_type_frame,
            text="Hard Subtitle",
            command=lambda: self.embed_subtitle("hard"),
            width=150,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD
        ).pack(side="left", padx=Spacing.XS)

        # Log
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(side="bottom", fill="x", padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(log_frame, text="İşlem Günlüğü", font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.log_text = ctk.CTkTextbox(log_frame, height=100, font=Fonts.MONO, fg_color=Colors.BG_INPUT)
        self.log_text.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

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
                    "Uyarı",
                    f"'{file_path.name}' bir video dosyası değil.\n"
                    f"Desteklenen formatlar: {', '.join(sorted(_VIDEO_EXTS))}"
                )
                return
            self.current_video_file = str(file_path)
            self.video_label.configure(text=file_path.name)
            self.log(f"Video bırakıldı: {file_path.name}")
        except Exception:
            pass

    def _on_subtitle_drop(self, event):
        """Handle a file dropped onto the subtitle drop zone."""
        try:
            file_path = self._parse_drop_path(event)
            self._highlight_zone(self._subtitle_drop_zone, self._subtitle_dnd_hint, False)
            if file_path.suffix.lower() not in _SUBTITLE_EXTS:
                messagebox.showwarning(
                    "Uyarı",
                    f"'{file_path.name}' bir altyazı dosyası değil.\n"
                    f"Desteklenen formatlar: {', '.join(sorted(_SUBTITLE_EXTS))}"
                )
                return
            self.current_subtitle_file = str(file_path)
            self.subtitle_label.configure(text=file_path.name)
            self.log(f"Altyazı bırakıldı: {file_path.name}")
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
            title="Video Seç",
            filetypes=[
                ("Video Dosyaları", "*.mp4 *.mkv *.avi *.mov"),
                ("Tüm Dosyalar", "*.*")
            ]
        )
        if file_path:
            self.current_video_file = file_path
            self.video_label.configure(text=Path(file_path).name)
            self.log(f"Video seçildi: {Path(file_path).name}")

    def select_subtitle_file(self):
        """Altyazı dosyası seç"""
        file_path = filedialog.askopenfilename(
            title="Altyazı Seç",
            filetypes=[
                ("Altyazı Dosyaları", "*.srt *.vtt *.ass *.ssa"),
                ("Tüm Dosyalar", "*.*")
            ]
        )
        if file_path:
            self.current_subtitle_file = file_path
            self.subtitle_label.configure(text=Path(file_path).name)
            self.log(f"Altyazı seçildi: {Path(file_path).name}")

    def download_subtitles(self):
        """Altyazıları indir"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Uyarı", "Lütfen video URL'si girin")
            return

        output_dir = self.output_dir_entry.get()

        languages = []
        if self.lang_tr_var.get():
            languages.append('tr')
        if self.lang_en_var.get():
            languages.append('en')

        if not languages:
            messagebox.showwarning("Uyarı", "En az bir dil seçin")
            return

        self.log(f"Altyazılar indiriliyor: {url}")
        self.download_subtitle_btn.configure(state="disabled", text="İndiriliyor...")

        def download_thread():
            try:
                subtitles = self.subtitle_downloader.download_subtitles(
                    url,
                    output_dir,
                    languages,
                    self.auto_sub_var.get()
                )

                if subtitles:
                    self.log(f"✅ {len(subtitles)} altyazı indirildi")
                    for sub in subtitles:
                        self.log(f"  - {sub.language}: {Path(sub.file_path).name}")
                else:
                    self.log("❌ Altyazı bulunamadı")

            except Exception as e:
                self.log(f"❌ Hata: {str(e)}")

            finally:
                self.after(0, lambda: self.download_subtitle_btn.configure(state="normal", text="Altyazıları İndir"))

        threading.Thread(target=download_thread, daemon=True).start()

    def convert_subtitle(self):
        """Altyazı formatını dönüştür"""
        if not self.current_subtitle_file:
            messagebox.showwarning("Uyarı", "Önce bir altyazı dosyası seçin")
            return

        target_format = self.format_combo.get().lower()
        output_file = str(Path(self.current_subtitle_file).with_suffix(f".{target_format}"))

        self.log(f"Dönüştürülüyor: {target_format.upper()}")

        success = self.subtitle_converter.convert(
            self.current_subtitle_file,
            SubtitleFormat[target_format.upper()],
            output_file
        )

        if success:
            self.log(f"✅ Dönüştürüldü: {Path(output_file).name}")
            self.current_subtitle_file = output_file
            self.subtitle_label.configure(text=Path(output_file).name)
        else:
            self.log("❌ Dönüştürme başarısız")

    def shift_timing(self):
        """Altyazı zamanlamasını kaydır"""
        if not self.current_subtitle_file:
            messagebox.showwarning("Uyarı", "Önce bir altyazı dosyası seçin")
            return

        shift_seconds = self.shift_slider.get()
        shift_ms = int(shift_seconds * 1000)

        output_file = str(Path(self.current_subtitle_file).with_stem(
            Path(self.current_subtitle_file).stem + "_shifted"
        ))

        self.log(f"Zamanlama kaydırılıyor: {shift_seconds:.1f}s")

        success = self.subtitle_editor.shift_timing(
            self.current_subtitle_file,
            output_file,
            shift_ms
        )

        if success:
            self.log(f"✅ Kaydırıldı: {Path(output_file).name}")
            self.current_subtitle_file = output_file
            self.subtitle_label.configure(text=Path(output_file).name)
        else:
            self.log("❌ Kaydırma başarısız")

    def embed_subtitle(self, embed_type: str):
        """Altyazıyı videoya göm"""
        if not self.current_video_file or not self.current_subtitle_file:
            messagebox.showwarning("Uyarı", "Video ve altyazı dosyası seçin")
            return

        output_file = str(Path(self.current_video_file).with_stem(
            Path(self.current_video_file).stem + f"_{embed_type}_sub"
        ))

        self.log(f"Altyazı gömülüyor ({embed_type})...")

        def embed_thread():
            try:
                if embed_type == "soft":
                    success = self.subtitle_embedder.embed_soft(
                        self.current_video_file,
                        self.current_subtitle_file,
                        output_file
                    )
                else:
                    success = self.subtitle_embedder.embed_hard(
                        self.current_video_file,
                        self.current_subtitle_file,
                        output_file
                    )

                if success:
                    self.log(f"✅ Tamamlandı: {Path(output_file).name}")
                else:
                    self.log("❌ Gömme başarısız")

            except Exception as e:
                self.log(f"❌ Hata: {str(e)}")

        threading.Thread(target=embed_thread, daemon=True).start()
