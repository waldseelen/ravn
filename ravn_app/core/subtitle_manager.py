"""
RAVN - Subtitle Management System (Faz 3)
Altyazı indirme, dönüştürme ve yönetim sistemi
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import logging


class SubtitleFormat(Enum):
    """Desteklenen altyazı formatları"""
    SRT = "srt"      # SubRip
    VTT = "vtt"      # WebVTT
    ASS = "ass"      # Advanced SubStation Alpha
    SSA = "ssa"      # SubStation Alpha
    SUB = "sub"      # MicroDVD


@dataclass
class SubtitleInfo:
    """Altyazı bilgileri"""
    language: str
    format: SubtitleFormat
    file_path: str
    is_auto_generated: bool = False
    line_count: int = 0


class SubtitleDownloader:
    """YouTube ve diğer platformlardan altyazı indirir"""

    def __init__(self):
        self.yt_dlp_path = "yt-dlp"

    def download_subtitles(
        self,
        video_url: str,
        output_dir: str,
        languages: List[str] = None,
        auto_sub: bool = True
    ) -> List[SubtitleInfo]:
        """
        Video URL'sinden altyazıları indir

        Args:
            video_url: Video URL'si
            output_dir: Çıkış dizini
            languages: İndirilecek diller (None = tümü)
            auto_sub: Otomatik altyazıları da indir

        Returns:
            İndirilen altyazıların listesi
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        languages = languages or ['tr', 'en']

        options = {
            'writesubtitles': True,
            'writeautomaticsub': auto_sub,
            'subtitleslangs': languages,
            'skip_download': True,
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'quiet': True
        }

        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(video_url, download=True)

                downloaded_subs = []
                if 'requested_subtitles' in info:
                    for lang, sub_info in info['requested_subtitles'].items():
                        if sub_info and 'filepath' in sub_info:
                            downloaded_subs.append(SubtitleInfo(
                                language=lang,
                                format=SubtitleFormat.VTT,
                                file_path=sub_info['filepath'],
                                is_auto_generated=False
                            ))

                return downloaded_subs

        except Exception as e:
            logging.error(f"Altyazı indirme hatası: {e}")
            return []

    def list_available_subtitles(self, video_url: str) -> Dict[str, List[str]]:
        """Video için mevcut altyazıları listele"""
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(video_url, download=False)

                result = {
                    'manual': [],
                    'automatic': []
                }

                if 'subtitles' in info:
                    result['manual'] = list(info['subtitles'].keys())

                if 'automatic_captions' in info:
                    result['automatic'] = list(info['automatic_captions'].keys())

                return result

        except Exception as e:
            logging.error(f"Altyazı listeleme hatası: {e}")
            return {'manual': [], 'automatic': []}


class SubtitleConverter:
    """Altyazı format dönüştürücü"""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def convert(
        self,
        input_file: str,
        output_format: SubtitleFormat,
        output_file: Optional[str] = None
    ) -> bool:
        """
        Altyazı formatını dönüştür

        Args:
            input_file: Giriş altyazı dosyası
            output_format: Hedef format
            output_file: Çıkış dosyası (None = otomatik)

        Returns:
            Başarılı ise True
        """
        if not os.path.exists(input_file):
            return False

        if output_file is None:
            input_path = Path(input_file)
            output_file = str(input_path.with_suffix(f'.{output_format.value}'))

        cmd = [
            self.ffmpeg_path,
            '-i', input_file,
            '-y',
            output_file
        ]

        try:
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0
        except Exception as e:
            logging.error(f"Altyazı dönüştürme hatası: {e}")
            return False

    def srt_to_vtt(self, srt_file: str, vtt_file: str) -> bool:
        """SRT'den VTT'ye dönüştür"""
        try:
            with open(srt_file, 'r', encoding='utf-8') as f:
                srt_content = f.read()

            vtt_content = "WEBVTT\n\n" + srt_content.replace(',', '.')

            with open(vtt_file, 'w', encoding='utf-8') as f:
                f.write(vtt_content)

            return True
        except Exception as e:
            logging.error(f"SRT->VTT dönüştürme hatası: {e}")
            return False

    def vtt_to_srt(self, vtt_file: str, srt_file: str) -> bool:
        """VTT'den SRT'ye dönüştür"""
        try:
            with open(vtt_file, 'r', encoding='utf-8') as f:
                vtt_content = f.read()

            # WEBVTT header'ını kaldır
            srt_content = re.sub(r'^WEBVTT\n\n', '', vtt_content)
            srt_content = srt_content.replace('.', ',')

            with open(srt_file, 'w', encoding='utf-8') as f:
                f.write(srt_content)

            return True
        except Exception as e:
            logging.error(f"VTT->SRT dönüştürme hatası: {e}")
            return False


