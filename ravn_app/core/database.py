"""
RAVN - Database and Configuration Management (Faz 4)
SQLite veritabanı ve konfigürasyon yönetimi
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class DownloadStatus(Enum):
    """İndirme durumu"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadRecord:
    """İndirme kaydı"""
    id: Optional[int] = None
    url: str = ""
    title: str = ""
    format: str = ""
    quality: str = ""
    file_path: str = ""
    file_size: int = 0
    download_date: str = ""
    status: str = DownloadStatus.COMPLETED.value
    duration: float = 0.0
    thumbnail_url: str = ""


@dataclass
class ConversionRecord:
    """Dönüştürme kaydı"""
    id: Optional[int] = None
    input_file: str = ""
    output_file: str = ""
    input_codec: str = ""
    output_codec: str = ""
    conversion_date: str = ""
    duration: float = 0.0
    status: str = DownloadStatus.COMPLETED.value


class DatabaseManager:
    """SQLite veritabanı yöneticisi"""

    def __init__(self, db_path: str = "ravn_history.db"):
        """
        DatabaseManager'ı başlat

        Args:
            db_path: Veritabanı dosya yolu
        """
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Veritabanına bağlan"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        except Exception as e:
            print(f"Veritabanı bağlantı hatası: {e}")

    def _create_tables(self):
        """Tabloları oluştur"""
        if not self.conn:
            return

        cursor = self.conn.cursor()

        # İndirme geçmişi tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT,
                format TEXT,
                quality TEXT,
                file_path TEXT,
                file_size INTEGER,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'completed',
                duration REAL,
                thumbnail_url TEXT
            )
        ''')

        # Dönüştürme geçmişi tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_file TEXT NOT NULL,
                output_file TEXT NOT NULL,
                input_codec TEXT,
                output_codec TEXT,
                conversion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration REAL,
                status TEXT DEFAULT 'completed'
            )
        ''')

        # Favoriler tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Playlist geçmişi
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT,
                video_count INTEGER,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def add_download(self, record: DownloadRecord) -> int:
        """İndirme kaydı ekle"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO downloads (
                url, title, format, quality, file_path, file_size,
                download_date, status, duration, thumbnail_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.url, record.title, record.format, record.quality,
            record.file_path, record.file_size, record.download_date,
            record.status, record.duration, record.thumbnail_url
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_downloads(
        self,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[DownloadRecord]:
        """İndirme kayıtlarını getir"""
        cursor = self.conn.cursor()

        if status:
            cursor.execute('''
                SELECT * FROM downloads
                WHERE status = ?
                ORDER BY download_date DESC
                LIMIT ?
            ''', (status, limit))
        else:
            cursor.execute('''
                SELECT * FROM downloads
                ORDER BY download_date DESC
                LIMIT ?
            ''', (limit,))

        rows = cursor.fetchall()
        return [self._row_to_download_record(row) for row in rows]

    def add_conversion(self, record: ConversionRecord) -> int:
        """Dönüştürme kaydı ekle"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO conversions (
                input_file, output_file, input_codec, output_codec,
                conversion_date, duration, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.input_file, record.output_file, record.input_codec,
            record.output_codec, record.conversion_date, record.duration,
            record.status
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_conversions(self, limit: int = 100) -> List[ConversionRecord]:
        """Dönüştürme kayıtlarını getir"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM conversions
            ORDER BY conversion_date DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        return [self._row_to_conversion_record(row) for row in rows]

    def add_favorite(self, url: str, title: str) -> bool:
        """Favorilere ekle"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO favorites (url, title)
                VALUES (?, ?)
            ''', (url, title))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Zaten var

    def get_favorites(self) -> List[Dict]:
        """Favorileri getir"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM favorites ORDER BY added_date DESC')

        return [dict(row) for row in cursor.fetchall()]

    def remove_favorite(self, url: str) -> bool:
        """Favorilerden kaldır"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM favorites WHERE url = ?', (url,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_statistics(self) -> Dict[str, Any]:
        """İstatistikleri al"""
        cursor = self.conn.cursor()

        stats = {}

        # Toplam indirme sayısı
        cursor.execute('SELECT COUNT(*) FROM downloads')
        stats['total_downloads'] = cursor.fetchone()[0]

        # Toplam dosya boyutu
        cursor.execute('SELECT SUM(file_size) FROM downloads')
        stats['total_size'] = cursor.fetchone()[0] or 0

        # Başarılı indirmeler
        cursor.execute('SELECT COUNT(*) FROM downloads WHERE status = ?', ('completed',))
        stats['successful_downloads'] = cursor.fetchone()[0]

        # Toplam dönüştürme
        cursor.execute('SELECT COUNT(*) FROM conversions')
        stats['total_conversions'] = cursor.fetchone()[0]

        # En popüler format
        cursor.execute('''
            SELECT format, COUNT(*) as count
            FROM downloads
            GROUP BY format
            ORDER BY count DESC
            LIMIT 1
        ''')
        result = cursor.fetchone()
        stats['most_popular_format'] = dict(result) if result else None

        return stats

    def clear_history(self, table: str = "all") -> bool:
        """Geçmişi temizle"""
        cursor = self.conn.cursor()

        if table == "all":
            cursor.execute('DELETE FROM downloads')
            cursor.execute('DELETE FROM conversions')
        elif table == "downloads":
            cursor.execute('DELETE FROM downloads')
        elif table == "conversions":
            cursor.execute('DELETE FROM conversions')

        self.conn.commit()
        return True

    def _row_to_download_record(self, row) -> DownloadRecord:
        """SQLite row'unu DownloadRecord'a çevir"""
        return DownloadRecord(
            id=row['id'],
            url=row['url'],
            title=row['title'],
            format=row['format'],
            quality=row['quality'],
            file_path=row['file_path'],
            file_size=row['file_size'],
            download_date=row['download_date'],
            status=row['status'],
            duration=row['duration'],
            thumbnail_url=row['thumbnail_url']
        )

    def _row_to_conversion_record(self, row) -> ConversionRecord:
        """SQLite row'unu ConversionRecord'a çevir"""
        return ConversionRecord(
            id=row['id'],
            input_file=row['input_file'],
            output_file=row['output_file'],
            input_codec=row['input_codec'],
            output_codec=row['output_codec'],
            conversion_date=row['conversion_date'],
            duration=row['duration'],
            status=row['status']
        )

    def close(self):
        """Veritabanı bağlantısını kapat"""
        if self.conn:
            self.conn.close()


class ConfigManager:
    """Konfigürasyon yöneticisi"""

    DEFAULT_CONFIG = {
        'default_download_path': str(Path.home() / 'Downloads' / 'RAVN'),
        'default_format': 'MP4',
        'default_quality': '1080p',
        'theme': 'nordic',
        'concurrent_downloads': 1,
        'auto_cleanup': False,
        'auto_update_check': True,
        'ffmpeg_path': 'ffmpeg',
        'language': 'tr',
        'notifications_enabled': True,
        'history_limit': 1000,
        'auto_subtitle_download': False,
        'preferred_subtitle_language': 'tr',
    }

    def __init__(self, config_file: str = "ravn_config.json"):
        """
        ConfigManager'ı başlat

        Args:
            config_file: Konfigürasyon dosyası yolu
        """
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Konfigürasyonu yükle"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Eksik anahtarları varsayılan değerlerle doldur
                    for key, value in self.DEFAULT_CONFIG.items():
                        if key not in loaded_config:
                            loaded_config[key] = value
                    return loaded_config
            except Exception as e:
                print(f"Konfigürasyon yükleme hatası: {e}")
                return self.DEFAULT_CONFIG.copy()
        else:
            return self.DEFAULT_CONFIG.copy()

    def save_config(self) -> bool:
        """Konfigürasyonu kaydet"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Konfigürasyon kaydetme hatası: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Konfigürasyon değeri al"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Konfigürasyon değeri ayarla"""
        self.config[key] = value
        return self.save_config()

    def reset(self) -> bool:
        """Konfigürasyonu varsayılana sıfırla"""
        self.config = self.DEFAULT_CONFIG.copy()
        return self.save_config()

    def export_config(self, export_path: str) -> bool:
        """Konfigürasyonu dışa aktar"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except:
            return False

    def import_config(self, import_path: str) -> bool:
        """Konfigürasyonu içe aktar"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            return self.save_config()
        except:
            return False


# ===== Plugin System (Genişletilebilir Mimari) =====

class PluginInterface:
    """Plugin arayüzü (gelecek genişletmeler için)"""

    def on_download_start(self, video_info: Dict):
        """İndirme başladığında"""
        pass

    def on_download_complete(self, file_path: str):
        """İndirme tamamlandığında"""
        pass

    def on_convert_start(self, input_file: str, output_format: str):
        """Dönüştürme başladığında"""
        pass

    def on_convert_complete(self, output_file: str):
        """Dönüştürme tamamlandığında"""
        pass


class PluginManager:
    """Plugin yöneticisi"""

    def __init__(self):
        self.plugins: List[PluginInterface] = []

    def register_plugin(self, plugin: PluginInterface):
        """Plugin kaydet"""
        self.plugins.append(plugin)

    def trigger(self, event: str, *args, **kwargs):
        """Event'i tetikle"""
        for plugin in self.plugins:
            method = getattr(plugin, event, None)
            if method and callable(method):
                try:
                    method(*args, **kwargs)
                except Exception as e:
                    print(f"Plugin hatası ({event}): {e}")
