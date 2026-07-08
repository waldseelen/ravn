"""
Tests for DatabaseManager and ConfigManager behavior.
"""

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from ravn_app.core.database import ConfigManager, ConversionRecord, DatabaseManager, DownloadRecord, OperationRecord


class TestDatabaseManagerBasics:
    def test_db_path_defaults_to_config_path(self, tmp_path):
        db_file = tmp_path / "default.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ), patch("ravn_app.core.database.get_database_file_path", return_value=db_file):
            db = DatabaseManager()
            try:
                assert db.db_path == str(db_file)
            finally:
                db.close()

    def test_connect_failure_leaves_no_connection(self, tmp_path):
        db_path = tmp_path / "bad.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ), patch("ravn_app.core.database.sqlite3.connect", side_effect=sqlite3.Error("boom")):
            with pytest.raises(Exception):
                DatabaseManager(db_path=str(db_path))

    def test_run_migrations_raises_without_connection(self, tmp_path):
        db_path = tmp_path / "x.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                db.conn = None
                with pytest.raises(Exception):
                    db._run_migrations()
            finally:
                db.close()

    def test_run_migrations_when_up_to_date_returns(self, tmp_path):
        db_path = tmp_path / "x.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                before = db.get_schema_version()
                db._run_migrations()
                after = db.get_schema_version()
                assert before == after
            finally:
                db.close()

    def test_run_migrations_missing_script_raises(self, tmp_path):
        db_path = tmp_path / "x.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                cursor = db.conn.cursor()
                cursor.execute("UPDATE schema_version SET version = 3 WHERE id = 1")
                db.conn.commit()
                with patch("ravn_app.core.database.LATEST_SCHEMA_VERSION", 5):
                    with pytest.raises(Exception):
                        db._run_migrations()
            finally:
                db.close()

    def test_run_migrations_wrapped_exception(self, tmp_path):
        db_path = tmp_path / "x.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                cursor = db.conn.cursor()
                cursor.execute("UPDATE schema_version SET version = 1 WHERE id = 1")
                db.conn.commit()
                with patch.object(db, "_migrate_v1_to_v2", side_effect=RuntimeError("broken")):
                    with pytest.raises(Exception):
                        db._run_migrations()
            finally:
                db.close()

    def test_noop_create_tables_when_connection_missing(self, tmp_path):
        db_path = tmp_path / "x.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                db.conn = None
                db._create_tables()
            finally:
                db.close()

    def test_get_schema_version_returns_1_when_row_missing(self, tmp_path):
        db_path = tmp_path / "x.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                db.conn.execute("DELETE FROM schema_version WHERE id = 1")
                db.conn.commit()
                assert db.get_schema_version() == 1
            finally:
                db.close()

    def test_backup_database_when_source_missing(self, tmp_path):
        db_path = tmp_path / "x.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                db.close()
                Path(db.db_path).unlink(missing_ok=True)
                backup_path = db.backup_database()
                assert Path(backup_path).exists()
            finally:
                db.close()

    def test_clear_history_all_and_conversions(self, tmp_path):
        db_path = tmp_path / "ravn.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                db.add_download(
                    DownloadRecord(
                        url="https://example.com/1",
                        title="Video",
                        format="mp4",
                        quality="best",
                        file_path="f.mp4",
                        file_size=100,
                        download_date="2024-01-01",
                        status="completed",
                    )
                )
                db.add_conversion(
                    ConversionRecord(
                        input_file="in.mp4",
                        output_file="out.mkv",
                        input_codec="h264",
                        output_codec="h265",
                        conversion_date="2024-01-01",
                        status="completed",
                    )
                )
                db.clear_history("conversions")
                assert len(db.get_conversions(limit=10)) == 0
                assert len(db.get_downloads(limit=10)) == 1
                db.clear_history("all")
                assert len(db.get_downloads(limit=10)) == 0
            finally:
                db.close()

    def test_get_downloads_with_status_filter(self, tmp_path):
        db_path = tmp_path / "ravn.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                db.add_download(
                    DownloadRecord(
                        url="https://example.com/a",
                        title="A",
                        format="mp4",
                        quality="best",
                        file_path="a.mp4",
                        file_size=100,
                        download_date="2024-01-01",
                        status="failed",
                    )
                )
                db.add_download(
                    DownloadRecord(
                        url="https://example.com/b",
                        title="B",
                        format="mp4",
                        quality="best",
                        file_path="b.mp4",
                        file_size=100,
                        download_date="2024-01-02",
                        status="completed",
                    )
                )
                failed = db.get_downloads(limit=10, status="failed")
                assert len(failed) == 1
                assert failed[0].status == "failed"
            finally:
                db.close()

    def test_add_and_get_downloads(self, tmp_path):
        db_path = tmp_path / "ravn.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                db.add_download(
                    DownloadRecord(
                        url="https://example.com/video",
                        title="Video",
                        format="mp4",
                        quality="best",
                        file_path=str(tmp_path / "video.mp4"),
                        file_size=1024,
                        download_date="2024-01-01T00:00:00",
                        status="completed",
                        duration=10.0,
                    )
                )
                items = db.get_downloads(limit=10)
                assert len(items) == 1
                assert items[0].title == "Video"
            finally:
                db.close()

    def test_add_and_get_conversions(self, tmp_path):
        db_path = tmp_path / "ravn.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                db.add_conversion(
                    ConversionRecord(
                        input_file="in.mp4",
                        output_file="out.mkv",
                        input_codec="h264",
                        output_codec="h265",
                        conversion_date="2024-01-01T00:00:00",
                        status="completed",
                    )
                )
                rows = db.get_conversions(limit=10)
                assert len(rows) == 1
                assert rows[0].output_file == "out.mkv"
            finally:
                db.close()

    def test_add_and_get_operations(self, tmp_path):
        db_path = tmp_path / "ravn.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                db.add_operation(
                    OperationRecord(
                        task_type="mixer_audio",
                        operation="mix",
                        title="mix.mp3",
                        input_paths=["a.mp3", "b.mp3"],
                        output_path="mix.mp3",
                        format="mp3",
                        started_at="2024-01-01T00:00:00",
                        completed_at="2024-01-01T00:00:10",
                        duration=10.0,
                        status="completed",
                        metadata={"track_count": 2},
                    )
                )
                rows = db.get_operations(limit=10)
                assert len(rows) == 1
                assert rows[0].task_type == "mixer_audio"
                assert rows[0].metadata["track_count"] == 2
            finally:
                db.close()

    def test_favorites_add_get_remove(self, tmp_path):
        db_path = tmp_path / "ravn.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                assert db.add_favorite("https://x", "X") is True
                assert db.add_favorite("https://x", "X") is False
                favs = db.get_favorites()
                assert len(favs) == 1
                assert db.remove_favorite("https://x") is True
            finally:
                db.close()

    def test_statistics_and_clear(self, tmp_path):
        db_path = tmp_path / "ravn.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                db.add_download(
                    DownloadRecord(
                        url="https://example.com",
                        title="Video",
                        format="mp4",
                        quality="best",
                        file_path="f.mp4",
                        file_size=4096,
                        download_date="2024-01-01",
                        status="completed",
                    )
                )
                db.add_operation(
                    OperationRecord(
                        task_type="apply_filters",
                        operation="apply_filters",
                        title="filtered.mp4",
                        input_paths=["input.mp4"],
                        output_path="filtered.mp4",
                        format="mp4",
                        completed_at="2024-01-01T00:00:05",
                        status="completed",
                    )
                )
                stats = db.get_statistics()
                assert stats["total_downloads"] >= 1
                assert stats["successful_downloads"] >= 1
                assert stats["total_operations"] >= 1
                db.clear_history("downloads")
                assert len(db.get_downloads(limit=10)) == 0
                db.clear_history("operations")
                assert len(db.get_operations(limit=10)) == 0
            finally:
                db.close()

    def test_history_indexes_exist(self, tmp_path):
        db_path = tmp_path / "ravn.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                rows = db.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index' AND name LIKE 'idx_%'"
                ).fetchall()
                index_names = {row[0] for row in rows}
                assert "idx_downloads_download_date" in index_names
                assert "idx_downloads_status_download_date" in index_names
                assert "idx_conversions_conversion_date" in index_names
                assert "idx_operations_history_sort" in index_names
                assert "idx_operations_task_type_history_sort" in index_names
            finally:
                db.close()

    def test_history_queries_use_indexes(self, tmp_path):
        db_path = tmp_path / "ravn.db"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            db = DatabaseManager(db_path=str(db_path))
            try:
                db.add_download(
                    DownloadRecord(
                        url="https://example.com/a",
                        title="A",
                        format="mp4",
                        quality="best",
                        file_path="a.mp4",
                        file_size=100,
                        download_date="2024-01-01T00:00:00",
                        status="completed",
                    )
                )
                db.add_operation(
                    OperationRecord(
                        task_type="filters",
                        operation="apply_filters",
                        title="filtered.mp4",
                        input_paths=["input.mp4"],
                        output_path="filtered.mp4",
                        format="mp4",
                        started_at="2024-01-01T00:00:00",
                        completed_at="2024-01-01T00:00:05",
                        status="completed",
                    )
                )

                download_plan = db.conn.execute(
                    "EXPLAIN QUERY PLAN SELECT * FROM downloads WHERE status = ? ORDER BY download_date DESC LIMIT ?",
                    ("completed", 5),
                ).fetchall()
                operation_plan = db.conn.execute(
                    "EXPLAIN QUERY PLAN SELECT * FROM operations ORDER BY COALESCE(completed_at, started_at) DESC LIMIT ?",
                    (5,),
                ).fetchall()

                download_details = " ".join(str(row[-1]) for row in download_plan)
                operation_details = " ".join(str(row[-1]) for row in operation_plan)
                assert "idx_downloads_status_download_date" in download_details
                assert "idx_operations_history_sort" in operation_details
                assert "TEMP B-TREE" not in operation_details.upper()
            finally:
                db.close()


