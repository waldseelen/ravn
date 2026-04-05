"""
FFmpeg Codec Denetleyicisi - Desteklenen codec'leri kontrol et
"""

import json
from typing import Dict, List

from ravn_app.core.runners.ffmpeg import FFmpegRunner


class FFmpegCodecChecker:
    """FFmpeg'in desteklediği codec'leri kontrol et"""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.codecs_cache = None
        self.encoders_cache = None
        self.runner = FFmpegRunner(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)
    
    def get_supported_codecs(self) -> List[str]:
        """Desteklenen codec'lerin listesini al"""
        if self.codecs_cache is not None:
            return self.codecs_cache

        data = self.runner.run_ffprobe_json(["-codecs", "-of", "json"], timeout=30)
        if data:
            self.codecs_cache = [c.get('name') for c in data.get('codecs', [])]
            return self.codecs_cache
        return []
    
    def is_codec_supported(self, codec_name: str) -> bool:
        """Belirtilen codec destekleniyor mu"""
        return codec_name in self.get_supported_codecs()
    
    def check_video_codecs(self) -> Dict[str, bool]:
        """Desteklenen video codec'leri kontrol et"""
        video_codecs = {
            'h264': 'libx264',
            'h265': 'libx265',
            'vp8': 'libvpx',
            'vp9': 'libvpx-vp9',
            'av1': 'libaom-av1',
        }
        
        return {
            name: self.is_codec_supported(lib)
            for name, lib in video_codecs.items()
        }
    
    def check_audio_codecs(self) -> Dict[str, bool]:
        """Desteklenen ses codec'lerini kontrol et"""
        audio_codecs = {
            'aac': 'aac',
            'mp3': 'libmp3lame',
            'opus': 'libopus',
            'vorbis': 'libvorbis',
            'flac': 'flac',
        }
        
        return {
            name: self.is_codec_supported(lib)
            for name, lib in audio_codecs.items()
        }
    
    def get_ffmpeg_info(self) -> Dict:
        """FFmpeg hakkında detaylı bilgi"""
        version_line = self.runner.get_version()
        if version_line:
            return {
                "version": version_line,
                "available": True,
                "video_codecs": self.check_video_codecs(),
                "audio_codecs": self.check_audio_codecs()
            }
        return {"available": False}


# Test
if __name__ == "__main__":
    checker = FFmpegCodecChecker()
    info = checker.get_ffmpeg_info()
    
    print("FFmpeg Bilgisi:")
    print(json.dumps(info, indent=2, ensure_ascii=False))