class SubtitleEditor:
    """Altyazı düzenleme ve senkronizasyon"""

    def __init__(self):
        pass

    def shift_timing(
        self,
        input_file: str,
        output_file: str,
        shift_ms: int
    ) -> bool:
        """
        Altyazı zamanlamasını kaydır

        Args:
            input_file: Giriş dosyası
            output_file: Çıkış dosyası
            shift_ms: Kaydırma miktarı (milisaniye)

        Returns:
            Başarılı ise True
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # SRT formatı için zaman kaydırma
            def shift_time(match):
                time_str = match.group(0)
                parts = re.findall(r'\d+', time_str)

                h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, parts)

                total_ms1 = h1 * 3600000 + m1 * 60000 + s1 * 1000 + ms1 + shift_ms
                total_ms2 = h2 * 3600000 + m2 * 60000 + s2 * 1000 + ms2 + shift_ms

                total_ms1 = max(0, total_ms1)
                total_ms2 = max(0, total_ms2)

                h1 = total_ms1 // 3600000
                m1 = (total_ms1 % 3600000) // 60000
                s1 = (total_ms1 % 60000) // 1000
                ms1 = total_ms1 % 1000

                h2 = total_ms2 // 3600000
                m2 = (total_ms2 % 3600000) // 60000
                s2 = (total_ms2 % 60000) // 1000
                ms2 = total_ms2 % 1000

                return f"{h1:02d}:{m1:02d}:{s1:02d},{ms1:03d} --> {h2:02d}:{m2:02d}:{s2:02d},{ms2:03d}"

            # Zaman pattern'ini bul ve değiştir
            pattern = r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}'
            new_content = re.sub(pattern, shift_time, content)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return True

        except Exception as e:
            logging.error(f"Zaman kaydırma hatası: {e}")
            return False

    def merge_subtitles(
        self,
        subtitle_files: List[str],
        output_file: str
    ) -> bool:
        """Birden fazla altyazıyı birleştir"""
        try:
            all_subtitles = []

            for file in subtitle_files:
                with open(file, 'r', encoding='utf-8') as f:
                    all_subtitles.append(f.read())

            merged = "\n\n".join(all_subtitles)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(merged)

            return True

        except Exception as e:
            logging.error(f"Altyazı birleştirme hatası: {e}")
            return False

    def remove_formatting(self, input_file: str, output_file: str) -> bool:
        """HTML/ASS formatlamasını kaldır"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # HTML tag'lerini kaldır
            clean_content = re.sub(r'<[^>]+>', '', content)

            # ASS/SSA stil kodlarını kaldır
            clean_content = re.sub(r'\{[^}]+\}', '', clean_content)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(clean_content)

            return True

        except Exception as e:
            logging.error(f"Formatlama kaldırma hatası: {e}")
            return False


class SubtitleEmbedder:
    """Videoylara altyazı gömme (hard-sub)"""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def embed_soft(
        self,
        video_file: str,
        subtitle_file: str,
        output_file: str,
        language: str = "tr"
    ) -> bool:
        """
        Soft subtitle ekle (ayrı stream olarak)

        Args:
            video_file: Video dosyası
            subtitle_file: Altyazı dosyası
            output_file: Çıkış dosyası
            language: Altyazı dili

        Returns:
            Başarılı ise True
        """
        cmd = [
            self.ffmpeg_path,
            '-i', video_file,
            '-i', subtitle_file,
            '-c', 'copy',
            '-c:s', 'mov_text',
            '-metadata:s:s:0', f'language={language}',
            '-y',
            output_file
        ]

        try:
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0
        except Exception as e:
            logging.error(f"Soft subtitle ekleme hatası: {e}")
            return False

    def embed_hard(
        self,
        video_file: str,
        subtitle_file: str,
        output_file: str,
        font_size: int = 24,
        font_color: str = "white"
    ) -> bool:
        """
        Hard subtitle ekle (videoya gömülü)

        Args:
            video_file: Video dosyası
            subtitle_file: Altyazı dosyası
            output_file: Çıkış dosyası
            font_size: Font boyutu
            font_color: Font rengi

        Returns:
            Başarılı ise True
        """
        # Windows path'lerini düzelt
        subtitle_path = subtitle_file.replace('\\', '/').replace(':', '\\:')

        cmd = [
            self.ffmpeg_path,
            '-i', video_file,
            '-vf', f"subtitles='{subtitle_path}':force_style='FontSize={font_size},PrimaryColour={font_color}'",
            '-c:a', 'copy',
            '-y',
            output_file
        ]

        try:
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0
        except Exception as e:
            logging.error(f"Hard subtitle ekleme hatası: {e}")
            return False

    def extract_subtitles(
        self,
        video_file: str,
        output_file: str,
        stream_index: int = 0
    ) -> bool:
        """Videodan altyazıyı çıkart"""
        cmd = [
            self.ffmpeg_path,
            '-i', video_file,
            '-map', f'0:s:{stream_index}',
            '-y',
            output_file
        ]

        try:
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0
        except Exception as e:
            logging.error(f"Altyazı çıkartma hatası: {e}")
            return False


# ===== Utility Functions =====

def detect_subtitle_format(file_path: str) -> Optional[SubtitleFormat]:
    """Altyazı formatını tespit et"""
    ext = Path(file_path).suffix.lower()[1:]

    format_map = {
        'srt': SubtitleFormat.SRT,
        'vtt': SubtitleFormat.VTT,
        'ass': SubtitleFormat.ASS,
        'ssa': SubtitleFormat.SSA,
        'sub': SubtitleFormat.SUB,
    }

    return format_map.get(ext)


def count_subtitle_lines(file_path: str) -> int:
    """Altyazı satır sayısını say"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Boş satırları say
        lines = [line for line in content.split('\n') if line.strip() and not line.strip().isdigit()]
        return len(lines)
    except:
        return 0
