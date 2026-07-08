"""
RAVN - Database and Configuration Management (Faz 4)
SQLite veritabanı ve konfigürasyon yönetimi
"""

import json
import logging
import os
import shutil
import sqlite3
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ravn_app.core.config_paths import (
    ensure_directories_exist,
    get_config_file_path,
    get_database_file_path,
    get_default_config,
    migrate_all_legacy_files,
    validate_config,
)

logger = logging.getLogger(__name__)


LATEST_SCHEMA_VERSION = 4


class DatabaseMigrationError(Exception):
    """Raised when database migration fails."""


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


@dataclass
class OperationRecord:
    """Generic persisted Phase 7 operation record."""
    id: Optional[int] = None
    task_type: str = ""
    operation: str = ""
    title: str = ""
    input_paths: Optional[List[str]] = None
    output_path: str = ""
    format: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration: float = 0.0
    status: str = DownloadStatus.COMPLETED.value
    error_message: str = ""
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.input_paths is None:
            self.input_paths = []
        if self.metadata is None:
            self.metadata = {}


class DatabaseManager:
    """SQLite veritabanı yöneticisi"""

    def __init__(self, db_path: Optional[str] = None):
        """
        DatabaseManager'ı başlat

        Args:
            db_path: Veritabanı dosya yolu (None = use OS-specific default)
        """
        # Ensure config directories exist and migrate legacy files
        ensure_directories_exist()
        migrate_all_legacy_files()

        if db_path is None:
            self.db_path = str(get_database_file_path())
        else:
            # Support both legacy path and explicit path
            self.db_path = db_path

        self.conn = None
        self._connect()
        self._run_migrations()
        self._create_tables()
        logger.debug(f"DatabaseManager initialized with path: {self.db_path}")

    def _connect(self):
        """Veritabanına bağlan"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.debug(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Veritabanı bağlantı hatası: {e}")

    def _require_conn(self) -> sqlite3.Connection:
        """Return the live connection or fail loudly.

        `self.conn` is best-effort (``_connect`` leaves it None on failure) and can be
        None after ``close()``. Routing writes/reads through this helper turns a cryptic
        ``AttributeError: 'NoneType' has no attribute 'cursor'`` into a clear, typed error,
        and lets the type checker know the connection is non-None past this point.
        """
        if self.conn is None:
            raise RuntimeError("Veritabanı bağlantısı yok (bağlantı kurulamadı veya kapatıldı)")
        return self.conn

    def _create_tables(self):
        """Tabloları oluştur"""
        if not self.conn:
            return

        cursor = self._require_conn().cursor()

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

        # Generic operation history (Phase 7 queue/history persistence)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                operation TEXT NOT NULL,
                title TEXT,
                input_paths TEXT,
                output_path TEXT,
                format TEXT,
                started_at TEXT,
                completed_at TEXT,
                duration REAL,
                status TEXT DEFAULT 'completed',
                error_message TEXT,
                metadata TEXT
            )
        ''')

        self._create_history_indexes(cursor)
        self._require_conn().commit()

    def _run_migrations(self):
        """Run schema migrations with backup protection."""
        if not self.conn:
            raise DatabaseMigrationError("Database connection is not initialized")

        self._ensure_schema_version_table()
        current_version = self.get_schema_version()

        if current_version >= LATEST_SCHEMA_VERSION:
            return

        for target_version in range(current_version + 1, LATEST_SCHEMA_VERSION + 1):
            backup_path = self.backup_database()
            logger.info(
                "Applying database migration v%s -> v%s (backup: %s)",
                target_version - 1,
                target_version,
                backup_path,
            )
            try:
                if target_version == 2:
                    self._migrate_v1_to_v2()
                elif target_version == 3:
                    self._migrate_v2_to_v3()
                elif target_version == 4:
                    self._migrate_v3_to_v4()
                else:
                    raise DatabaseMigrationError(
                        f"No migration script available for schema v{target_version}"
                    )
                self._set_schema_version(target_version)
            except Exception as exc:
                raise DatabaseMigrationError(
                    f"Migration to schema v{target_version} failed: {exc}"
                ) from exc

    def _ensure_schema_version_table(self):
        """Create schema_version table if not present and initialize row."""
        cursor = self._require_conn().cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
            '''
        )
        cursor.execute('SELECT version FROM schema_version WHERE id = 1')
        row = cursor.fetchone()
        if row is None:
            cursor.execute(
                '''
                INSERT INTO schema_version (id, version, updated_at)
                VALUES (1, 1, ?)
                ''',
                (self._utc_now_iso(),),
            )
        self._require_conn().commit()

    def get_schema_version(self) -> int:
        """Return current schema version."""
        cursor = self._require_conn().cursor()
        cursor.execute('SELECT version FROM schema_version WHERE id = 1')
        row = cursor.fetchone()
        if row is None:
            return 1
        return int(row["version"])

    def _set_schema_version(self, version: int):
        """Persist schema version after migration."""
        cursor = self._require_conn().cursor()
        cursor.execute(
            '''
            UPDATE schema_version
            SET version = ?, updated_at = ?
            WHERE id = 1
            ''',
            (version, self._utc_now_iso()),
        )
        self._require_conn().commit()

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _create_history_indexes(cursor: sqlite3.Cursor) -> None:
        """Create indexes that support the most common history/top-N reads."""
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_downloads_download_date ON downloads(download_date DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_downloads_status_download_date ON downloads(status, download_date DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversions_conversion_date ON conversions(conversion_date DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_operations_history_sort ON operations(COALESCE(completed_at, started_at) DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_operations_task_type_history_sort ON operations(task_type, COALESCE(completed_at, started_at) DESC)"
        )

    def backup_database(self) -> str:
        """Create a timestamped backup before migration attempt."""
        source_path = Path(self.db_path)
        backup_dir = source_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        backup_path = backup_dir / f"{source_path.stem}.migration-{timestamp}.bak"

        if source_path.exists():
            shutil.copy2(source_path, backup_path)
        else:
            backup_path.write_bytes(b"")

        return str(backup_path)

    def _migrate_v1_to_v2(self):
        """
        Migration script v1 -> v2.

        Phase 2 config dir relocation shipped at filesystem level. This migration
        records the transition in DB metadata so startup can apply versioned DB
        migrations deterministically.
        """
        cursor = self._require_conn().cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS migration_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_version INTEGER NOT NULL,
                to_version INTEGER NOT NULL,
                migration_name TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                details TEXT
            )
            '''
        )
        cursor.execute(
            '''
            INSERT INTO migration_history (
                from_version, to_version, migration_name, applied_at, details
            ) VALUES (?, ?, ?, ?, ?)
            ''',
            (
                1,
                2,
                "config_dir_relocation",
                self._utc_now_iso(),
                "Recorded Phase 2 config/data relocation migration",
            ),
        )
        self._require_conn().commit()

    def _migrate_v2_to_v3(self):
        """Migration script v2 -> v3 for generic Phase 7 operation history."""
        cursor = self._require_conn().cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS migration_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_version INTEGER NOT NULL,
                to_version INTEGER NOT NULL,
                migration_name TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                details TEXT
            )
            '''
        )
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                operation TEXT NOT NULL,
                title TEXT,
                input_paths TEXT,
                output_path TEXT,
                format TEXT,
                started_at TEXT,
                completed_at TEXT,
                duration REAL,
                status TEXT DEFAULT 'completed',
                error_message TEXT,
                metadata TEXT
            )
            '''
        )
        cursor.execute(
            '''
            INSERT INTO migration_history (
                from_version, to_version, migration_name, applied_at, details
            ) VALUES (?, ?, ?, ?, ?)
            ''',
            (
                2,
                3,
                "phase7_operation_history",
                self._utc_now_iso(),
                "Added generic operations table for Phase 7 queue/history persistence",
            ),
        )
        self._require_conn().commit()

    def _migrate_v3_to_v4(self):
        """Migration script v3 -> v4 for history/top-N query indexes."""
        cursor = self._require_conn().cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS migration_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_version INTEGER NOT NULL,
                to_version INTEGER NOT NULL,
                migration_name TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                details TEXT
            )
            '''
        )
        cursor.execute(
            '''
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
            '''
        )
        cursor.execute(
            '''
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
            '''
        )
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                operation TEXT NOT NULL,
                title TEXT,
                input_paths TEXT,
                output_path TEXT,
                format TEXT,
                started_at TEXT,
                completed_at TEXT,
                duration REAL,
                status TEXT DEFAULT 'completed',
                error_message TEXT,
                metadata TEXT
            )
            '''
        )
        self._create_history_indexes(cursor)
        cursor.execute(
            '''
            INSERT INTO migration_history (
                from_version, to_version, migration_name, applied_at, details
            ) VALUES (?, ?, ?, ?, ?)
            ''',
            (
                3,
                4,
                "history_query_indexes",
                self._utc_now_iso(),
                "Added top-N/history indexes for downloads, conversions, and operations",
            ),
        )
        self._require_conn().commit()

    def add_download(self, record: DownloadRecord) -> int:
        """İndirme kaydı ekle"""
        cursor = self._require_conn().cursor()

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

        self._require_conn().commit()
        return cursor.lastrowid or 0

    def get_downloads(
        self,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[DownloadRecord]:
        """İndirme kayıtlarını getir"""
        cursor = self._require_conn().cursor()

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
        cursor = self._require_conn().cursor()

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

        self._require_conn().commit()
        return cursor.lastrowid or 0

    def get_conversions(self, limit: int = 100) -> List[ConversionRecord]:
        """Dönüştürme kayıtlarını getir"""
        cursor = self._require_conn().cursor()
        cursor.execute('''
            SELECT * FROM conversions
            ORDER BY conversion_date DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        return [self._row_to_conversion_record(row) for row in rows]

    def add_operation(self, record: OperationRecord) -> int:
        """Persist a generic Phase 7 operation history record."""
        cursor = self._require_conn().cursor()
        cursor.execute(
            '''
            INSERT INTO operations (
                task_type, operation, title, input_paths, output_path, format,
                started_at, completed_at, duration, status, error_message, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                record.task_type,
                record.operation,
                record.title,
                json.dumps(record.input_paths, ensure_ascii=False),
                record.output_path,
                record.format,
                record.started_at,
                record.completed_at,
                record.duration,
                record.status,
                record.error_message,
                json.dumps(record.metadata, ensure_ascii=False),
            ),
        )
        self._require_conn().commit()
        return cursor.lastrowid or 0

    def get_operations(self, limit: int = 100, task_type: Optional[str] = None) -> List[OperationRecord]:
        """Return persisted generic operation history rows."""
        cursor = self._require_conn().cursor()
        if task_type:
            cursor.execute(
                '''
                SELECT * FROM operations
                WHERE task_type = ?
                ORDER BY COALESCE(completed_at, started_at) DESC
                LIMIT ?
                ''',
                (task_type, limit),
            )
        else:
            cursor.execute(
                '''
                SELECT * FROM operations
                ORDER BY COALESCE(completed_at, started_at) DESC
                LIMIT ?
                ''',
                (limit,),
            )
        rows = cursor.fetchall()
        return [self._row_to_operation_record(row) for row in rows]

    def add_favorite(self, url: str, title: str) -> bool:
        """Favorilere ekle"""
        try:
            cursor = self._require_conn().cursor()
            cursor.execute('''
                INSERT INTO favorites (url, title)
                VALUES (?, ?)
            ''', (url, title))
            self._require_conn().commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Zaten var

    def get_favorites(self) -> List[Dict]:
        """Favorileri getir"""
        cursor = self._require_conn().cursor()
        cursor.execute('SELECT * FROM favorites ORDER BY added_date DESC')

        return [dict(row) for row in cursor.fetchall()]

    def remove_favorite(self, url: str) -> bool:
        """Favorilerden kaldır"""
        cursor = self._require_conn().cursor()
        cursor.execute('DELETE FROM favorites WHERE url = ?', (url,))
        self._require_conn().commit()
        return cursor.rowcount > 0

    def get_statistics(self) -> Dict[str, Any]:
        """İstatistikleri al"""
        cursor = self._require_conn().cursor()

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

        # Toplam Phase 7 operasyon
        cursor.execute('SELECT COUNT(*) FROM operations')
        stats['total_operations'] = cursor.fetchone()[0]

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
        cursor = self._require_conn().cursor()

        if table == "all":
            cursor.execute('DELETE FROM downloads')
            cursor.execute('DELETE FROM conversions')
            cursor.execute('DELETE FROM operations')
        elif table == "downloads":
            cursor.execute('DELETE FROM downloads')
        elif table == "conversions":
            cursor.execute('DELETE FROM conversions')
        elif table == "operations":
            cursor.execute('DELETE FROM operations')

        self._require_conn().commit()
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

    def _row_to_operation_record(self, row) -> OperationRecord:
        """SQLite row'unu OperationRecord'a çevir."""
        try:
            input_paths = json.loads(row['input_paths']) if row['input_paths'] else []
        except Exception:
            input_paths = []
        try:
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
        except Exception:
            metadata = {}
        return OperationRecord(
            id=row['id'],
            task_type=row['task_type'],
            operation=row['operation'],
            title=row['title'] or "",
            input_paths=input_paths,
            output_path=row['output_path'] or "",
            format=row['format'] or "",
            started_at=row['started_at'] or "",
            completed_at=row['completed_at'] or "",
            duration=row['duration'] or 0.0,
            status=row['status'] or DownloadStatus.COMPLETED.value,
            error_message=row['error_message'] or "",
            metadata=metadata,
        )

    def close(self):
        """Veritabanı bağlantısını kapat"""
        if self.conn:
            self.conn.close()


class ConfigManager:
    """Konfigürasyon yöneticisi"""

    DEFAULT_CONFIG = get_default_config()

    def __init__(self, config_file: Optional[str] = None):
        """
        ConfigManager'ı başlat

        Args:
            config_file: Konfigürasyon dosyası yolu (None = use OS-specific default)
        """
        # Ensure config directories exist and migrate legacy files
        ensure_directories_exist()
        migrate_all_legacy_files()

        if config_file is None:
            self.config_file = str(get_config_file_path())
        else:
            # Support both legacy path and explicit path
            self.config_file = config_file

        self.config = self._load_config()
        logger.debug(f"ConfigManager initialized with path: {self.config_file}")

    def _load_config(self) -> Dict[str, Any]:
        """Konfigürasyonu yükle ve şemaya göre doğrula"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Validate and fill missing keys with defaults
                    validated_config, errors = validate_config(loaded_config)
                    if errors:
                        for error in errors:
                            logger.warning(f"Config validation: {error}")
                    return validated_config
            except Exception as e:
                logger.error(f"Konfigürasyon yükleme hatası: {e}")
                return get_default_config()
        else:
            # Create new config with defaults
            config = get_default_config()
            # Ensure parent directory exists before saving
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                logger.info(f"Created new config file at {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to create config file: {e}")
            return config

    def save_config(self) -> bool:
        """Konfigürasyonu kaydet"""
        try:
            # Ensure parent directory exists
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.debug(f"Saved config to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Konfigürasyon kaydetme hatası: {e}")
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
        self.config = deepcopy(self.DEFAULT_CONFIG)
        return self.save_config()

    def get_section(self, key: str) -> Dict[str, Any]:
        """Return a defensive copy of a nested config section."""
        value = self.config.get(key, {})
        return deepcopy(value) if isinstance(value, dict) else {}

    def export_config(self, export_path: str) -> bool:
        """Konfigürasyonu dışa aktar"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as exc:
            logger.error("Konfigürasyon dışa aktarılamadı (%s): %s", export_path, exc)
            return False

    def import_config(self, import_path: str) -> bool:
        """Konfigürasyonu içe aktar"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            return self.save_config()
        except Exception as exc:
            logger.error("Konfigürasyon içe aktarılamadı (%s): %s", import_path, exc)
            return False


# ===== Internal hook placeholders (not a public runtime plugin API) =====

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
                    logger.error("Plugin hatası (%s): %s", event, e)
