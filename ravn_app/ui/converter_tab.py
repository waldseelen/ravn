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


class ConverterTab(ctk.CTkFrame):
    """Video converter sekmesi"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.converter = VideoConverter()
        self.batch_converter = None
        self.conversion_thread = None
        self.is_converting = False

        self.setup_ui()

    def setup_ui(self):
        """UI bileşenlerini kur"""
        # Başlık
        title = ctk.CTkLabel(
            self,
            text="🔄 Video Dönüştürücü",
            font=("Arial", 20, "bold")
        )
        title.pack(pady=10, padx=10)

        # Ana frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ===== Giriş Dosyası =====
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(input_frame, text="Giriş Dosyası:", font=("Arial", 12, "bold")).pack(anchor="w")

        input_subframe = ctk.CTkFrame(input_frame)
        input_subframe.pack(fill="x", pady=5)

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
        options_frame.pack(fill="x", pady=10)

        # Video Codec
        video_frame = ctk.CTkFrame(options_frame)
        video_frame.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkLabel(video_frame, text="Video Codec:", font=("Arial", 11, "bold")).pack(anchor="w")
        self.video_codec = ctk.CTkComboBox(
            video_frame,
            values=list(CodecManager.VIDEO_CODECS.keys()),
            state="readonly"
        )
        self.video_codec.set("h264")
        self.video_codec.pack(fill="x", pady=5)

        # Ses Codec
        audio_frame = ctk.CTkFrame(options_frame)
        audio_frame.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkLabel(audio_frame, text="Ses Codec:", font=("Arial", 11, "bold")).pack(anchor="w")
        self.audio_codec = ctk.CTkComboBox(
            audio_frame,
            values=list(CodecManager.AUDIO_CODECS.keys()),
            state="readonly"
        )
        self.audio_codec.set("aac")
        self.audio_codec.pack(fill="x", pady=5)

        # Kalite
        quality_frame = ctk.CTkFrame(options_frame)
        quality_frame.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkLabel(quality_frame, text="Kalite:", font=("Arial", 11, "bold")).pack(anchor="w")
        self.quality = ctk.CTkComboBox(
            quality_frame,
            values=["Kayıpsız", "Çok Yüksek", "Yüksek", "Orta", "Düşük", "Çok Düşük"],
            state="readonly"
        )
        self.quality.set("Yüksek")
        self.quality.pack(fill="x", pady=5)

        # ===== İleri Ayarlar =====
        advanced_frame = ctk.CTkFrame(main_frame)
        advanced_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(advanced_frame, text="İleri Ayarlar:", font=("Arial", 11, "bold")).pack(anchor="w", pady=5)

        # Hız Preset
        preset_frame = ctk.CTkFrame(advanced_frame)
        preset_frame.pack(fill="x", pady=5)

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
        bitrate_frame.pack(fill="x", pady=5)

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
        output_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(output_frame, text="Çıkış Dosyası:", font=("Arial", 12, "bold")).pack(anchor="w")

        output_subframe = ctk.CTkFrame(output_frame)
        output_subframe.pack(fill="x", pady=5)

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
        progress_frame.pack(fill="x", pady=10)

        self.progress_var = ctk.DoubleVar(value=0)
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            variable=self.progress_var
        )
        self.progress_bar.pack(fill="x", pady=5)

        # Status
        self.status_label = ctk.CTkLabel(
            progress_frame,
            text="Hazır",
            font=("Arial", 10),
            text_color="#00AA00"
        )
        self.status_label.pack(anchor="w", pady=5)

        # ===== Log Alanı =====
        log_frame = ctk.CTkFrame(main_frame)
        log_frame.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(log_frame, text="İşlem Günlüğü:", font=("Arial", 11, "bold")).pack(anchor="w")

        scrollbar = ctk.CTkScrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_text = ctk.CTkTextbox(
            log_frame,
            yscrollcommand=scrollbar.set,
            height=150
        )
        self.log_text.pack(fill="both", expand=True, pady=5)
        scrollbar.configure(command=self.log_text.yview)

        # ===== Butonlar =====
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=10)

        self.convert_btn = ctk.CTkButton(
            button_frame,
            text="▶ Dönüştür",
            command=self.start_conversion,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        self.convert_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            button_frame,
            text="⏹ Durdur",
            command=self.stop_conversion,
            fg_color="#f44336",
            hover_color="#da190b",
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

        self.clear_btn = ctk.CTkButton(
            button_frame,
            text="🗑 Temizle",
            command=self.clear_fields,
            fg_color="#2196F3",
            hover_color="#0b7dda"
        )
        self.clear_btn.pack(side="left", padx=5)

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
        self.log_add("Dönüştürme başlatılıyor...")

        self.conversion_thread = Thread(
            target=self._conversion_worker,
            args=(settings,),
            daemon=True
        )
        self.conversion_thread.start()

    def _conversion_worker(self, settings: ConversionSettings):
        """Dönüştürme işçisi (thread'de çalışır)"""
        self.converter.set_status_callback(self.log_add)
        success = self.converter.convert(settings)

        self.is_converting = False
        self.convert_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

        if success:
            self.status_label.configure(text="✓ Dönüştürme tamamlandı", text_color="#00AA00")
            self.progress_var.set(100)
            messagebox.showinfo("Başarılı", f"Video başarıyla dönüştürüldü:\n{settings.output_file}")
        else:
            self.status_label.configure(text="✗ Dönüştürme başarısız", text_color="#FF0000")
            messagebox.showerror("Hata", "Dönüştürme sırasında hata oluştu")

    def stop_conversion(self):
        """Dönüştürmeyi durdur"""
        self.converter.stop()
        self.is_converting = False
        self.convert_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="Durduruldu", text_color="#FFA500")
        self.log_add("Dönüştürme durduruldu")

    def clear_fields(self):
        """Alanları temizle"""
        self.input_path.delete(0, "end")
        self.output_path.delete(0, "end")
        self.log_text.delete("1.0", "end")
        self.progress_var.set(0)
        self.status_label.configure(text="Hazır", text_color="#00AA00")
        self.video_codec.set("h264")
        self.audio_codec.set("aac")
        self.quality.set("Yüksek")

    def log_add(self, message: str):
        """Günlüğe mesaj ekle"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