class TestConfigManagerBasics:
    def test_config_path_defaults_to_config_file_path(self, tmp_path):
        cfg_path = tmp_path / "cfg.json"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ), patch("ravn_app.core.database.get_config_file_path", return_value=cfg_path):
            cfg = ConfigManager()
            try:
                assert cfg.config_file == str(cfg_path)
            finally:
                if hasattr(cfg, "config_file"):
                    Path(cfg.config_file).unlink(missing_ok=True)

    def test_config_created_and_persisted(self, tmp_path):
        config_file = tmp_path / "config.json"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            cfg = ConfigManager(config_file=str(config_file))
            try:
                assert config_file.exists()
                cfg.set("theme", "dark")
                assert cfg.get("theme") == "dark"
            finally:
                Path(config_file).unlink(missing_ok=True)

    def test_config_validation_applies_defaults(self, tmp_path):
        config_file = tmp_path / "invalid.json"
        config_file.write_text(json.dumps({"concurrent_downloads": "bad"}), encoding="utf-8")
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            cfg = ConfigManager(config_file=str(config_file))
            assert isinstance(cfg.get("concurrent_downloads"), int)

    def test_config_load_invalid_json_returns_defaults(self, tmp_path):
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{invalid json", encoding="utf-8")
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            cfg = ConfigManager(config_file=str(config_file))
            assert cfg.get("theme") == "dark"

    def test_export_import_config(self, tmp_path):
        config_file = tmp_path / "base.json"
        export_file = tmp_path / "export.json"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            cfg = ConfigManager(config_file=str(config_file))
            cfg.set("language", "en")
            assert cfg.export_config(str(export_file)) is True
            assert export_file.exists()

            cfg2 = ConfigManager(config_file=str(tmp_path / "import_target.json"))
            assert cfg2.import_config(str(export_file)) is True
            assert cfg2.get("language") == "en"
            Path(cfg2.config_file).unlink(missing_ok=True)

    def test_reset_restores_defaults(self, tmp_path):
        config_file = tmp_path / "config.json"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            cfg = ConfigManager(config_file=str(config_file))
            cfg.set("language", "en")
            assert cfg.reset() is True
            assert cfg.get("language") == "tr"

    def test_get_section_returns_copy(self, tmp_path):
        config_file = tmp_path / "config.json"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            cfg = ConfigManager(config_file=str(config_file))
            mixer_section = cfg.get_section("mixer")
            mixer_section["default_format"] = "wav"
            assert cfg.get("mixer")["default_format"] == "mp3"

    def test_save_config_failure(self, tmp_path):
        config_file = tmp_path / "config.json"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            cfg = ConfigManager(config_file=str(config_file))
            with patch("builtins.open", side_effect=OSError("cannot write")):
                assert cfg.save_config() is False

    def test_export_and_import_failure(self, tmp_path):
        config_file = tmp_path / "config.json"
        with patch("ravn_app.core.database.ensure_directories_exist"), patch(
            "ravn_app.core.database.migrate_all_legacy_files"
        ):
            cfg = ConfigManager(config_file=str(config_file))
            assert cfg.export_config(str(tmp_path / "no" / "dir" / "x.json")) is False
            assert cfg.import_config(str(tmp_path / "missing.json")) is False


class TestPluginHooks:
    def test_plugin_interface_methods(self):
        from ravn_app.core.database import PluginInterface

        plugin = PluginInterface()
        plugin.on_download_start({"title": "x"})
        plugin.on_download_complete("x.mp4")
        plugin.on_convert_start("in.mp4", "mp4")
        plugin.on_convert_complete("out.mp4")

    def test_plugin_manager_trigger_and_error_path(self, caplog):
        import logging

        from ravn_app.core.database import PluginInterface, PluginManager

        class GoodPlugin(PluginInterface):
            def __init__(self):
                self.called = False

            def on_download_start(self, video_info):
                self.called = bool(video_info)

        class BadPlugin(PluginInterface):
            def on_download_start(self, _video_info):
                raise RuntimeError("plugin boom")

        manager = PluginManager()
        good = GoodPlugin()
        bad = BadPlugin()
        manager.register_plugin(good)
        manager.register_plugin(bad)

        with caplog.at_level(logging.ERROR, logger="ravn_app.core.database"):
            manager.trigger("on_download_start", {"title": "ok"})
        assert good.called is True
        assert "Plugin hatası" in caplog.text

