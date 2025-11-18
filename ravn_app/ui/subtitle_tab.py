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
        download_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            download_frame,
            text="🎬 Altyazı İndir",
            font=("Arial", 16, "bold")
        ).pack(pady=10)

        # Video URL
        ctk.CTkLabel(download_frame, text="Video URL:").pack(pady=5)
        self.url_entry = ctk.CTkEntry(download_frame, width=400)
        self.url_entry.pack(pady=5)

        # Dil seçimi
        ctk.CTkLabel(download_frame, text="Diller:").pack(pady=5)
        lang_frame = ctk.CTkFrame(download_frame)
        lang_frame.pack(pady=5)

        self.lang_tr_var = ctk.BooleanVar(value=True)
        self.lang_en_var = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(lang_frame, text="Türkçe", variable=self.lang_tr_var).pack(side="left", padx=5)
        ctk.CTkCheckBox(lang_frame, text="İngilizce", variable=self.lang_en_var).pack(side="left", padx=5)

        # Otomatik altyazı
        self.auto_sub_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            download_frame,
            text="Otomatik altyazıları da indir",
            variable=self.auto_sub_var
        ).pack(pady=5)

        # Çıkış dizini
        ctk.CTkLabel(download_frame, text="Kayıt Konumu:").pack(pady=5)
        dir_frame = ctk.CTkFrame(download_frame)
        dir_frame.pack(pady=5, fill="x", padx=10)

        self.output_dir_entry = ctk.CTkEntry(dir_frame, width=300)
        self.output_dir_entry.pack(side="left", padx=5)
        self.output_dir_entry.insert(0, str(Path.home() / "Downloads"))

        ctk.CTkButton(
            dir_frame,
            text="Gözat",
            width=80,
            command=self.select_output_dir
        ).pack(side="left")

        # İndir butonu
        ctk.CTkButton(
            download_frame,
            text="🎯 Altyazıları İndir",
            command=self.download_subtitles,
            height=40
        ).pack(pady=20)

        # Sağ panel - Altyazı İşleme
        process_frame = ctk.CTkFrame(self)
        process_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            process_frame,
            text="⚙️ Altyazı İşleme",
            font=("Arial", 16, "bold")
        ).pack(pady=10)

        # Dosya seçimi
        file_frame = ctk.CTkFrame(process_frame)
        file_frame.pack(pady=10, fill="x", padx=10)

        ctk.CTkButton(
            file_frame,
            text="📁 Video Seç",
            command=self.select_video_file,
            width=150
        ).pack(pady=5)

        self.video_label = ctk.CTkLabel(file_frame, text="Video seçilmedi")
        self.video_label.pack(pady=5)

        ctk.CTkButton(
            file_frame,
            text="📄 Altyazı Seç",
            command=self.select_subtitle_file,
            width=150
        ).pack(pady=5)

        self.subtitle_label = ctk.CTkLabel(file_frame, text="Altyazı seçilmedi")
        self.subtitle_label.pack(pady=5)

        # Dönüştürme
        convert_frame = ctk.CTkFrame(process_frame)
        convert_frame.pack(pady=10, fill="x", padx=10)

        ctk.CTkLabel(convert_frame, text="Format Dönüştür:").pack(pady=5)
        self.format_combo = ctk.CTkComboBox(
            convert_frame,
            values=["SRT", "VTT", "ASS", "SSA"]
        )
        self.format_combo.pack(pady=5)

        ctk.CTkButton(
            convert_frame,
            text="🔄 Dönüştür",
            command=self.convert_subtitle
        ).pack(pady=5)

        # Zamanlama düzenleme
        timing_frame = ctk.CTkFrame(process_frame)
        timing_frame.pack(pady=10, fill="x", padx=10)

        ctk.CTkLabel(timing_frame, text="Zaman Kaydırma (saniye):").pack(pady=5)
        self.shift_slider = ctk.CTkSlider(
            timing_frame,
            from_=-10,
            to=10,
            number_of_steps=40
        )
        self.shift_slider.pack(pady=5, fill="x", padx=20)
        self.shift_slider.set(0)

        self.shift_label = ctk.CTkLabel(timing_frame, text="0.0s")
        self.shift_label.pack(pady=5)
        self.shift_slider.configure(command=lambda v: self.shift_label.configure(text=f"{v:.1f}s"))

        ctk.CTkButton(
            timing_frame,
            text="⏱️ Zamanlamayı Ayarla",
            command=self.shift_timing
        ).pack(pady=5)

        # Videoya gömme
        embed_frame = ctk.CTkFrame(process_frame)
        embed_frame.pack(pady=10, fill="x", padx=10)

        ctk.CTkLabel(embed_frame, text="Videoya Ekle:").pack(pady=5)

        embed_type_frame = ctk.CTkFrame(embed_frame)
        embed_type_frame.pack(pady=5)

        ctk.CTkButton(
            embed_type_frame,
            text="Soft Subtitle",
            command=lambda: self.embed_subtitle("soft"),
            width=150
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            embed_type_frame,
            text="Hard Subtitle",
            command=lambda: self.embed_subtitle("hard"),
            width=150
        ).pack(side="left", padx=5)

        # Log
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        ctk.CTkLabel(log_frame, text="📝 Log:").pack(anchor="w", padx=5, pady=5)
        self.log_text = ctk.CTkTextbox(log_frame, height=100)
        self.log_text.pack(fill="x", padx=5, pady=5)

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
