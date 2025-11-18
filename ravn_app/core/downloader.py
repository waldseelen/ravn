"""
YouTube indirme motoru - yt-dlp entegrasyonu
"""

import yt_dlp
import os
import threading
import queue


class YouTubeDownloader:
    """YouTube videolarını indirmek için ana sınıf"""
    
    def __init__(self):
        self.download_queue = queue.Queue()
        self.is_worker_active = False
        self.active_downloads = {}
    
    def extract_video_info(self, url):
        """Video bilgilerini YouTube'dan çek"""
        try:
            with yt_dlp.YoutubeDL({
                'quiet': True,
                'extract_flat': True,
                'force_generic_extractor': True
            }) as ydl:
                info = ydl.extract_info(url, download=False)
            return info
        except Exception as e:
            raise Exception(f"Bilgi alınamadı: {str(e)}")
    
    def get_video_format_options(self):
        """Desteklenen format seçenekleri"""
        return {
            "MP4 (Video)": {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "postprocessors": []
            },
            "MP3 (Ses)": {
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }]
            }
        }
    
    def get_quality_options(self):
        """Kalite seçenekleri"""
        return ["En İyi", "1080p", "720p", "480p"]
    
    @staticmethod
    def sanitize_filename(name):
        """Dosya adını temizle"""
        import re
        return re.sub(r'[\/*?:"<>|]', "", name)
