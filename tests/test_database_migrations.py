"""
Tests for DatabaseManager migrations and schema versioning.
"""

from pathlib import Path
from unittest.mock import patch

import sqlite3

from ravn_app.core.database import DatabaseManager, LATEST_SCHEMA_VERSION


class TestDatabaseMigrations:
    def test_schema_version_table_created_and_upgraded(self, tmp_path):
        db_path = tmp_path / "ravn_history.db"

        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                assert db.get_schema_version() == LATEST_SCHEMA_VERSION
            finally:
                db.close()

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_version WHERE id = 1")
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == LATEST_SCHEMA_VERSION

            cursor.execute("SELECT COUNT(*) FROM migration_history")
            migrated_rows = cursor.fetchone()[0]
            assert migrated_rows >= 1
        finally:
            conn.close()

    def test_backup_created_before_migration(self, tmp_path):
        db_path = tmp_path / "ravn_history.db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE seed (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                backup_dir = Path(db.db_path).parent / "backups"
                backups = list(backup_dir.glob("ravn_history.migration-*.bak"))
                assert backups, "expected at least one migration backup"
            finally:
                db.close()

