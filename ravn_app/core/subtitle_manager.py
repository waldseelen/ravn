"""
RAVN - Subtitle Management System (Faz 3)
Altyazı indirme, dönüştürme ve yönetim sistemi
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable
from enum import Enum
from dataclasses import dataclass
import logging

from ravn_app.core.runners import FFmpegRunner, YtDlpRunner, RunnerResult

logger = logging.getLogger(__name__)


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

    def __init__(self, yt_dlp_path: str = "yt-dlp"):
        self.yt_dlp_path = yt_dlp_path
        self._runner = YtDlpRunner(yt_dlp_path)

    def download_subtitles(
        self,
        video_url: str,
        output_dir: str,
        languages: Optional[List[str]] = None,
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

        # yt-dlp args for subtitle-only download
        args = [
            '--write-subs',
            '--sub-langs', ','.join(languages),
            '--skip-download',
            '-o', os.path.join(output_dir, '%(title)s.%(ext)s'),
            '--quiet',
        ]
        
        if auto_sub:
            args.append('--write-auto-subs')

        # Run using YtDlpRunner
        result = self._runner.download(video_url, output_dir, extra_args=args)
        
        if not result.success:
            logger.error(f"Altyazı indirme hatası: {result.error_message}")
            return []

        # Find downloaded subtitle files
        downloaded_subs = []
        for lang in languages:
            # Look for subtitle files with various extensions
            for ext in ['vtt', 'srt', 'ass', 'ssa']:
                pattern = os.path.join(output_dir, f"*.{lang}.{ext}")
                import glob
                for sub_file in glob.glob(pattern):
                    try:
                        fmt = SubtitleFormat(ext)
                    except ValueError:
                        fmt = SubtitleFormat.VTT
                    
                    downloaded_subs.append(SubtitleInfo(
                        language=lang,
                        format=fmt,
                        file_path=sub_file,
                        is_auto_generated='auto' in sub_file.lower()
                    ))
        
        return downloaded_subs

    def list_available_subtitles(self, video_url: str) -> Dict[str, List[str]]:
        """Video için mevcut altyazıları listele"""
        result = self._runner.extract_info(video_url)
        
        if not result.success:
            logger.error(f"Altyazı listeleme hatası: {result.error_message}")
            return {'manual': [], 'automatic': []}

        info = result.metadata.get('info', {})
        
        return {
            'manual': list(info.get('subtitles', {}).keys()),
            'automatic': list(info.get('automatic_captions', {}).keys())
        }


class SubtitleConverter:
    """Altyazı format dönüştürücü - FFmpegRunner kullanır"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self._runner = FFmpegRunner(ffmpeg_path, ffprobe_path)

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
            logger.error(f"Dosya bulunamadı: {input_file}")
            return False

        if output_file is None:
            input_path = Path(input_file)
            output_file = str(input_path.with_suffix(f'.{output_format.value}'))

        result = self._runner.run_raw(
            args=[
                '-i', input_file,
                '-y',
                output_file
            ]
        )

        if result.success:
            logger.info(f"Altyazı dönüştürme başarılı: {output_file}")
            return True
        else:
            logger.error(f"Altyazı dönüştürme hatası: {result.error_message}")
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
            logger.error(f"SRT->VTT dönüştürme hatası: {e}")
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
            logger.error(f"VTT->SRT dönüştürme hatası: {e}")
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
            logger.error(f"Zaman kaydırma hatası: {e}")
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
            logger.error(f"Altyazı birleştirme hatası: {e}")
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
            logger.error(f"Formatlama kaldırma hatası: {e}")
            return False


class SubtitleEmbedder:
    """Videoylara altyazı gömme - FFmpegRunner kullanır"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self._runner = FFmpegRunner(ffmpeg_path, ffprobe_path)

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
        if not os.path.exists(video_file):
            logger.error(f"Video dosyası bulunamadı: {video_file}")
            return False
        
        if not os.path.exists(subtitle_file):
            logger.error(f"Altyazı dosyası bulunamadı: {subtitle_file}")
            return False

        result = self._runner.run_raw(
            args=[
                '-i', video_file,
                '-i', subtitle_file,
                '-c', 'copy',
                '-c:s', 'mov_text',
                '-metadata:s:s:0', f'language={language}',
                '-y',
                output_file
            ]
        )

        if result.success:
            logger.info(f"Soft subtitle ekleme başarılı: {output_file}")
            return True
        else:
            logger.error(f"Soft subtitle ekleme hatası: {result.error_message}")
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
        if not os.path.exists(video_file):
            logger.error(f"Video dosyası bulunamadı: {video_file}")
            return False
        
        if not os.path.exists(subtitle_file):
            logger.error(f"Altyazı dosyası bulunamadı: {subtitle_file}")
            return False

        # Windows path'lerini düzelt
        subtitle_path = subtitle_file.replace('\\', '/').replace(':', '\\:')

        result = self._runner.run_raw(
            args=[
                '-i', video_file,
                '-vf', f"subtitles='{subtitle_path}':force_style='FontSize={font_size},PrimaryColour={font_color}'",
                '-c:a', 'copy',
                '-y',
                output_file
            ]
        )

        if result.success:
            logger.info(f"Hard subtitle ekleme başarılı: {output_file}")
            return True
        else:
            logger.error(f"Hard subtitle ekleme hatası: {result.error_message}")
            return False

    def extract_subtitles(
        self,
        video_file: str,
        output_file: str,
        stream_index: int = 0
    ) -> bool:
        """Videodan altyazıyı çıkart"""
        if not os.path.exists(video_file):
            logger.error(f"Video dosyası bulunamadı: {video_file}")
            return False

        result = self._runner.run_raw(
            args=[
                '-i', video_file,
                '-map', f'0:s:{stream_index}',
                '-y',
                output_file
            ]
        )

        if result.success:
            logger.info(f"Altyazı çıkartma başarılı: {output_file}")
            return True
        else:
            logger.error(f"Altyazı çıkartma hatası: {result.error_message}")
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
